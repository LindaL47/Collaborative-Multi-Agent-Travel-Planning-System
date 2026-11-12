#!/usr/bin/env python3
"""
MySQL数据库设置脚本
直接使用SQLAlchemy创建数据库和表结构
"""

import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# 加载MySQL环境变量
load_dotenv('.env.mysql')

# 导入MySQL模型
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'server', 'api'))
from models.mysql_database import Base, create_tables, create_tables_async

class MySQLSetup:
    def __init__(self):
        # 从环境变量读取数据库URL
        database_url_env = os.getenv('DATABASE_URL')
        if database_url_env:
            # 将aiomysql替换为pymysql用于同步连接
            self.database_url = database_url_env.replace('mysql+aiomysql://', 'mysql+pymysql://')
            self.async_database_url = database_url_env
            
            # 解析URL获取连接参数
            from urllib.parse import urlparse
            parsed = urlparse(database_url_env)
            self.mysql_host = parsed.hostname or "localhost"
            self.mysql_port = parsed.port or 3306
            self.mysql_user = parsed.username or "aigame_user"
            self.mysql_password = parsed.password or "aigame_strong_password_123"
            self.mysql_database = parsed.path.lstrip('/') or "aigame_db"
        else:
            # 回退到默认配置
            self.mysql_host = "localhost"
            self.mysql_port = 3306
            self.mysql_user = "aigame_user"
            self.mysql_password = "aigame_strong_password_123"
            self.mysql_database = "aigame_db"
            
            # 构建连接URL
            self.database_url = f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            self.async_database_url = f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        
        print(f"数据库连接URL: {self.database_url}")
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            # 先尝试连接到MySQL服务器（不指定数据库）
            server_url = f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}"
            engine = create_engine(server_url)
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                print(f"✅ MySQL服务器连接成功: {row[0]}")
                
                # 创建数据库（如果不存在）
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {self.mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
                print(f"✅ 数据库 '{self.mysql_database}' 创建成功")
                
            engine.dispose()
            return True
            
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            print("\n请检查以下配置:")
            print(f"- MySQL服务是否运行")
            print(f"- 用户名: {self.mysql_user}")
            print(f"- 密码: {self.mysql_password}")
            print(f"- 主机: {self.mysql_host}")
            print(f"- 端口: {self.mysql_port}")
            return False
    
    def create_tables_sync(self):
        """同步创建表"""
        try:
            engine = create_engine(self.database_url)
            
            # 创建所有表
            Base.metadata.create_all(bind=engine)
            
            # 验证表是否创建成功
            with engine.connect() as conn:
                result = conn.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result.fetchall()]
                
                print("\n📋 创建的表:")
                for table in tables:
                    print(f"  ✅ {table}")
                
                expected_tables = [
                    'Memory_user_profiles',
                    'Memory_core_events', 
                    'Memory_entity_events',
                    'Memory_core_reflections',
                    'Memory_long_term_reflections',
                    'Memory_npc_stories',
                    'Memory_dialogue_logs'
                ]
                
                missing_tables = [t for t in expected_tables if t not in tables]
                if missing_tables:
                    print("\n❌ 缺失的表:")
                    for table in missing_tables:
                        print(f"  - {table}")
                    return False
                else:
                    print("\n✅ 所有表创建成功!")
            
            engine.dispose()
            return True
            
        except Exception as e:
            print(f"❌ 创建表失败: {e}")
            return False
    
    async def test_async_operations(self):
        """测试异步操作"""
        try:
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
            from sqlalchemy.orm import sessionmaker
            
            async_engine = create_async_engine(self.async_database_url)
            AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = :db_name"), 
                                              {"db_name": self.mysql_database})
                row = result.fetchone()
                table_count = row[0]
                print(f"✅ 异步连接测试成功，数据库中有 {table_count} 个表")
            
            await async_engine.dispose()
            return True
            
        except Exception as e:
            print(f"❌ 异步操作测试失败: {e}")
            return False
    
    async def setup_database(self):
        """完整的数据库设置流程"""
        print("🚀 开始MySQL数据库设置...\n")
        
        # 1. 测试连接并创建数据库
        print("1️⃣ 测试数据库连接...")
        if not self.test_connection():
            return False
        
        # 2. 创建表结构
        print("\n2️⃣ 创建数据表...")
        if not self.create_tables_sync():
            return False
        
        # 3. 测试异步操作
        print("\n3️⃣ 测试异步操作...")
        if not await self.test_async_operations():
            return False
        
        print("\n🎉 MySQL数据库设置完成！")
        print("\n📋 下一步操作:")
        print("1. 将 .env.mysql 重命名为 .env (备份原 .env 文件)")
        print("2. 运行测试脚本: python test_mysql_connection.py")
        print("3. 如需迁移现有数据，运行: python migrate_to_mysql.py")
        print("4. 重启应用程序")
        
        return True

async def main():
    """主函数"""
    setup = MySQLSetup()
    await setup.setup_database()

if __name__ == "__main__":
    asyncio.run(main())