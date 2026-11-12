from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, JSON, text, UniqueConstraint
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库连接URL
DATABASE_URL = os.getenv('DATABASE_URL')

# 如果DATABASE_URL不正确，使用MySQL配置
if not DATABASE_URL or '+aiomysql' not in DATABASE_URL:
    DATABASE_URL = 'mysql+aiomysql://aigame_user:aigame_strong_password_123@121.40.249.125:3306/aigame_db'
    os.environ['DATABASE_URL'] = DATABASE_URL

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

if '+aiomysql' not in DATABASE_URL:
    raise ValueError("DATABASE_URL must contain '+aiomysql' for async operations")

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = 'Memory_user_profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    project_id = Column(String(255), nullable=False)
    profile_json = Column(JSON, default={})
    dialogue_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('user_id', 'project_id', name='_user_project_uc'),)

class CoreEvent(Base):
    """核心事件模型 - 存储重大事件（核心记忆）"""
    __tablename__ = "Memory_core_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class EntityEvent(Base):
    """实体事件模型 - 存储实体事件（长期记忆）"""
    __tablename__ = "Memory_entity_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON)  # 向量嵌入存储为JSON格式
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class CoreReflection(Base):
    """核心反思记忆模型 - 存储重大反思（核心记忆）"""
    __tablename__ = "Memory_core_reflections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class LongTermReflection(Base):
    """长期反思记忆模型 - 存储普通反思（长期记忆）"""
    __tablename__ = "Memory_long_term_reflections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON)  # 向量嵌入存储为JSON格式
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class NpcStory(Base):
    """NPC故事记忆模型 - 存储NPC的背景故事和关键经历"""
    __tablename__ = "Memory_npc_stories"
    
    id = Column(Integer, primary_key=True, index=True)
    story_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON)  # 向量嵌入存储为JSON格式

class DialogueLog(Base):
    """对话日志模型 - 存储完整的原始对话历史"""
    __tablename__ = "Memory_dialogue_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # 'user' 或 'assistant'
    content = Column(Text, nullable=False)
    embedding = Column(JSON)  # 向量嵌入存储为JSON格式
    created_at = Column(DateTime, server_default=func.now())

def get_async_database_url():
    """获取异步数据库连接URL"""
    return DATABASE_URL

# 同步引擎用于创建表
engine = create_engine(
    DATABASE_URL.replace('+aiomysql', '+pymysql') if DATABASE_URL else '',
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_recycle=3600,   # 1小时后回收连接
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接数
    echo=False           # 不打印SQL语句
)

# 异步引擎用于运行时操作
if DATABASE_URL and '+aiomysql' in DATABASE_URL:
    async_engine = create_async_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # 连接前检查连接是否有效
        pool_recycle=3600,   # 1小时后回收连接
        pool_size=10,        # 连接池大小
        max_overflow=20,     # 最大溢出连接数
        echo=False           # 不打印SQL语句
    )
else:
    raise ValueError("DATABASE_URL must contain '+aiomysql' for async operations")
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    """获取异步数据库会话（带重试机制）"""
    max_retries = 3
    retry_delay = 1  # 秒
    
    for attempt in range(max_retries):
        try:
            async with AsyncSessionLocal() as session:
                # 测试连接
                await session.execute(text("SELECT 1"))
                yield session
                return
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"数据库连接失败，第{attempt + 1}次重试中... 错误: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                print(f"数据库连接失败，已达到最大重试次数: {e}")
                raise

def get_db():
    """获取同步数据库会话（仅用于兼容性）"""
    from sqlalchemy.orm import sessionmaker as sync_sessionmaker
    SessionLocal = sync_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建所有数据表"""
    Base.metadata.create_all(bind=engine)

async def create_tables_async():
    """异步创建所有数据表"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)