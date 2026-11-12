#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库表结构更新脚本
为UserProfile表添加dialogue_count字段
"""

import asyncio
import aiomysql
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 数据库连接配置
MYSQL_HOST = '121.40.249.125'
MYSQL_PORT = 3306
MYSQL_USER = 'aigame_user'
MYSQL_PASSWORD = 'aigame_strong_password_123'
MYSQL_DATABASE = 'aigame_db'

async def update_user_profile_table():
    """
    更新UserProfile表结构，添加dialogue_count字段
    """
    connection = None
    try:
        # 建立数据库连接
        print("[INFO] 连接到MySQL数据库...")
        connection = await aiomysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            charset='utf8mb4'
        )
        
        cursor = await connection.cursor()
        
        # 检查表是否存在
        print("[INFO] 检查Memory_user_profiles表是否存在...")
        await cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = 'Memory_user_profiles'
        """, (MYSQL_DATABASE,))
        
        table_exists = (await cursor.fetchone())[0] > 0
        
        if not table_exists:
            print("[INFO] Memory_user_profiles表不存在，创建新表...")
            # 创建完整的Memory_user_profiles表
            await cursor.execute("""
                CREATE TABLE Memory_user_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    project_id VARCHAR(255) NOT NULL,
                    profile_json JSON DEFAULT (JSON_OBJECT()),
                    dialogue_count INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY _user_project_uc (user_id, project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("[SUCCESS] Memory_user_profiles表创建成功！")
        else:
            print("[INFO] Memory_user_profiles表已存在，检查dialogue_count字段...")
            
            # 检查dialogue_count字段是否存在
            await cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'Memory_user_profiles' 
                AND column_name = 'dialogue_count'
            """, (MYSQL_DATABASE,))
            
            column_exists = (await cursor.fetchone())[0] > 0
            
            if not column_exists:
                print("[INFO] dialogue_count字段不存在，添加字段...")
                # 添加dialogue_count字段
                await cursor.execute("""
                    ALTER TABLE Memory_user_profiles 
                    ADD COLUMN dialogue_count INT DEFAULT 0
                """)
                print("[SUCCESS] dialogue_count字段添加成功！")
            else:
                print("[INFO] dialogue_count字段已存在，无需添加。")
        
        # 提交更改
        await connection.commit()
        print("[SUCCESS] 数据库表结构更新完成！")
        
        # 显示当前表结构
        print("\n[INFO] 当前Memory_user_profiles表结构：")
        await cursor.execute("DESCRIBE Memory_user_profiles")
        columns = await cursor.fetchall()
        
        print("字段名\t\t类型\t\t\t空值\t键\t默认值")
        print("-" * 80)
        for column in columns:
            field, type_, null, key, default, extra = column
            print(f"{field:<15} {type_:<20} {null:<8} {key:<8} {default or 'NULL':<15}")
        
    except Exception as e:
        print(f"[ERROR] 数据库操作失败: {e}")
        if connection:
            await connection.rollback()
        raise
    finally:
        if connection:
            await connection.ensure_closed()
            print("[INFO] 数据库连接已关闭。")

async def main():
    """
    主函数
    """
    print("=" * 80)
    print("Memory_user_profiles表结构更新脚本")
    print("=" * 80)
    print(f"数据库: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
    print(f"用户: {MYSQL_USER}")
    print("=" * 80)
    
    try:
        await update_user_profile_table()
        print("\n[SUCCESS] 表结构更新完成！")
    except Exception as e:
        print(f"\n[ERROR] 更新失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)