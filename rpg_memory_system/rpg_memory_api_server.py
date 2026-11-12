"""
RPG记忆系统API服务器
提供提示词版本管理的FastAPI应用
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
import os

# 添加项目路径
sys.path.append('/home/shengchan/prodev/AIgame/rpg_memory_system')

# 导入路由
from src.server.api.routes.rpg_memory_prompts import create_rpg_memory_prompt_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="RPG记忆系统API",
    description="RPG记忆系统提示词版本管理API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"全局异常处理: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": f"服务器内部错误: {str(exc)}"}
    )

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        # 测试数据库连接
        import aiomysql
        conn = await aiomysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='aigame_strong_root_password_123',
            db='aigame_db',
            charset='utf8mb4'
        )
        await conn.ensure_closed()
        
        return {
            "status": "healthy",
            "service": "RPG记忆系统API",
            "version": "1.0.0",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "service": "RPG记忆系统API",
                "error": str(e)
            }
        )

# 根路径
@app.get("/")
async def root():
    """根路径信息"""
    return {
        "message": "RPG记忆系统API服务",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }

# 注册RPG记忆系统提示词管理路由
rpg_memory_router = create_rpg_memory_prompt_router()
app.include_router(rpg_memory_router)

# 启动信息
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 RPG记忆系统API服务启动")
    logger.info("📋 可用的API端点:")
    logger.info("   • GET /health - 健康检查")
    logger.info("   • GET /docs - API文档")
    logger.info("   • GET /api/rpg-memory-prompts/templates - 获取所有模板")
    logger.info("   • GET /api/rpg-memory-prompts/templates/{template_key}/versions - 获取模板版本")
    logger.info("   • POST /api/rpg-memory-prompts/templates/{template_key}/versions - 创建新版本")
    logger.info("   • PUT /api/rpg-memory-prompts/versions/{version_id} - 更新版本")
    logger.info("   • POST /api/rpg-memory-prompts/versions/{version_id}/publish - 发布版本")
    logger.info("   • DELETE /api/rpg-memory-prompts/versions/{version_id} - 删除版本")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 RPG记忆系统API服务关闭")

if __name__ == "__main__":
    import uvicorn
    
    # 启动开发服务器
    uvicorn.run(
        "rpg_memory_api_server:app",
        host="0.0.0.0",
        port=8888,
        reload=True,
        log_level="info"
    )