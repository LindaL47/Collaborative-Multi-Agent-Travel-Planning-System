import os
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models.mysql_database import UserProfile, CoreEvent, CoreReflection, get_db, get_async_db
from ..models.redis_client import redis_client
from .memory_processor import memory_processor
from .rag_retriever import rag_retriever

class MemoryManager:
    """记忆管理器 - 统一的记忆操作接口"""
    
    def __init__(self):
        self.memory_threshold = int(os.getenv("MEMORY_THRESHOLD", 60))
        self.short_term_size = int(os.getenv("SHORT_TERM_MEMORY_SIZE", 60))
        self.consolidation_trigger_rounds = int(os.getenv("MEMORY_CONSOLIDATION_TRIGGER_ROUNDS", 240))
        
    async def add_dialogue(self, user_id: str, project_id: str, 
                          role: str, content: str) -> Dict[str, Any]:
        """添加新对话到短期记忆"""
        try:
            # 获取当前短期记忆
            dialogue_history = await redis_client.get_short_term_memory(user_id, project_id)
            
            # 添加新对话
            new_message = {
                'role': role,
                'content': content,
                'timestamp': str(int(time.time()))
            }
            dialogue_history.append(new_message)
            
            # 保持短期记忆大小限制
            if len(dialogue_history) > self.short_term_size:
                dialogue_history = dialogue_history[-self.short_term_size:]
            
            # 存储回Redis
            await redis_client.store_short_term_memory(user_id, project_id, dialogue_history)
            
            # 检查是否需要触发记忆处理
            should_process = len(dialogue_history) >= self.memory_threshold
            
            return {
                'status': 'success',
                'dialogue_count': len(dialogue_history),
                'should_process_memory': should_process
            }
            
        except Exception as e:
            print(f"添加对话失败: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def process_memory(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """处理记忆（当达到阈值时调用）"""
        db = None
        try:
            # 获取短期记忆
            dialogue_history = await redis_client.get_short_term_memory(user_id, project_id)
            
            if not dialogue_history:
                return {'status': 'error', 'message': '没有找到短期记忆'}

            db = next(get_db())
            profile = db.query(UserProfile).filter(
                and_(UserProfile.user_id == user_id, UserProfile.project_id == project_id)
            ).first()

            if not profile:
                return {'status': 'error', 'message': '用户画像不存在，请先初始化用户'}

            # 增加对话计数
            processed_dialogue_count = len(dialogue_history)
            if profile.dialogue_count is None:
                profile.dialogue_count = 0
            profile.dialogue_count += processed_dialogue_count
            
            # 执行记忆处理流水线
            result = await memory_processor.process_memory_pipeline(
                user_id, project_id, dialogue_history
            )
            
            consolidation_triggered = False
            consolidation_result = None
            
            if result.get('status') == 'processing_in_background':
                # 清空短期记忆
                await redis_client.clear_short_term_memory(user_id, project_id)
                
                # 检查是否需要触发核心记忆整合
                if profile.dialogue_count >= self.consolidation_trigger_rounds:
                    print(f"用户 {user_id} 的对话轮数 ({profile.dialogue_count}) 达到阈值 ({self.consolidation_trigger_rounds})，触发核心记忆整合。")
                    consolidation_triggered = True
                    consolidation_result = await memory_processor.consolidate_core_memories(user_id, project_id)
                    if consolidation_result.get('status') == 'success':
                        # 成功后重置计数器
                        profile.dialogue_count = 0
                        # 将合并信息添加到结果中
                        result['consolidation_triggered'] = True
                        result['consolidation_result'] = consolidation_result
                    else:
                        print(f"核心记忆整合失败，对话计数器将不会重置，将在下次处理时重试。")
                        result['consolidation_triggered'] = True
                        result['consolidation_failed'] = True
                        result['consolidation_error'] = consolidation_result.get('message', '未知错误')
                else:
                    result['consolidation_triggered'] = False

                # 立即更新核心记忆缓存，不再依赖后台任务
                await self._update_core_memory(user_id, project_id)
            
            db.commit()
            return result
            
        except Exception as e:
            if db:
                db.rollback()
            print(f"处理记忆失败: {e}")
            return {'status': 'error', 'message': str(e)}
        finally:
            if db:
                db.close()
            
    async def get_memory_context(self, user_id: str, project_id: str, 
                               query: str) -> Dict[str, Any]:
        """获取记忆上下文（用于对话生成）"""
        try:
            # 1. 获取短期记忆
            short_term_memory = await redis_client.get_short_term_memory(user_id, project_id)
            
            # 2. 获取核心记忆
            core_memory = await redis_client.get_core_memory(user_id, project_id)
            
            # 3. RAG检索长期记忆
            long_term_retrieval = await rag_retriever.retrieve_long_term_memory(
                query, user_id, project_id
            )
            
            return {
                'short_term_memory': short_term_memory,
                'core_memory': core_memory,
                'long_term_memory_retrieval': long_term_retrieval,
                'status': 'success'
            }
            
        except Exception as e:
            print(f"获取记忆上下文失败: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def _update_core_memory(self, user_id: str, project_id: str):
        """更新核心记忆"""
        try:
            # 从数据库获取最新的用户画像、核心事件和核心反思
            db = next(get_db())
            try:
                # 获取用户画像
                profile_record = db.query(UserProfile).filter(
                    and_(UserProfile.user_id == user_id, 
                         UserProfile.project_id == project_id)
                ).first()
                
                # 获取核心事件
                core_events = db.query(CoreEvent).filter(
                    and_(CoreEvent.user_id == user_id, 
                         CoreEvent.project_id == project_id)
                ).order_by(CoreEvent.created_at.desc()).limit(10).all()
                
                # 获取核心反思
                core_reflections = db.query(CoreReflection).filter(
                    and_(CoreReflection.user_id == user_id, 
                         CoreReflection.project_id == project_id)
                ).order_by(CoreReflection.created_at.desc()).limit(10).all()
                
                if profile_record:
                    core_memory = {
                        'user_profile': profile_record.profile_json,
                        'core_events': [event.content for event in core_events],
                        'core_reflections': [reflection.content for reflection in core_reflections],
                        'last_updated': profile_record.updated_at.isoformat()
                    }
                    
                    # 存储到Redis
                    await redis_client.store_core_memory(user_id, project_id, core_memory)
                    
            finally:
                db.close()
                
        except Exception as e:
            print(f"更新核心记忆失败: {e}")
            
    async def initialize_user_memory(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """初始化用户记忆"""
        try:
            # 使用同步数据库操作避免greenlet错误
            db = next(get_db())
            try:
                existing_profile = db.query(UserProfile).filter(
                    and_(UserProfile.user_id == user_id, 
                         UserProfile.project_id == project_id)
                ).first()
                
                profile_data = {
                    'personality': {},
                    'interests': [],
                    'behavior_patterns': {},
                    'preferences': {},
                    'other_traits': {}
                }
                
                if not existing_profile:
                    # 创建初始用户画像
                    initial_profile = UserProfile(
                        user_id=user_id,
                        project_id=project_id,
                        profile_json=profile_data
                    )
                    db.add(initial_profile)
                    db.commit()
                    db.refresh(initial_profile)
                    profile_to_use = initial_profile
                else:
                    profile_to_use = existing_profile
                    
                # 初始化Redis中的记忆
                await redis_client.store_short_term_memory(user_id, project_id, [])
                await redis_client.store_core_memory(user_id, project_id, {
                    'user_profile': profile_to_use.profile_json,
                    'last_updated': profile_to_use.updated_at.isoformat() if profile_to_use.updated_at else profile_to_use.created_at.isoformat()
                })
                
                return {'status': 'success', 'message': '用户记忆初始化完成'}
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"初始化用户记忆失败: {e}")
            return {'status': 'error', 'message': str(e)}

# 全局记忆管理器实例
memory_manager = MemoryManager()