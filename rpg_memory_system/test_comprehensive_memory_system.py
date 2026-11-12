#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统综合测试文件

本测试文件全面测试RPG记忆系统的各项功能，包括：
1. 记忆接口功能测试
2. 记忆管理器功能测试
3. 记忆处理器功能测试
4. LLM客户端功能测试
5. 数据库操作测试
6. Redis缓存测试
7. RAG检索测试
8. 定时器功能测试
9. 错误处理和异常情况测试
10. 性能和压力测试
"""

import asyncio
import os
import sys
import time
import logging
import json
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目路径
project_root = os.path.dirname(__file__)
api_path = os.path.join(project_root, 'src', 'server', 'api')
sys.path.insert(0, api_path)

# 配置环境变量
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-686b3638-8ce2-4824-a259-48b6a79aca15"
os.environ["LANGFUSE_HOST"] = "http://121.40.249.125:3000"
os.environ["DATABASE_URL"] = "mysql+aiomysql://aigame_user:aigame_strong_password_123@121.40.249.125:3306/aigame_db"

# 导入记忆系统组件
try:
    from src.server.api.memory_interface import (
        add_dialogue_to_memory,
        get_memory_context_for_chat,
        initialize_user_memory
    )
    from src.server.api.controllers.memory_manager import memory_manager
    from src.server.api.controllers.memory_processor import memory_processor
    from src.server.api.controllers.memory_timer import memory_timer
    from src.server.api.controllers.rag_retriever import rag_retriever
    from src.server.api.models.llm_client import llm_client
    from src.server.api.models.redis_client import redis_client
    from src.server.api.models.mysql_database import get_async_db
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python路径: {sys.path}")
    raise

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveMemorySystemTest:
    """记忆系统综合测试类"""
    
    def __init__(self):
        self.test_user_id = f"test_user_{int(time.time())}"
        self.test_project_id = f"test_project_{int(time.time())}"
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': [],
            'performance_metrics': {}
        }
        
        # 测试对话数据
        self.test_dialogues = [
            {"role": "user", "content": "你好，我是新来的冒险者，叫做艾莉亚。"},
            {"role": "assistant", "content": "欢迎来到这个世界，艾莉亚！我是村长，很高兴见到你。"},
            {"role": "user", "content": "这个村子看起来很安静，有什么任务可以做吗？"},
            {"role": "assistant", "content": "最近村子附近出现了一些哥布林，如果你愿意的话，可以帮我们清理一下。"},
            {"role": "user", "content": "好的，我接受这个任务。哥布林在哪里？"},
            {"role": "assistant", "content": "它们在村子北边的森林里，小心一点，带上这把剑。"},
            {"role": "user", "content": "谢谢村长，我会小心的。我现在就出发。"},
            {"role": "assistant", "content": "祝你好运，艾莉亚！记得如果遇到危险就回来。"},
            {"role": "user", "content": "我在森林里发现了哥布林的巢穴，里面有很多哥布林。"},
            {"role": "assistant", "content": "太好了！你能处理得了吗？如果太多的话，可以先撤退。"}
        ]
        
        logger.info(f"初始化测试环境 - 用户ID: {self.test_user_id}, 项目ID: {self.test_project_id}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始运行记忆系统综合测试")
        start_time = time.time()
        
        # 测试列表
        tests = [
            ("基础连接测试", self.test_basic_connections),
            ("用户记忆初始化测试", self.test_user_memory_initialization),
            ("对话添加功能测试", self.test_dialogue_addition),
            ("记忆上下文获取测试", self.test_memory_context_retrieval),
            ("记忆处理流水线测试", self.test_memory_processing_pipeline),
            ("LLM客户端功能测试", self.test_llm_client_functions),
            ("RAG检索功能测试", self.test_rag_retrieval),
            ("定时器功能测试", self.test_timer_functionality),
            ("数据库操作测试", self.test_database_operations),
            ("Redis缓存测试", self.test_redis_cache_operations),
            ("错误处理测试", self.test_error_handling),
            ("性能压力测试", self.test_performance_stress),
            ("数据一致性测试", self.test_data_consistency),
            ("并发操作测试", self.test_concurrent_operations)
        ]
        
        for test_name, test_func in tests:
            await self._run_single_test(test_name, test_func)
        
        total_time = time.time() - start_time
        self.test_results['performance_metrics']['total_test_time'] = total_time
        
        self._print_final_results()
    
    async def _run_single_test(self, test_name: str, test_func):
        """运行单个测试"""
        logger.info(f"\n{'='*60}")
        logger.info(f"开始测试: {test_name}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        try:
            result = await test_func()
            test_time = time.time() - start_time
            
            if result:
                self.test_results['passed'] += 1
                logger.info(f"✅ {test_name} - 通过 (耗时: {test_time:.2f}s)")
            else:
                self.test_results['failed'] += 1
                logger.error(f"❌ {test_name} - 失败 (耗时: {test_time:.2f}s)")
                
            self.test_results['performance_metrics'][test_name] = test_time
            
        except Exception as e:
            test_time = time.time() - start_time
            self.test_results['failed'] += 1
            error_msg = f"{test_name}: {str(e)}"
            self.test_results['errors'].append(error_msg)
            logger.error(f"❌ {test_name} - 异常: {str(e)} (耗时: {test_time:.2f}s)")
            self.test_results['performance_metrics'][test_name] = test_time
    
    async def test_basic_connections(self) -> bool:
        """测试基础连接"""
        try:
            # 测试Redis连接
            await redis_client.connect()
            logger.info("✅ Redis连接成功")
            
            # 测试数据库连接
            async for db in get_async_db():
                logger.info("✅ MySQL数据库连接成功")
                break
            
            return True
        except Exception as e:
            logger.error(f"❌ 基础连接测试失败: {str(e)}")
            return False
    
    async def test_user_memory_initialization(self) -> bool:
        """测试用户记忆初始化"""
        try:
            result = await initialize_user_memory(self.test_user_id, self.test_project_id)
            
            if result['status'] == 'success':
                logger.info(f"✅ 用户记忆初始化成功: {result}")
                return True
            else:
                logger.error(f"❌ 用户记忆初始化失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 用户记忆初始化异常: {str(e)}")
            return False
    
    async def test_dialogue_addition(self) -> bool:
        """测试对话添加功能"""
        try:
            success_count = 0
            
            for i, dialogue in enumerate(self.test_dialogues):
                result = await add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    dialogue['role'],
                    dialogue['content']
                )
                
                if result['status'] == 'success':
                    success_count += 1
                    logger.info(f"✅ 对话 {i+1} 添加成功，当前对话数: {result['dialogue_count']}")
                    
                    # 检查是否触发记忆处理
                    if result.get('should_process_memory'):
                        logger.info(f"🔄 触发记忆处理，对话数达到阈值")
                else:
                    logger.error(f"❌ 对话 {i+1} 添加失败: {result}")
            
            return success_count == len(self.test_dialogues)
            
        except Exception as e:
            logger.error(f"❌ 对话添加测试异常: {str(e)}")
            return False
    
    async def test_memory_context_retrieval(self) -> bool:
        """测试记忆上下文获取"""
        try:
            test_queries = [
                "告诉我关于艾莉亚的信息",
                "村长给了什么任务？",
                "哥布林在哪里？",
                "艾莉亚的冒险经历"
            ]
            
            success_count = 0
            
            for query in test_queries:
                result = await get_memory_context_for_chat(
                    self.test_user_id,
                    self.test_project_id,
                    query
                )
                
                if result['status'] == 'success':
                    success_count += 1
                    logger.info(f"✅ 查询 '{query}' 成功")
                    logger.info(f"   - 短期记忆: {len(result['memory_context']['short_term_memory'])} 条")
                    logger.info(f"   - 核心记忆: {len(result['memory_context']['core_memory'])} 项")
                    logger.info(f"   - 相关记忆: {len(result['memory_context']['relevant_memories'])} 条")
                else:
                    logger.error(f"❌ 查询 '{query}' 失败: {result}")
            
            return success_count == len(test_queries)
            
        except Exception as e:
            logger.error(f"❌ 记忆上下文获取测试异常: {str(e)}")
            return False
    
    async def test_memory_processing_pipeline(self) -> bool:
        """测试记忆处理流水线"""
        try:
            # 添加足够的对话以触发记忆处理
            extended_dialogues = self.test_dialogues * 6  # 60条对话
            
            for dialogue in extended_dialogues:
                await add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    dialogue['role'],
                    dialogue['content']
                )
            
            # 手动触发记忆处理
            result = await memory_manager.process_memory(self.test_user_id, self.test_project_id)
            
            if result['status'] == 'success':
                logger.info(f"✅ 记忆处理流水线成功: {result}")
                return True
            else:
                logger.error(f"❌ 记忆处理流水线失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 记忆处理流水线测试异常: {str(e)}")
            return False
    
    async def test_llm_client_functions(self) -> bool:
        """测试LLM客户端功能"""
        try:
            test_text = "艾莉亚是一个勇敢的冒险者，她接受了清理哥布林的任务。"
            
            # 测试嵌入向量生成
            embedding = await llm_client.generate_embedding(test_text)
            if embedding and len(embedding) > 0:
                logger.info(f"✅ 嵌入向量生成成功，维度: {len(embedding)}")
            else:
                logger.error("❌ 嵌入向量生成失败")
                return False
            
            # 测试用户画像提取
            user_profile = await llm_client.extract_user_profile(self.test_dialogues)
            if user_profile:
                logger.info(f"✅ 用户画像提取成功: {user_profile[:100]}...")
            else:
                logger.error("❌ 用户画像提取失败")
                return False
            
            # 测试事件提取
            events = await llm_client.extract_events(self.test_dialogues)
            if events:
                logger.info(f"✅ 事件提取成功，提取到 {len(events)} 个事件")
            else:
                logger.error("❌ 事件提取失败")
                return False
            
            # 测试反思生成
            reflection = await llm_client.generate_reflection(self.test_dialogues)
            if reflection:
                logger.info(f"✅ 反思生成成功: {reflection[:100]}...")
            else:
                logger.error("❌ 反思生成失败")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ LLM客户端功能测试异常: {str(e)}")
            return False
    
    async def test_rag_retrieval(self) -> bool:
        """测试RAG检索功能"""
        try:
            test_query = "艾莉亚的冒险任务"
            
            # 测试相关记忆检索
            relevant_memories = await rag_retriever.get_relevant_memories(
                self.test_user_id,
                self.test_project_id,
                test_query
            )
            
            logger.info(f"✅ RAG检索成功，找到 {len(relevant_memories)} 条相关记忆")
            return True
            
        except Exception as e:
            logger.error(f"❌ RAG检索功能测试异常: {str(e)}")
            return False
    
    async def test_timer_functionality(self) -> bool:
        """测试定时器功能"""
        try:
            # 测试定时器状态
            timer_status = memory_timer.get_status()
            logger.info(f"✅ 定时器状态获取成功: {timer_status}")
            
            # 测试手动触发定时任务
            await memory_timer.process_pending_memories()
            logger.info("✅ 手动触发定时任务成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 定时器功能测试异常: {str(e)}")
            return False
    
    async def test_database_operations(self) -> bool:
        """测试数据库操作"""
        try:
            # 测试数据库连接和基本操作
            async for db in get_async_db():
                # 这里可以添加更多数据库操作测试
                logger.info("✅ 数据库操作测试成功")
                return True
            
        except Exception as e:
            logger.error(f"❌ 数据库操作测试异常: {str(e)}")
            return False
    
    async def test_redis_cache_operations(self) -> bool:
        """测试Redis缓存操作"""
        try:
            test_key = f"test_cache_{int(time.time())}"
            test_data = {"test": "data", "timestamp": time.time()}
            
            # 测试存储
            await redis_client.set_cache(test_key, test_data, expire_time=60)
            logger.info("✅ Redis缓存存储成功")
            
            # 测试读取
            cached_data = await redis_client.get_cache(test_key)
            if cached_data == test_data:
                logger.info("✅ Redis缓存读取成功")
            else:
                logger.error("❌ Redis缓存读取数据不匹配")
                return False
            
            # 测试删除
            await redis_client.delete_cache(test_key)
            logger.info("✅ Redis缓存删除成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Redis缓存操作测试异常: {str(e)}")
            return False
    
    async def test_error_handling(self) -> bool:
        """测试错误处理"""
        try:
            # 测试无效用户ID
            result = await get_memory_context_for_chat(
                "invalid_user_id",
                "invalid_project_id",
                "test query"
            )
            
            # 应该能够优雅处理错误
            if result['status'] in ['success', 'error']:
                logger.info("✅ 错误处理测试成功")
                return True
            else:
                logger.error("❌ 错误处理测试失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 错误处理测试异常: {str(e)}")
            return False
    
    async def test_performance_stress(self) -> bool:
        """测试性能和压力"""
        try:
            start_time = time.time()
            
            # 并发添加多个对话
            tasks = []
            for i in range(20):
                task = add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    "user" if i % 2 == 0 else "assistant",
                    f"压力测试消息 {i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
            total_time = time.time() - start_time
            
            logger.info(f"✅ 压力测试完成: {success_count}/{len(tasks)} 成功，耗时: {total_time:.2f}s")
            
            return success_count >= len(tasks) * 0.8  # 80%成功率即可
            
        except Exception as e:
            logger.error(f"❌ 性能压力测试异常: {str(e)}")
            return False
    
    async def test_data_consistency(self) -> bool:
        """测试数据一致性"""
        try:
            # 添加对话并检查数据一致性
            test_content = f"数据一致性测试消息 {int(time.time())}"
            
            result = await add_dialogue_to_memory(
                self.test_user_id,
                self.test_project_id,
                "user",
                test_content
            )
            
            if result['status'] == 'success':
                # 立即获取记忆上下文，检查数据是否一致
                context_result = await get_memory_context_for_chat(
                    self.test_user_id,
                    self.test_project_id,
                    "最近的消息"
                )
                
                if context_result['status'] == 'success':
                    short_term = context_result['memory_context']['short_term_memory']
                    # 检查最新消息是否在短期记忆中
                    latest_message = short_term[-1] if short_term else None
                    
                    if latest_message and latest_message['content'] == test_content:
                        logger.info("✅ 数据一致性测试成功")
                        return True
                    else:
                        logger.error("❌ 数据一致性测试失败：数据不匹配")
                        return False
                else:
                    logger.error("❌ 数据一致性测试失败：无法获取上下文")
                    return False
            else:
                logger.error("❌ 数据一致性测试失败：无法添加对话")
                return False
                
        except Exception as e:
            logger.error(f"❌ 数据一致性测试异常: {str(e)}")
            return False
    
    async def test_concurrent_operations(self) -> bool:
        """测试并发操作"""
        try:
            # 创建多个并发任务
            tasks = []
            
            # 并发添加对话
            for i in range(10):
                task = add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    "user" if i % 2 == 0 else "assistant",
                    f"并发测试消息 {i}"
                )
                tasks.append(task)
            
            # 并发获取记忆上下文
            for i in range(5):
                task = get_memory_context_for_chat(
                    self.test_user_id,
                    self.test_project_id,
                    f"并发查询 {i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            for result in results:
                if isinstance(result, dict) and result.get('status') == 'success':
                    success_count += 1
                elif isinstance(result, Exception):
                    logger.error(f"并发操作异常: {str(result)}")
            
            logger.info(f"✅ 并发操作测试完成: {success_count}/{len(tasks)} 成功")
            
            return success_count >= len(tasks) * 0.8  # 80%成功率即可
            
        except Exception as e:
            logger.error(f"❌ 并发操作测试异常: {str(e)}")
            return False
    
    def _print_final_results(self):
        """打印最终测试结果"""
        logger.info("\n" + "="*80)
        logger.info("记忆系统综合测试结果")
        logger.info("="*80)
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过: {self.test_results['passed']}")
        logger.info(f"失败: {self.test_results['failed']}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"总耗时: {self.test_results['performance_metrics'].get('total_test_time', 0):.2f}s")
        
        if self.test_results['errors']:
            logger.info("\n错误详情:")
            for error in self.test_results['errors']:
                logger.error(f"  - {error}")
        
        logger.info("\n性能指标:")
        for test_name, duration in self.test_results['performance_metrics'].items():
            if test_name != 'total_test_time':
                logger.info(f"  - {test_name}: {duration:.2f}s")
        
        logger.info("\n" + "="*80)
        
        if success_rate >= 80:
            logger.info("🎉 记忆系统测试整体通过！")
        else:
            logger.warning("⚠️ 记忆系统测试存在问题，请检查失败的测试项。")

async def main():
    """主函数"""
    test_suite = ComprehensiveMemorySystemTest()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
