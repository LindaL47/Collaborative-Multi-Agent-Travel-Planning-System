import redis.asyncio as redis
import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class RedisClient:
    """Redis客户端，用于短期记忆存储"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = None
        
    async def connect(self):
        """连接Redis"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def _ensure_connected(self):
        """确保Redis连接已建立"""
        if self.redis_client is None:
            await self.connect()
            
    async def store_short_term_memory(self, user_id: str, project_id: str, 
                                    dialogue_history: List[Dict[str, Any]]) -> bool:
        """存储短期记忆（对话历史）"""
        try:
            await self._ensure_connected()
            key = f"short_term:{user_id}:{project_id}"
            value = json.dumps(dialogue_history, ensure_ascii=False)
            await self.redis_client.setex(key, 3600, value)  # 1小时过期
            return True
        except Exception as e:
            print(f"存储短期记忆失败: {e}")
            return False
            
    async def get_short_term_memory(self, user_id: str, project_id: str) -> List[Dict[str, Any]]:
        """获取短期记忆"""
        try:
            await self._ensure_connected()
            key = f"short_term:{user_id}:{project_id}"
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return []
        except Exception as e:
            print(f"获取短期记忆失败: {e}")
            return []
            
    async def store_core_memory(self, user_id: str, project_id: str, 
                              core_memory: Dict[str, Any]) -> bool:
        """存储核心记忆"""
        try:
            await self._ensure_connected()
            key = f"core_memory:{user_id}:{project_id}"
            value = json.dumps(core_memory, ensure_ascii=False)
            await self.redis_client.set(key, value)
            return True
        except Exception as e:
            print(f"存储核心记忆失败: {e}")
            return False
            
    async def get_core_memory(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """获取核心记忆"""
        try:
            await self._ensure_connected()
            key = f"core_memory:{user_id}:{project_id}"
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return {}
        except Exception as e:
            print(f"获取核心记忆失败: {e}")
            return {}
            
    async def clear_short_term_memory(self, user_id: str, project_id: str) -> bool:
        """清空短期记忆"""
        try:
            await self._ensure_connected()
            key = f"short_term:{user_id}:{project_id}"
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"清空短期记忆失败: {e}")
            return False

# 全局Redis客户端实例
redis_client = RedisClient()