import asyncio
from typing import List, Dict, Any, Optional
import os
import json
import math
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from ..models.mysql_database import (
    EntityEvent, LongTermReflection, NpcStory, DialogueLog, get_db
)
from ..models.llm_client import llm_client
import sys

class RAGRetriever:
    """RAG检索器 - 长期记忆检索"""
    
    def __init__(self):
        self.top_k = int(os.getenv("RAG_TOP_K", 10))
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        try:
            # 计算点积
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # 计算向量的模长
            norm1 = math.sqrt(sum(a * a for a in vec1))
            norm2 = math.sqrt(sum(a * a for a in vec2))
            
            # 避免除零错误
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # 计算余弦相似度
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))  # 确保结果在[0,1]范围内
        except Exception:
            return 0.0
        
    async def retrieve_long_term_memory(self, query: str, user_id: str, 
                                      project_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """并行检索所有四种长期记忆"""
        try:
            # 生成查询向量
            query_embedding = await llm_client.generate_embedding(query)
            if not query_embedding:
                return self._empty_results()
            
            # 使用asyncio.gather并行执行四个检索任务
            entity_events_task = self._retrieve_entity_events(query_embedding, user_id, project_id)
            dialogue_logs_task = self._retrieve_dialogue_logs(query_embedding, user_id, project_id)
            reflections_task = self._retrieve_long_term_reflections(query_embedding, user_id, project_id)
            npc_stories_task = self._retrieve_npc_stories(query_embedding)
            
            # 并行执行所有任务
            entity_events, dialogue_logs, reflections, npc_stories = await asyncio.gather(
                entity_events_task,
                dialogue_logs_task,
                reflections_task,
                npc_stories_task,
                return_exceptions=True
            )
            
            # 处理可能的异常结果
            return {
                'entity_events': entity_events if not isinstance(entity_events, Exception) else [],
                'dialogue_logs': dialogue_logs if not isinstance(dialogue_logs, Exception) else [],
                'long_term_reflections': reflections if not isinstance(reflections, Exception) else [],
                'npc_stories': npc_stories if not isinstance(npc_stories, Exception) else []
            }
            
        except Exception as e:
            print(f"RAG检索失败: {e}")
            return self._empty_results()
            
    async def _retrieve_entity_events(self, query_embedding: List[float], 
                                     user_id: str, project_id: str) -> List[Dict[str, Any]]:
        """检索实体事件记忆"""
        db = next(get_db())
        try:
            # 使用MySQL兼容的查询获取所有记录
            query_sql = text("""
                SELECT id, content, created_at, embedding
                FROM Memory_entity_events 
                WHERE user_id = :user_id AND project_id = :project_id
                AND embedding IS NOT NULL
            """)
            
            result = db.execute(query_sql, {
                'user_id': user_id,
                'project_id': project_id
            })
            
            events = []
            for row in result:
                try:
                    # 解析JSON格式的embedding
                    if row.embedding:
                        stored_embedding = json.loads(row.embedding) if isinstance(row.embedding, str) else row.embedding
                        similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                        
                        events.append({
                            'id': row.id,
                            'content': row.content,
                            'created_at': row.created_at.isoformat(),
                            'similarity': similarity
                        })
                except Exception as e:
                    print(f"处理实体事件记录失败: {e}")
                    continue
            
            # 按相似度排序并返回top_k
            events.sort(key=lambda x: x['similarity'], reverse=True)
            return events[:self.top_k]
            
        except Exception as e:
            print(f"检索实体事件失败: {e}")
            return []
        finally:
            db.close()
            
    async def _retrieve_dialogue_logs(self, query_embedding: List[float], 
                                     user_id: str, project_id: str) -> List[Dict[str, Any]]:
        """检索原始对话记忆 - 带上下文召回功能"""
        db = next(get_db())
        try:
            # 第一步：找到所有相关的对话并计算相似度
            query_sql = text("""
                SELECT id, role, content, created_at, embedding
                FROM Memory_dialogue_logs 
                WHERE user_id = :user_id AND project_id = :project_id
                AND embedding IS NOT NULL
                ORDER BY created_at ASC
            """)
            
            result = db.execute(query_sql, {
                'user_id': user_id,
                'project_id': project_id
            })
            
            all_dialogues = []
            for row in result:
                try:
                    # 解析JSON格式的embedding
                    if row.embedding:
                        stored_embedding = json.loads(row.embedding) if isinstance(row.embedding, str) else row.embedding
                        similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                        
                        all_dialogues.append({
                            'id': row.id,
                            'role': row.role,
                            'content': row.content,
                            'created_at': row.created_at.isoformat(),
                            'similarity': similarity
                        })
                except Exception as e:
                    print(f"处理对话记录失败: {e}")
                    continue
            
            # 第二步：按相似度排序，找到最相关的对话
            all_dialogues.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 第三步：获取最相关的3组上下文对话
            context_groups = await self._get_context_dialogue_groups(all_dialogues, user_id, project_id, db)
            
            return context_groups
            
        except Exception as e:
            print(f"检索对话记忆失败: {e}")
            return []
        finally:
            db.close()
    
    async def _get_context_dialogue_groups(self, sorted_dialogues: List[Dict[str, Any]], 
                                         user_id: str, project_id: str, db) -> List[Dict[str, Any]]:
        """获取上下文对话组：找到最相关的对话后，获取其上下文（上4条下5条），每组10条对话"""
        try:
            if not sorted_dialogues:
                return []
            
            # 获取最相关的前3个对话作为锚点
            top_anchors = sorted_dialogues[:3]
            all_context_dialogues = []
            
            for anchor in top_anchors:
                anchor_id = anchor['id']
                
                # 获取以锚点为中心的上下文对话：上4条 + 锚点 + 下5条 = 10条
                context_sql = text("""
                    (
                        SELECT id, role, content, created_at, 'before' as position
                        FROM Memory_dialogue_logs 
                        WHERE user_id = :user_id AND project_id = :project_id
                        AND id < :anchor_id
                        ORDER BY id DESC LIMIT 4
                    )
                    UNION ALL
                    (
                        SELECT id, role, content, created_at, 'anchor' as position
                        FROM Memory_dialogue_logs 
                        WHERE user_id = :user_id AND project_id = :project_id
                        AND id = :anchor_id
                    )
                    UNION ALL
                    (
                        SELECT id, role, content, created_at, 'after' as position
                        FROM Memory_dialogue_logs 
                        WHERE user_id = :user_id AND project_id = :project_id
                        AND id > :anchor_id
                        ORDER BY id ASC LIMIT 5
                    )
                    ORDER BY id ASC
                """)
                
                # 执行查询
                result = db.execute(context_sql, {
                    'user_id': user_id,
                    'project_id': project_id,
                    'anchor_id': anchor_id
                })
                
                # 构建当前锚点的上下文对话组
                context_group = []
                for row in result:
                    # 如果是锚点对话，使用已计算的相似度
                    if row.id == anchor_id:
                        similarity = anchor['similarity']
                        is_anchor = True
                    else:
                        similarity = 0.0
                        is_anchor = False
                    
                    context_group.append({
                        'id': row.id,
                        'role': row.role,
                        'content': row.content,
                        'created_at': row.created_at.isoformat(),
                        'similarity': similarity,
                        'is_anchor': is_anchor
                    })
                
                # 将当前组的对话添加到总列表中
                if context_group:
                    all_context_dialogues.extend(context_group)
            
            return all_context_dialogues
            
        except Exception as e:
            print(f"获取上下文对话组失败: {e}")
            return sorted_dialogues[:self.top_k]  # 降级到原始逻辑
            
    async def _retrieve_long_term_reflections(self, query_embedding: List[float], 
                                             user_id: str, project_id: str) -> List[Dict[str, Any]]:
        """检索反思记忆"""
        db = next(get_db())
        try:
            query_sql = text("""
                SELECT id, content, created_at, embedding
                FROM Memory_long_term_reflections 
                WHERE user_id = :user_id AND project_id = :project_id
                AND embedding IS NOT NULL
            """)
            
            result = db.execute(query_sql, {
                'user_id': user_id,
                'project_id': project_id
            })
            
            reflections = []
            for row in result:
                try:
                    # 解析JSON格式的embedding
                    if row.embedding:
                        stored_embedding = json.loads(row.embedding) if isinstance(row.embedding, str) else row.embedding
                        similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                        
                        reflections.append({
                            'id': row.id,
                            'content': row.content,
                            'created_at': row.created_at.isoformat(),
                            'similarity': similarity
                        })
                except Exception as e:
                    print(f"处理反思记录失败: {e}")
                    continue
            
            # 按相似度排序并返回top_k
            reflections.sort(key=lambda x: x['similarity'], reverse=True)
            return reflections[:self.top_k]
            
        except Exception as e:
            print(f"检索反思记忆失败: {e}")
            return []
        finally:
            db.close()
            
    async def _retrieve_npc_stories(self, query_embedding: List[float]) -> List[Dict[str, Any]]:
        """检索NPC故事记忆"""
        db = next(get_db())
        try:
            query_sql = text("""
                SELECT id, story_name, content, embedding
                FROM Memory_npc_stories 
                WHERE embedding IS NOT NULL
            """)
            
            result = db.execute(query_sql)
            
            stories = []
            for row in result:
                try:
                    # 解析JSON格式的embedding
                    if row.embedding:
                        stored_embedding = json.loads(row.embedding) if isinstance(row.embedding, str) else row.embedding
                        similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                        
                        stories.append({
                            'id': row.id,
                            'story_name': row.story_name,
                            'content': row.content,
                            'similarity': similarity
                        })
                except Exception as e:
                    print(f"处理NPC故事记录失败: {e}")
                    continue
            
            # 按相似度排序并返回top_k
            stories.sort(key=lambda x: x['similarity'], reverse=True)
            return stories[:self.top_k]
            
        except Exception as e:
            print(f"检索NPC故事失败: {e}")
            return []
        finally:
            db.close()
            
    def _empty_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """返回空结果"""
        return {
            'entity_events': [],
            'dialogue_logs': [],
            'long_term_reflections': [],
            'npc_stories': []
        }

# 全局RAG检索器实例
rag_retriever = RAGRetriever()