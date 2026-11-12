from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from pgvector.psycopg2 import register_vector
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

Base = declarative_base()

class UserProfile(Base):
    """用户画像模型 - 存储玩家的结构化信息"""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    profile_json = Column(JSONB, nullable=False)  # 存储性格、偏好等结构化信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CoreEvent(Base):
    """核心事件模型 - 存储重大事件（核心记忆）"""
    __tablename__ = "core_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EntityEvent(Base):
    """实体事件模型 - 存储实体事件（长期记忆）"""
    __tablename__ = "entity_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(2048))  # 向量嵌入
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CoreReflection(Base):
    """核心反思记忆模型 - 存储重大反思（核心记忆）"""
    __tablename__ = "core_reflections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class LongTermReflection(Base):
    """长期反思记忆模型 - 存储普通反思（长期记忆）"""
    __tablename__ = "long_term_reflections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(2048))  # 向量嵌入
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class NpcStory(Base):
    """NPC故事记忆模型 - 存储NPC的背景故事和关键经历"""
    __tablename__ = "npc_stories"
    
    id = Column(Integer, primary_key=True, index=True)
    story_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(2048))  # 向量嵌入

class DialogueLog(Base):
    """对话日志模型 - 存储完整的原始对话历史"""
    __tablename__ = "dialogue_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' 或 'assistant'
    content = Column(Text, nullable=False)
    embedding = Column(Vector(2048))  # 向量嵌入
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 数据库连接配置
DATABASE_URL = os.getenv("DATABASE_URL")

def get_async_database_url():
    """获取异步数据库连接URL"""
    # 将同步URL转换为异步URL
    if DATABASE_URL.startswith("postgresql://"):
        return DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    return DATABASE_URL

# 同步引擎用于创建表
engine = create_engine(DATABASE_URL)

# 注册pgvector类型到psycopg2连接
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    register_vector(dbapi_connection)

# 异步引擎用于运行时操作
async_engine = create_async_engine(get_async_database_url())
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_db():
    """获取同步数据库会话（仅用于兼容性）"""
    from sqlalchemy.orm import sessionmaker as sync_sessionmaker
    SessionLocal = sync_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# def get_database_url():
#     """获取数据库连接URL"""
#     return DATABASE_URL

# def get_async_database_url():
#     """获取异步数据库连接URL"""
#     # 将同步URL转换为异步URL
#     if DATABASE_URL.startswith("postgresql://"):
#         return DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
#     return DATABASE_URL

def create_tables():
    """创建所有数据表"""
    Base.metadata.create_all(bind=engine)

async def create_tables_async():
    """异步创建所有数据表"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)