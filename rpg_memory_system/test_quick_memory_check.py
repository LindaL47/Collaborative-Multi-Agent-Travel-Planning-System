#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统快速检查测试

这是一个轻量级的测试文件，用于快速验证记忆系统的核心功能是否正常工作。
适合在开发过程中进行快速检查和调试。

主要测试：
1. 基础连接（Redis + MySQL）
2. 记忆接口基本功能
3. 简单的对话流程
4. 核心组件状态检查
"""

import asyncio
import os
import sys
import time
import logging
from typing import Dict, Any

# 添加项目路径
project_root = os.path.dirname(__file__)
api_path = os.path.join(project_root, 'src', 'server', 'api')
sys.path.insert(0, api_path)

# 配置环境变量（简化版）
os.environ["DATABASE_URL"] = "mysql+aiomysql://aigame_user:aigame_strong_password_123@121.40.249.125:3306/aigame_db"

# 导入核心组件
try:
    from src.server.api.memory_interface import (
        add_dialogue_to_memory,
        get_memory_context_for_chat,
        initialize_user_memory
    )
    from src.server.api.models.redis_client import redis_client
    from src.server.api.models.mysql_database import get_async_db
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在rpg_memory_system目录下运行此测试")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickMemoryTest:
    """快速记忆测试类"""
    
    def __init__(self):
        self.test_user_id = f"quick_test_{int(time.time())}"
        self.test_project_id = f"quick_project_{int(time.time())}"
        
    async def run_quick_check(self):
        """运行快速检查"""
        logger.info("🚀 开始记忆系统快速检查")
        logger.info(f"测试用户: {self.test_user_id}")
        logger.info(f"测试项目: {self.test_project_id}")
        
        tests = [
            ("连接检查", self.check_connections),
            ("初始化测试", self.test_initialization),
            ("对话测试", self.test_dialogue_flow),
            ("上下文测试", self.test_context_retrieval)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n📋 {test_name}...")
                result = await test_func()
                if result:
                    logger.info(f"✅ {test_name} - 通过")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name} - 失败")
            except Exception as e:
                logger.error(f"❌ {test_name} - 异常: {str(e)}")
        
        logger.info(f"\n📊 快速检查结果: {passed}/{total} 通过")
        
        if passed == total:
            logger.info("🎉 记忆系统状态良好！")
        elif passed >= total * 0.75:
            logger.warning("⚠️ 记忆系统基本正常，但有部分问题")
        else:
            logger.error("🚨 记忆系统存在严重问题！")
        
        return passed == total
    
    async def check_connections(self) -> bool:
        """检查基础连接"""
        try:
            # 检查Redis
            await redis_client.connect()
            logger.info("  ✓ Redis连接正常")
            
            # 检查MySQL
            async for db in get_async_db():
                logger.info("  ✓ MySQL连接正常")
                break
            
            return True
        except Exception as e:
            logger.error(f"  ✗ 连接检查失败: {str(e)}")
            return False
    
    async def test_initialization(self) -> bool:
        """测试初始化"""
        try:
            result = await initialize_user_memory(self.test_user_id, self.test_project_id)
            
            if result.get('status') == 'success':
                logger.info("  ✓ 用户记忆初始化成功")
                return True
            else:
                logger.error(f"  ✗ 初始化失败: {result}")
                return False
        except Exception as e:
            logger.error(f"  ✗ 初始化异常: {str(e)}")
            return False
    
    async def test_dialogue_flow(self) -> bool:
        """测试对话流程"""
        try:
            # 添加几条测试对话
            dialogues = [
                {"role": "user", "content": "你好，我是测试用户"},
                {"role": "assistant", "content": "你好！很高兴见到你"},
                {"role": "user", "content": "今天天气怎么样？"},
                {"role": "assistant", "content": "今天天气很好，适合外出"}
            ]
            
            for i, dialogue in enumerate(dialogues):
                result = await add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    dialogue['role'],
                    dialogue['content']
                )
                
                if result.get('status') != 'success':
                    logger.error(f"  ✗ 对话 {i+1} 添加失败")
                    return False
            
            logger.info(f"  ✓ 成功添加 {len(dialogues)} 条对话")
            return True
            
        except Exception as e:
            logger.error(f"  ✗ 对话流程异常: {str(e)}")
            return False
    
    async def test_context_retrieval(self) -> bool:
        """测试上下文获取"""
        try:
            result = await get_memory_context_for_chat(
                self.test_user_id,
                self.test_project_id,
                "最近我们聊了什么？"
            )
            
            if result.get('status') == 'success':
                memory_context = result.get('memory_context', {})
                short_term = memory_context.get('short_term_memory', [])
                
                logger.info(f"  ✓ 成功获取记忆上下文")
                logger.info(f"  ✓ 短期记忆: {len(short_term)} 条")
                logger.info(f"  ✓ 核心记忆: {len(memory_context.get('core_memory', {}))} 项")
                
                return True
            else:
                logger.error(f"  ✗ 上下文获取失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"  ✗ 上下文获取异常: {str(e)}")
            return False

async def main():
    """主函数"""
    tester = QuickMemoryTest()
    success = await tester.run_quick_check()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())