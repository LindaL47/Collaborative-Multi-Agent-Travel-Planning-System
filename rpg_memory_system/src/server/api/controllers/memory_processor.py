import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models.mysql_database import (
    UserProfile, CoreEvent, EntityEvent, CoreReflection, LongTermReflection, NpcStory, DialogueLog, get_db
)
from ..models.redis_client import redis_client
from ..models.llm_client import llm_client

class MemoryProcessor:
    """记忆处理器 - 核心记忆处理流水线"""
    
    def __init__(self):
        pass
        
    async def process_memory_pipeline(self, user_id: str, project_id: str, 
                                    dialogue_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        记忆处理流水线 - 并行处理三个LLM任务, 增加健壮性
        - 使用 asyncio.wait_for 设置总超时
        - 使用 return_exceptions=True 优雅处理单个任务失败
        - 将耗时的数据库存储操作放入后台任务
        """
        PIPELINE_TIMEOUT = 20.0 # 设置一个15秒的总体超时

        try:
            # 定义三个并行任务
            tasks = [
                llm_client.extract_user_profile(dialogue_history),
                llm_client.extract_events(dialogue_history),
                llm_client.generate_reflection(dialogue_history)
            ]
            
            # 并行执行所有任务，设置总体超时并允许返回异常
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=PIPELINE_TIMEOUT
            )
            
            # 分离成功的结果和异常
            profile_result, events_result, reflection_result = results
            
            # 处理结果，检查每个任务是否成功
            user_profile = profile_result if not isinstance(profile_result, Exception) else {}
            if isinstance(profile_result, Exception):
                print(f"用户画像提取失败: {profile_result}")

            events = events_result if not isinstance(events_result, Exception) else {}
            if isinstance(events_result, Exception):
                print(f"事件提取失败: {events_result}")

            reflections = reflection_result if not isinstance(reflection_result, Exception) else {}
            if isinstance(reflection_result, Exception):
                print(f"反思生成失败: {reflection_result}")

            # 即使部分任务失败，也继续处理成功的部分
            # 同步等待存储操作完成，确保数据一致性
            await self._store_memory(
                user_id, project_id, user_profile, events, reflections, dialogue_history
            )
            
            # 存储完成后返回结果
            return {
                'user_profile': user_profile,
                'events': events,
                'reflection': reflections,
                'status': 'processing_in_background' # 保持状态名称以兼容现有逻辑
            }

        except asyncio.TimeoutError:
            print(f"记忆处理流水线超时（超过 {PIPELINE_TIMEOUT} 秒）")
            return {'status': 'error', 'message': 'Memory processing timed out.'}
            
        except Exception as e:
            print(f"记忆处理流水线发生意外错误: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def _store_memory(self, user_id: str, project_id: str, 
                           user_profile: Dict[str, Any], events: Dict[str, List[str]], 
                           reflections: Dict[str, List[str]], dialogue_history: List[Dict[str, Any]]):
        """存储记忆到数据库"""
        db = next(get_db())
        try:
            # 存储用户画像
            if user_profile:
                profile_record = db.query(UserProfile).filter(
                    and_(UserProfile.user_id == user_id, 
                         UserProfile.project_id == project_id)
                ).first()
                
                if profile_record:
                    # 合并现有画像
                    merged_profile = {**profile_record.profile_json, **user_profile}
                    profile_record.profile_json = merged_profile
                else:
                    # 创建新画像
                    new_profile = UserProfile(
                        user_id=user_id,
                        project_id=project_id,
                        profile_json=user_profile
                    )
                    db.add(new_profile)
            
            # 并行生成嵌入向量
            async def generate_entity_event_embeddings():
                embeddings = []
                for event in events.get('entity_events', []):
                    embedding = await llm_client.generate_embedding(event)
                    embeddings.append((event, embedding))
                return embeddings
            
            async def generate_long_term_reflection_embeddings():
                embeddings = []
                for reflection in reflections.get('long_term_reflections', []):
                    embedding = await llm_client.generate_embedding(reflection)
                    embeddings.append((reflection, embedding))
                return embeddings
            
            async def generate_dialogue_embeddings():
                dialogue_embeddings = []
                for msg in dialogue_history:
                    content = f"{msg['role']}: {msg['content']}"
                    embedding = await llm_client.generate_embedding(content)
                    dialogue_embeddings.append((msg, embedding))
                return dialogue_embeddings
            
            # 并行执行嵌入生成
            entity_event_embeddings, long_term_reflection_embeddings, dialogue_embeddings = await asyncio.gather(
                generate_entity_event_embeddings(),
                generate_long_term_reflection_embeddings(),
                generate_dialogue_embeddings()
            )
            
            # 存储核心事件（去重）
            existing_core_events = db.query(CoreEvent.content).filter(
                and_(CoreEvent.user_id == user_id, CoreEvent.project_id == project_id)
            ).all()
            existing_core_events_set = {item.content for item in existing_core_events}
            
            for event in events.get('core_events', []):
                if event not in existing_core_events_set:
                    event_record = CoreEvent(
                        user_id=user_id,
                        project_id=project_id,
                        content=event
                    )
                    db.add(event_record)
                    existing_core_events_set.add(event)
            
            # 存储实体事件（需要嵌入向量）
            for event, embedding in entity_event_embeddings:
                event_record = EntityEvent(
                    user_id=user_id,
                    project_id=project_id,
                    content=event,
                    embedding=embedding
                )
                db.add(event_record)
            
            # 存储核心反思（去重）
            existing_core_reflections = db.query(CoreReflection.content).filter(
                and_(CoreReflection.user_id == user_id, CoreReflection.project_id == project_id)
            ).all()
            existing_core_reflections_set = {item.content for item in existing_core_reflections}

            for reflection in reflections.get('core_reflections', []):
                if reflection not in existing_core_reflections_set:
                    reflection_record = CoreReflection(
                        user_id=user_id,
                        project_id=project_id,
                        content=reflection
                    )
                    db.add(reflection_record)
                    existing_core_reflections_set.add(reflection)
            
            # 存储长期反思（需要嵌入向量）
            for reflection, embedding in long_term_reflection_embeddings:
                reflection_record = LongTermReflection(
                    user_id=user_id,
                    project_id=project_id,
                    content=reflection,
                    embedding=embedding
                )
                db.add(reflection_record)
            
            # 存储对话日志
            for msg, embedding in dialogue_embeddings:
                log_record = DialogueLog(
                    user_id=user_id,
                    project_id=project_id,
                    role=msg['role'],
                    content=msg['content'],
                    embedding=embedding
                )
                db.add(log_record)
            
            db.commit()
            core_events_count = len(events.get('core_events', []))
            entity_events_count = len(events.get('entity_events', []))
            core_reflections_count = len(reflections.get('core_reflections', []))
            long_term_reflections_count = len(reflections.get('long_term_reflections', []))
            print(f"记忆存储完成: 用户画像1条, 核心事件{core_events_count}条, 实体事件{entity_events_count}条, 核心反思{core_reflections_count}条, 长期反思{long_term_reflections_count}条, 对话{len(dialogue_history)}条")
            
        except Exception as e:
            db.rollback()
            print(f"存储记忆失败: {e}")
        finally:
            db.close()
            

    async def _consolidate_core_memory_type(self, user_id: str, project_id: str, db: Session, memory_model, memory_type_str: str):
        """
        整合特定类型的核心记忆 (事件或反思).
        返回: (before_count, after_count, success)
        """
        limit = 20
        
        count = db.query(memory_model).filter(
            and_(memory_model.user_id == user_id, memory_model.project_id == project_id)
        ).count()

        if count > limit:
            print(f"核心{memory_type_str}数量 ({count}) 超过 {limit}，开始整合...")
            
            current_memories = db.query(memory_model).filter(
                and_(memory_model.user_id == user_id, memory_model.project_id == project_id)
            ).all()
            memory_contents = [mem.content for mem in current_memories]
            
            consolidated_memories = await llm_client.consolidate_memories(memory_contents, memory_type_str)
            
            if consolidated_memories:
                # 删除旧的核心记忆
                db.query(memory_model).filter(
                    and_(memory_model.user_id == user_id, memory_model.project_id == project_id)
                ).delete(synchronize_session=False)
                
                # 存储整合后的新记忆
                for content in consolidated_memories:
                    new_mem = memory_model(
                        user_id=user_id,
                        project_id=project_id,
                        content=content
                    )
                    db.add(new_mem)
                
                print(f"核心{memory_type_str}整合准备完成，数量从 {count} 减少到 {len(consolidated_memories)}.")
                return count, len(consolidated_memories), True
            else:
                print(f"LLM未能返回整合后的核心{memory_type_str}，跳过本次整合。")
                return count, count, False
        else:
            # 数量未超过限制，无需整合
            return count, count, True

    async def consolidate_core_memories(self, user_id: str, project_id: str):
        """
        为指定用户整合核心事件和核心反思.
        """
        db = next(get_db())
        try:
            print(f"开始为用户 {user_id} 整合核心记忆...")
            
            # 整合核心事件
            events_before, events_after, events_success = await self._consolidate_core_memory_type(
                user_id, project_id, db, CoreEvent, "事件"
            )
            
            # 整合核心反思
            reflections_before, reflections_after, reflections_success = await self._consolidate_core_memory_type(
                user_id, project_id, db, CoreReflection, "反思"
            )
            
            db.commit() # Commit all changes at once
            print(f"用户 {user_id} 的核心记忆整合完成。")
            
            return {
                'status': 'success',
                'events_before_consolidation': events_before,
                'events_after_consolidation': events_after,
                'reflections_before_consolidation': reflections_before,
                'reflections_after_consolidation': reflections_after,
                'events_consolidation_success': events_success,
                'reflections_consolidation_success': reflections_success
            }
        except Exception as e:
            db.rollback()
            print(f"核心记忆整合失败: {e}")
            return {'status': 'error', 'message': str(e)}
        finally:
            db.close()
            
    async def _create_dialogue_with_embedding(self, msg: Dict[str, Any], 
                                            user_id: str, project_id: str) -> Optional[DialogueLog]:
        """创建带嵌入向量的对话记录"""
        try:
            embedding = await llm_client.generate_embedding(msg['content'])
            return DialogueLog(
                user_id=user_id,
                project_id=project_id,
                role=msg['role'],
                content=msg['content'],
                embedding=embedding
            )
        except Exception as e:
            print(f"创建对话记录失败: {e}")
            return None

# 全局记忆处理器实例
memory_processor = MemoryProcessor()