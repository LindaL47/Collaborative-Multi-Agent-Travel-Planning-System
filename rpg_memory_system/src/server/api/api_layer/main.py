from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import os
from contextlib import asynccontextmanager

# 导入模型和控制器
from ..models.mysql_database import create_tables_async
from ..models.redis_client import redis_client
from ..controllers.memory_manager import memory_manager
from ..controllers.rag_retriever import rag_retriever

# Pydantic模型
class DialogueRequest(BaseModel):
    user_id: str
    project_id: str
    role: str  # 'user' 或 'assistant'
    content: str

class MemoryContextRequest(BaseModel):
    user_id: str
    project_id: str
    query: str

class InitializeUserRequest(BaseModel):
    user_id: str
    project_id: str

class ProcessMemoryRequest(BaseModel):
    user_id: str
    project_id: str

class GenerateResponseRequest(BaseModel):
    user_id: str
    project_id: str
    user_message: str

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("正在启动AI记忆系统...")
    
    # 创建数据库表
    await create_tables_async()
    print("数据库表创建完成")
    
    # 连接Redis
    await redis_client.connect()
    print("Redis连接成功")
    
    yield
    
    # 关闭时执行
    print("正在关闭AI记忆系统...")
    await redis_client.disconnect()
    print("Redis连接已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="AI游戏记忆系统",
    description="基于memobase思想的AI游戏记忆系统API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI游戏记忆系统API",
        "version": "1.0.0",
        "status": "running"
    }

@app.post("/api/memory/initialize")
async def initialize_user_memory(request: InitializeUserRequest):
    """初始化用户记忆"""
    try:
        result = await memory_manager.initialize_user_memory(
            request.user_id, request.project_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/dialogue")
async def add_dialogue(request: DialogueRequest):
    """添加对话到记忆系统"""
    try:
        result = await memory_manager.add_dialogue(
            request.user_id, request.project_id, request.role, request.content
        )
        
        # 如果需要处理记忆，自动触发
        if result.get('should_process_memory', False):
            process_result = await memory_manager.process_memory(
                request.user_id, request.project_id
            )
            result['memory_processing'] = process_result
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/context")
async def get_memory_context(request: MemoryContextRequest):
    """获取记忆上下文"""
    try:
        result = await memory_manager.get_memory_context(
            request.user_id, request.project_id, request.query
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/process")
async def process_memory(request: ProcessMemoryRequest):
    """手动触发记忆处理"""
    try:
        result = await memory_manager.process_memory(
            request.user_id, request.project_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/generate_response")
async def generate_response(request: GenerateResponseRequest):
    """生成NPC回复"""
    try:
        # 获取完整的记忆上下文（包括短期记忆、核心记忆和长期记忆RAG检索）
        memory_context_result = await memory_manager.get_memory_context(
            request.user_id, request.project_id, request.user_message
        )
        
        if memory_context_result.get('status') != 'success':
            raise Exception(f"获取记忆上下文失败: {memory_context_result.get('message')}")
        
        # 提取各部分记忆
        short_term_memory = memory_context_result.get('short_term_memory', [])
        core_memory = memory_context_result.get('core_memory', {})
        long_term_memory_retrieval = memory_context_result.get('long_term_memory_retrieval', {})
        
        # 调试信息：打印记忆上下文信息
        print(f"[DEBUG] 短期记忆长度: {len(short_term_memory)}")
        print(f"[DEBUG] 核心记忆: {bool(core_memory)}")
        print(f"[DEBUG] 长期记忆检索结果: {list(long_term_memory_retrieval.keys())}")
        
        # 构建完整的记忆上下文
        full_memory_context = {
            'core_memory': core_memory,
            **long_term_memory_retrieval  # 展开长期记忆检索结果
        }
        
        # 生成NPC回复
        from ..models.llm_client import llm_client
        npc_response = await llm_client.generate_npc_response(
            request.user_message, short_term_memory, full_memory_context
        )
        
        # 将NPC回复添加到对话历史
        await memory_manager.add_dialogue(
            request.user_id, request.project_id, "assistant", npc_response
        )
        
        return {
            "status": "success",
            "npc_response": npc_response,
            "memory_context_used": bool(full_memory_context),
            "dialogue_history_length": len(short_term_memory),
            "core_memory_used": bool(core_memory),
            "long_term_retrieval_used": bool(long_term_memory_retrieval)
        }
        
    except Exception as e:
        print(f"生成NPC回复失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )