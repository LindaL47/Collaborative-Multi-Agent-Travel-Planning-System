#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从rowData.csv导入聊天记录到记忆系统
基于test_memory_interface.py的格式进行数据导入
"""

import asyncio
import csv
import sys
import os
from typing import List, Tuple

# 添加项目路径到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    # 导入记忆接口函数
    from src.server.api.memory_interface import (
        add_dialogue_to_memory,
        get_memory_context_for_chat,
        initialize_user_memory
    )
    # 导入Redis客户端
    from src.server.api.models.redis_client import redis_client
    print("[OK] 成功导入记忆接口函数")
except ImportError as e:
    print(f"[ERROR] 导入记忆接口函数失败: {e}")
    print("[INFO] 请确保在rpg_memory_system目录下运行此脚本")
    sys.exit(1)

class CSVMemoryImporter:
    def __init__(self, csv_file_path: str):
        """初始化CSV导入器"""
        self.csv_file_path = csv_file_path
        self.dialogues = []
        self.user_ids = set()
        
        # 初始化Redis连接
        asyncio.run(self._init_redis())
        
    async def _init_redis(self):
        """初始化Redis连接"""
        try:
            await redis_client.connect()
            print("[OK] Redis连接成功")
        except Exception as e:
            print(f"[ERROR] Redis连接失败: {e}")
            print("[INFO] 请确保Redis服务正在运行")
            raise
    
    def load_csv_data(self) -> bool:
        """从CSV文件加载对话数据"""
        try:
            print(f"[INFO] 开始读取CSV文件: {self.csv_file_path}")
            
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row in csv_reader:
                    user_id = row['user_id']
                    role = row['role']
                    content = row['content']
                    
                    # 收集用户ID
                    self.user_ids.add(user_id)
                    
                    # 添加到对话列表
                    self.dialogues.append({
                        'user_id': user_id,
                        'role': role,
                        'content': content
                    })
            
            print(f"[OK] 成功读取 {len(self.dialogues)} 条对话记录")
            print(f"[INFO] 涉及用户数: {len(self.user_ids)}")
            print(f"[INFO] 用户ID列表: {list(self.user_ids)}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 读取CSV文件失败: {e}")
            return False
    
    def group_dialogues_by_user(self) -> dict:
        """按用户ID分组对话"""
        user_dialogues = {}
        
        for dialogue in self.dialogues:
            user_id = dialogue['user_id']
            if user_id not in user_dialogues:
                user_dialogues[user_id] = []
            
            user_dialogues[user_id].append((dialogue['role'], dialogue['content']))
        
        return user_dialogues
    
    async def initialize_users(self) -> bool:
        """初始化所有用户的记忆系统"""
        print("\n[STEP] 初始化用户记忆系统")
        
        try:
            for user_id in self.user_ids:
                project_id = f"test_llm1"
                
                print(f"[INFO] 初始化用户: {user_id}")
                
                result = await initialize_user_memory(user_id, project_id)
                
                if result.get('status') == 'success':
                    print(f"[OK] 用户 {user_id} 初始化成功")
                else:
                    print(f"[ERROR] 用户 {user_id} 初始化失败: {result.get('message')}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 用户初始化异常: {e}")
            return False
    
    async def import_dialogues_for_user(self, user_id: str, dialogues: List[Tuple[str, str]]) -> bool:
        """为指定用户导入对话数据"""
        project_id = f"project_{user_id}"
        
        print(f"\n[IMPORT] 开始导入用户 {user_id} 的对话数据")
        print(f"[INFO] 对话数量: {len(dialogues)}")
        
        try:
            dialogue_count = 0
            memory_processed_count = 0
            
            for i, (role, content) in enumerate(dialogues):
                print(f"[{i+1}/{len(dialogues)}] 添加对话: {role} -> {content[:50]}...")
                
                result = await add_dialogue_to_memory(
                    user_id, project_id, role, content
                )
                
                if result.get('status') == 'success':
                    dialogue_count = result.get('dialogue_count', 0)
                    should_process = result.get('should_process_memory', False)
                    
                    if should_process:
                        memory_processed_count += 1
                        print(f"[TRIGGER] 触发记忆处理！(第{memory_processed_count}次)")
                        if 'memory_processing' in result:
                            processing_result = result['memory_processing']
                            print(f"[MEMORY] 处理状态: {processing_result.get('status')}")
                else:
                    print(f"[ERROR] 添加对话失败: {result.get('message')}")
                    return False
                
                # 每20轮对话暂停一下，避免过快
                if (i + 1) % 20 == 0:
                    print(f"[INFO] 已添加 {i+1} 轮对话，暂停0.5秒...")
                    await asyncio.sleep(0.5)
            
            print(f"\n[SUMMARY] 用户 {user_id} 导入完成:")
            print(f"  - 总对话数: {len(dialogues)}")
            print(f"  - 最终对话计数: {dialogue_count}")
            print(f"  - 记忆处理次数: {memory_processed_count}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 用户 {user_id} 对话导入异常: {e}")
            return False
    
    async def import_all_data(self) -> bool:
        """导入所有数据"""
        print("\n" + "="*60)
        print("开始从CSV导入聊天记录到记忆系统")
        print("="*60)
        
        # 1. 加载CSV数据
        if not self.load_csv_data():
            return False
        
        # 2. 初始化用户
        if not await self.initialize_users():
            return False
        
        # 3. 按用户分组对话
        user_dialogues = self.group_dialogues_by_user()
        
        # 4. 为每个用户导入对话
        success_count = 0
        for user_id, dialogues in user_dialogues.items():
            if await self.import_dialogues_for_user(user_id, dialogues):
                success_count += 1
            else:
                print(f"[WARNING] 用户 {user_id} 导入失败")
        
        # 5. 总结结果
        print("\n" + "="*60)
        print("导入结果总结")
        print("="*60)
        print(f"总用户数: {len(self.user_ids)}")
        print(f"成功导入: {success_count}")
        print(f"失败导入: {len(self.user_ids) - success_count}")
        print(f"总对话数: {len(self.dialogues)}")
        
        if success_count == len(self.user_ids):
            print("\n[SUCCESS] 🎉 所有数据导入成功！")
            return True
        else:
            print("\n[WARNING] ⚠️ 部分数据导入失败，请检查错误信息。")
            return False
    
    async def test_memory_retrieval(self, user_id: str) -> bool:
        """测试记忆检索功能"""
        project_id = f"project_{user_id}"
        
        print(f"\n[TEST] 测试用户 {user_id} 的记忆检索")
        
        test_queries = [
            "你好",
            "Kane",
            "飞船",
            "星球"
        ]
        
        try:
            for query in test_queries:
                print(f"\n[QUERY] {query}")
                
                result = await get_memory_context_for_chat(
                    user_id, project_id, query
                )
                
                if result.get('status') == 'success':
                    context = result.get('context', {})
                    short_term = context.get('short_term_memory', [])
                    long_term = context.get('long_term_memory_retrieval', [])
                    
                    print(f"[RESULT] 短期记忆: {len(short_term)} 条")
                    print(f"[RESULT] 长期记忆: {len(long_term)} 条")
                    
                    if short_term:
                        print(f"[PREVIEW] 最新对话: {short_term[-1].get('content', '')[:100]}...")
                else:
                    print(f"[ERROR] 记忆检索失败: {result.get('message')}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 记忆检索测试异常: {e}")
            return False


def main():
    """主函数"""
    csv_file_path = "rowData.csv"
    
    if not os.path.exists(csv_file_path):
        print(f"[ERROR] CSV文件不存在: {csv_file_path}")
        print("[INFO] 请确保rowData.csv文件在当前目录下")
        return
    
    # 创建导入器实例
    importer = CSVMemoryImporter(csv_file_path)
    
    # 运行导入
    try:
        success = asyncio.run(importer.import_all_data())
        
        if success:
            # 测试记忆检索（使用第一个用户）
            if importer.user_ids:
                first_user = list(importer.user_ids)[0]
                asyncio.run(importer.test_memory_retrieval(first_user))
        
    except KeyboardInterrupt:
        print("\n[INTERRUPT] 导入被用户中断")
    except Exception as e:
        print(f"\n[ERROR] 导入运行异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()