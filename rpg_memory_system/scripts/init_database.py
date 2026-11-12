# -*- coding: utf-8 -*-
import asyncio
import sys
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.server.api.models.database import Base, get_async_database_url
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def init_database():
    """初始化数据库"""
    print("=== 初始化数据库 ===")
    
    try:
        # 创建数据库引擎
        database_url = get_async_database_url()
        print(f"数据库URL: {database_url.replace(database_url.split('@')[0].split('//')[1], '***')}")
        
        engine = create_async_engine(
            database_url,
            echo=True,  # 显示SQL语句
            future=True
        )
        
        # 测试数据库连接
        print("\n1. 测试数据库连接...")
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"[OK] PostgreSQL版本: {version}")
            
        # 检查pgvector扩展
        print("\n2. 检查pgvector扩展...")
        async with engine.begin() as conn:
            # 创建pgvector扩展（如果不存在）
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # 检查扩展是否安装
            result = await conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'vector';"
            ))
            if result.fetchone():
                print("[OK] pgvector扩展已安装")
            else:
                print("[ERROR] pgvector扩展未安装")
                return False
                
        # 创建所有表
        print("\n3. 创建数据库表...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            print("[OK] 清理旧表")
            
            await conn.run_sync(Base.metadata.create_all)
            print("[OK] 创建新表")
            
        # 验证表创建
        print("\n4. 验证表结构...")
        async with engine.begin() as conn:
            # 获取所有表名
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = [
                'user_profiles', 'user_events', 'reflections', 
                'npc_stories', 'dialogue_logs'
            ]
            
            print(f"创建的表: {tables}")
            
            for table in expected_tables:
                if table in tables:
                    print(f"[OK] {table}")
                else:
                    print(f"[ERROR] {table} 缺失")
                    
        # 创建向量搜索函数
        print("\n5. 创建向量搜索函数...")
        async with engine.begin() as conn:
            # 余弦相似度函数
            await conn.execute(text("""
                CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector)
                RETURNS float AS $$
                BEGIN
                    RETURN 1 - (a <=> b);
                END;
                $$ LANGUAGE plpgsql IMMUTABLE STRICT;
            """))
            print("[OK] 余弦相似度函数已创建")
            
            # 创建向量索引（提高查询性能）
            index_queries = [
                "CREATE INDEX IF NOT EXISTS idx_user_events_embedding ON user_events USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
                "CREATE INDEX IF NOT EXISTS idx_dialogue_logs_embedding ON dialogue_logs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
                "CREATE INDEX IF NOT EXISTS idx_reflections_embedding ON reflections USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
                "CREATE INDEX IF NOT EXISTS idx_npc_stories_embedding ON npc_stories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
            ]
            
            for query in index_queries:
                try:
                    await conn.execute(text(query))
                    print(f"[OK] 向量索引已创建")
                except Exception as e:
                    print(f"[WARNING] 向量索引创建警告: {e}")
                    
        await engine.dispose()
        
        print("\n=== 数据库初始化完成 ===")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 数据库初始化失败: {e}")
        return False

async def check_database_status():
    """检查数据库状态"""
    print("=== 检查数据库状态 ===")
    
    try:
        database_url = get_database_url()
        engine = create_async_engine(database_url, echo=False)
        
        async with engine.begin() as conn:
            # 检查表是否存在
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"现有表: {tables}")
            
            # 检查每个表的记录数
            for table in tables:
                if table.startswith(('user_', 'dialogue_', 'reflections', 'npc_')):
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table};"))
                    count = result.fetchone()[0]
                    print(f"  {table}: {count} 条记录")
                    
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"[ERROR] 检查数据库状态失败: {e}")
        return False

async def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "init":
            success = await init_database()
            sys.exit(0 if success else 1)
            
        elif command == "status":
            success = await check_database_status()
            sys.exit(0 if success else 1)
            
        elif command == "reset":
            print("重置数据库...")
            success = await init_database()
            if success:
                print("\n数据库重置完成")
            sys.exit(0 if success else 1)
            
        else:
            print(f"未知命令: {command}")
            print("可用命令: init, status, reset")
            sys.exit(1)
    else:
        print("数据库管理工具")
        print("用法:")
        print("  python scripts/init_database.py init    - 初始化数据库")
        print("  python scripts/init_database.py status  - 检查数据库状态")
        print("  python scripts/init_database.py reset   - 重置数据库")
        
        # 默认检查状态
        await check_database_status()

if __name__ == "__main__":
    asyncio.run(main())