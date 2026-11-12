#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统功能测试

测试新修改的功能：
1. 定时处理机制
2. 核心记忆修复
3. LangSmith监控集成
"""

import asyncio
import os
import sys
import time
import logging
from typing import Dict, Any, List

# 添加项目路径
project_root = os.path.dirname(__file__)
api_path = os.path.join(project_root, 'src', 'server', 'api')
sys.path.insert(0, api_path)

# 配置Langfuse环境变量
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-686b3638-8ce2-4824-a259-48b6a79aca15"
os.environ["LANGFUSE_HOST"] = "http://121.40.249.125:3000"

# 配置数据库连接
os.environ["DATABASE_URL"] = "mysql+aiomysql://aigame_user:aigame_strong_password_123@121.40.249.125:3306/aigame_db"

# 导入记忆接口
try:
    from src.server.api.memory_interface import (
        add_dialogue_to_memory,
        get_memory_context_for_chat,
        initialize_user_memory
    )
    from src.server.api.controllers.memory_timer import memory_timer
    from src.server.api.models.llm_client import llm_client
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

class MemoryFeatureTest:
    """记忆功能测试类"""
    
    def __init__(self):
        self.test_user_id = "test_redis_001"
        self.test_project_id = "test_redis_001"
        self.test_results = []
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始记忆系统功能测试")
        
        try:
            # 测试1: 初始化用户记忆
            await self.test_initialize_memory()
            
            # 测试2: 添加对话并触发记忆处理
            await self.test_dialogue_and_memory_processing()
            
            # 测试3: 测试记忆上下文获取和Langfuse监控
            await self.test_memory_context_with_langfuse()
            
            # 测试4: 测试定时器功能
            await self.test_timer_functionality()
            
            # 测试5: 测试核心记忆修复
            await self.test_core_memory_fix()
            
            # 输出测试结果
            self.print_test_results()
            
        except Exception as e:
            logger.error(f"测试执行异常: {e}")
            raise
    
    async def test_initialize_memory(self):
        """测试1: 初始化用户记忆"""
        logger.info("=== 测试1: 初始化用户记忆 ===")
        
        try:
            result = await initialize_user_memory(self.test_user_id, self.test_project_id)
            
            success = result.get('status') == 'success'
            self.test_results.append({
                'test_name': '初始化用户记忆',
                'success': success,
                'result': result
            })
            
            logger.info(f"初始化结果: {result}")
            
        except Exception as e:
            logger.error(f"初始化测试失败: {e}")
            self.test_results.append({
                'test_name': '初始化用户记忆',
                'success': False,
                'error': str(e)
            })
    
    async def test_dialogue_and_memory_processing(self):
        """测试2: 添加对话并触发记忆处理"""
        logger.info("=== 测试2: 添加对话并触发记忆处理 ===")
        
        # 模拟多轮对话，达到触发记忆处理的阈值
        test_dialogues = [
            ("user", "你好，我是一个新玩家，想了解这个世界的背景故事"),
            ("assistant", "欢迎来到艾莉亚的世界！这是一个充满魔法和冒险的奇幻大陆..."),
            ("user", "听起来很有趣！我想选择法师职业，可以告诉我更多关于魔法的知识吗？"),
            ("assistant", "法师是一个非常强大的职业！在艾莉亚世界中，魔法分为元素魔法、治疗魔法和暗黑魔法..."),
            ("user", "我对元素魔法特别感兴趣，特别是火系魔法"),
            ("assistant", "火系魔法是元素魔法中最具攻击性的分支，需要强大的意志力来控制..."),
        ]
        
        # 添加更多对话以达到处理阈值
        for i in range(30):
            test_dialogues.extend([
                ("user", f"我想了解更多关于魔法修炼的知识，第{i+1}个问题"),
                ("assistant", f"关于魔法修炼，这是第{i+1}个回答，包含了重要的修炼要点...")
            ])
        
        try:
            dialogue_count = 0
            memory_processed = False
            
            for role, content in test_dialogues:
                result = await add_dialogue_to_memory(
                    self.test_user_id, self.test_project_id, role, content
                )
                
                dialogue_count = result.get('dialogue_count', 0)
                should_process = result.get('should_process_memory', False)
                
                if (dialogue_count % 10 == 0) or should_process:
                    logger.info(f"添加对话 - 角色: {role}, 对话数: {dialogue_count}, 是否触发处理: {should_process}")
                
                if should_process:
                    memory_processed = True
                    logger.info(f"记忆处理被触发！处理结果: {result.get('memory_processing')}")
                    break
                
                # 短暂延迟
                await asyncio.sleep(0.1)
            
            self.test_results.append({
                'test_name': '对话添加和记忆处理',
                'success': memory_processed,
                'dialogue_count': dialogue_count,
                'memory_processed': memory_processed
            })
            
        except Exception as e:
            logger.error(f"对话测试失败: {e}")
            self.test_results.append({
                'test_name': '对话添加和记忆处理',
                'success': False,
                'error': str(e)
            })
    
    async def test_memory_context_with_langfuse(self):
        """测试3: 测试记忆上下文获取和Langfuse监控"""
        logger.info("=== 测试3: 记忆上下文获取和Langfuse监控 ===")
        
        test_queries = [
            "我想了解更多关于火系魔法的高级技能",
            "告诉我关于这个世界的历史和传说",
            "我应该如何提升我的魔法能力？"
        ]
        
        try:
            for i, query in enumerate(test_queries, 1):
                logger.info(f"\n--- 查询 {i}: {query} ---")
                
                # 获取记忆上下文
                result = await get_memory_context_for_chat(
                    self.test_user_id, self.test_project_id, query
                )
                
                if result.get('status') == 'success':
                    # 打印完整的记忆上下文（用于后端日志监控）
                    self.print_complete_memory_context(result, query)
                    
                    # 分析记忆组成
                    self.analyze_memory_composition(result)
                    
                    # 测试完整的LLM调用和Langfuse监控
                    await self.test_llm_call_with_langfuse(query, result)
                    
                else:
                    logger.error(f"获取记忆上下文失败: {result.get('message')}")
                
                await asyncio.sleep(2)  # 延迟以便观察Langfuse
            
            self.test_results.append({
                'test_name': '记忆上下文获取和Langfuse监控',
                'success': True,
                'queries_tested': len(test_queries)
            })
            
        except Exception as e:
            logger.error(f"记忆上下文测试失败: {e}")
            self.test_results.append({
                'test_name': '记忆上下文获取和Langfuse监控',
                'success': False,
                'error': str(e)
            })
    
    def print_complete_memory_context(self, result: Dict[str, Any], query: str):
        """打印完整的记忆上下文（用于后端日志监控）"""
        logger.info("\n" + "="*80)
        logger.info(f"完整记忆上下文 - 查询: {query}")
        logger.info("="*80)
        
        # 打印格式化的上下文文本
        formatted_text = result.get('formatted_context_text', '')
        if formatted_text:
            logger.info("\n【完整组装的提示词内容】:")
            logger.info(formatted_text)
        
        # 打印详细的记忆组成
        logger.info("\n【记忆组成详情】:")
        
        # 短期记忆
        short_term = result.get('short_term_memory', [])
        logger.info(f"短期记忆: {len(short_term)}条")
        
        # 核心记忆
        core_memory = result.get('core_memory', {})
        logger.info("核心记忆:")
        logger.info(f"  - 用户画像: {'有' if core_memory.get('user_profile') else '无'}")
        logger.info(f"  - 核心事件: {len(core_memory.get('core_events', []))}条")
        logger.info(f"  - 核心反思: {len(core_memory.get('core_reflections', []))}条")
        
        # 长期记忆检索结果
        long_term = result.get('long_term_memory_retrieval', {})
        logger.info("相关长期记忆:")
        logger.info(f"  - 相关事件: {len(long_term.get('entity_events', []))}条")
        logger.info(f"  - 历史对话: {len(long_term.get('dialogue_logs', []))}条")
        logger.info(f"  - 长期反思: {len(long_term.get('long_term_reflections', []))}条")
        logger.info(f"  - NPC故事: {len(long_term.get('npc_stories', []))}条")
        
        logger.info("="*80 + "\n")
    
    def analyze_memory_composition(self, result: Dict[str, Any]):
        """分析记忆组成"""
        core_memory = result.get('core_memory', {})
        long_term = result.get('long_term_memory_retrieval', {})
        
        # 检查核心记忆是否正常
        has_user_profile = bool(core_memory.get('user_profile'))
        has_core_events = len(core_memory.get('core_events', [])) > 0
        has_core_reflections = len(core_memory.get('core_reflections', [])) > 0
        
        # 检查长期记忆是否正常
        has_entity_events = len(long_term.get('entity_events', [])) > 0
        has_dialogue_logs = len(long_term.get('dialogue_logs', [])) > 0
        has_long_reflections = len(long_term.get('long_term_reflections', [])) > 0
        has_npc_stories = len(long_term.get('npc_stories', [])) > 0
        
        logger.info("\n【记忆组成分析】:")
        logger.info(f"核心记忆状态: 用户画像={has_user_profile}, 核心事件={has_core_events}, 核心反思={has_core_reflections}")
        logger.info(f"长期记忆状态: 相关事件={has_entity_events}, 历史对话={has_dialogue_logs}, 长期反思={has_long_reflections}, NPC故事={has_npc_stories}")
        
        # 验证核心记忆修复是否生效
        if has_user_profile or has_core_events or has_core_reflections:
            logger.info("✅ 核心记忆修复成功 - 能够正常获取核心记忆数据")
        else:
            logger.warning("❌ 核心记忆可能仍有问题 - 无法获取核心记忆数据")
    
    async def test_llm_call_with_langfuse(self, query: str, memory_context: Dict[str, Any]):
        """测试LLM调用和Langfuse监控"""
        logger.info(f"\n=== LLM调用测试 - 查询: {query} ===")
        
        try:
            # 模拟短期记忆（对话历史）
            dialogue_history = [
                {"role": "user", "content": "你好，我是一个新玩家，想了解这个世界的背景故事"},
                {"role": "assistant", "content": "欢迎来到艾莉亚的世界！这是一个充满魔法和冒险的奇幻大陆..."},
                {"role": "user", "content": "听起来很有趣！我想选择法师职业，可以告诉我更多关于魔法的知识吗？"},
                {"role": "assistant", "content": "法师是一个非常强大的职业！在艾莉亚世界中，魔法分为元素魔法、治疗魔法和暗黑魔法..."},
                {"role": "user", "content": query}
            ]
            
            # 调用LLM生成回复（这将被Langfuse监控）
            logger.info("\n🤖 调用LLM生成回复（Langfuse监控中...）")
            
            # 打印完整的提示词内容（用于后端日志监控）
            self.print_complete_prompt_for_llm(query, dialogue_history, memory_context)
            
            # 实际调用LLM
            npc_response = await llm_client.generate_npc_response(
                query, dialogue_history, memory_context
            )
            
            logger.info(f"\n📝 LLM生成的回复: {npc_response}")
            logger.info("\n📊 Langfuse监控信息:")
            logger.info(f"   - Host: {os.environ.get('LANGFUSE_HOST')}")
            logger.info(f"   - Public Key: {os.environ.get('LANGFUSE_PUBLIC_KEY')[:20]}...")
            logger.info("   - 请在Langfuse平台查看完整的调用链和记忆组装过程")
            
        except Exception as e:
            logger.error(f"LLM调用测试失败: {e}")
    
    def print_complete_prompt_for_llm(self, query: str, dialogue_history: List[Dict[str, Any]], 
                                     memory_context: Dict[str, Any]):
        """打印发送给LLM的完整提示词内容"""
        logger.info("\n" + "="*100)
        logger.info("完整的LLM提示词内容（后端日志监控）")
        logger.info("="*100)
        
        # 1. 系统提示
        system_prompt = """你是一个智能的AI助手，能够基于对话历史和记忆上下文进行自然对话。
请根据用户的消息和提供的上下文信息，生成合适的回复。

回复要求：
1. 自然、友好、有帮助
2. 基于提供的记忆上下文进行个性化回复
3. 保持对话的连贯性
4. 回复长度适中，不要过长
5. 如果没有足够的上下文，可以询问更多信息"""
        
        logger.info("\n【系统提示】:")
        logger.info(system_prompt)
        
        # 2. 对话历史
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in dialogue_history
        ])
        
        logger.info("\n【对话历史】:")
        logger.info(history_text)
        
        # 3. 记忆上下文
        context_text = ""
        if memory_context:
            # 核心记忆
            core_memory = memory_context.get('core_memory', {})
            if core_memory:
                context_text += "=== 核心记忆 ===\n"
                
                # 用户画像
                user_profile = core_memory.get('user_profile', {})
                if user_profile:
                    context_text += "用户画像:\n"
                    for key, value in user_profile.items():
                        if value:
                            context_text += f"- {key}: {value}\n"
                
                # 核心事件
                core_events = core_memory.get('core_events', [])
                if core_events:
                    context_text += "\n核心事件:\n"
                    for event in core_events:
                        context_text += f"- {event}\n"
                
                # 核心反思
                core_reflections = core_memory.get('core_reflections', [])
                if core_reflections:
                    context_text += "\n核心反思:\n"
                    for reflection in core_reflections:
                        context_text += f"- {reflection}\n"
                
                context_text += "\n"
            
            # 长期记忆RAG检索结果
            long_term = memory_context.get('long_term_memory_retrieval', {})
            if long_term:
                context_text += "=== 相关长期记忆 ===\n"
                
                # 相关实体事件
                if long_term.get('entity_events'):
                    context_text += "相关事件记忆:\n"
                    for event in long_term['entity_events'][:3]:
                        similarity = event.get('similarity', 0)
                        context_text += f"- {event['content']} (相似度: {similarity:.2f})\n"
                
                # 相关历史对话记录
                if long_term.get('dialogue_logs'):
                    context_text += "\n相关历史对话:\n"
                    for dialogue in long_term['dialogue_logs'][:3]:
                        role_name = "用户" if dialogue['role'] == 'user' else "助手"
                        similarity = dialogue.get('similarity', 0)
                        context_text += f"- {role_name}: {dialogue['content']} (相似度: {similarity:.2f})\n"
                
                # 相关反思记忆
                if long_term.get('long_term_reflections'):
                    context_text += "\n相关反思记忆:\n"
                    for reflection in long_term['long_term_reflections'][:3]:
                        similarity = reflection.get('similarity', 0)
                        context_text += f"- {reflection['content']} (相似度: {similarity:.2f})\n"
                
                # 相关NPC故事
                if long_term.get('npc_stories'):
                    context_text += "\n相关NPC故事:\n"
                    for story in long_term['npc_stories'][:2]:
                        similarity = story.get('similarity', 0)
                        context_text += f"- {story['content']} (相似度: {similarity:.2f})\n"
        
        logger.info("\n【记忆上下文】:")
        logger.info(context_text if context_text else "无记忆上下文")
        
        # 4. 用户查询
        logger.info(f"\n【用户最新消息】: {query}")
        
        # 5. 完整的用户提示
        user_prompt = f"""对话历史：
{history_text}

记忆上下文：
{context_text}

用户最新消息：{query}

请生成合适的回复："""
        
        logger.info("\n【完整用户提示】:")
        logger.info(user_prompt)
        
        logger.info("="*100 + "\n")
    
    async def test_timer_functionality(self):
        """测试4: 测试定时器功能"""
        logger.info("=== 测试4: 定时器功能测试 ===")
        
        try:
            # 获取定时器状态
            status = memory_timer.get_status()
            logger.info(f"定时器状态: {status}")
            
            # 模拟用户活动
            memory_timer.update_user_activity("timer_test_user", "timer_test_project")
            logger.info("已更新测试用户活动时间")
            
            # 再次获取状态
            updated_status = memory_timer.get_status()
            logger.info(f"更新后定时器状态: {updated_status}")
            
            self.test_results.append({
                'test_name': '定时器功能',
                'success': status.get('running', False),
                'timer_status': status
            })
            
        except Exception as e:
            logger.error(f"定时器测试失败: {e}")
            self.test_results.append({
                'test_name': '定时器功能',
                'success': False,
                'error': str(e)
            })
    
    async def test_core_memory_fix(self):
        """测试5: 测试核心记忆修复"""
        logger.info("=== 测试5: 核心记忆修复测试 ===")
        
        try:
            # 添加一些对话以生成记忆
            await add_dialogue_to_memory(
                "core_test_user", "core_test_project", 
                "user", "我是一个喜欢探索的冒险者，对古老的魔法很感兴趣"
            )
            
            await add_dialogue_to_memory(
                "core_test_user", "core_test_project", 
                "assistant", "我看得出你是一个充满好奇心的探索者！古老魔法确实很神秘..."
            )
            
            # 等待一段时间让记忆处理完成
            await asyncio.sleep(2)
            
            # 获取记忆上下文，检查核心记忆是否正常
            result = await get_memory_context_for_chat(
                "core_test_user", "core_test_project", 
                "告诉我更多关于古老魔法的知识"
            )
            
            if result.get('status') == 'success':
                core_memory = result.get('core_memory', {})
                has_core_data = (
                    bool(core_memory.get('user_profile')) or
                    len(core_memory.get('core_events', [])) > 0 or
                    len(core_memory.get('core_reflections', [])) > 0
                )
                
                logger.info(f"核心记忆修复测试结果: {'成功' if has_core_data else '失败'}")
                logger.info(f"核心记忆内容: {core_memory}")
                
                self.test_results.append({
                    'test_name': '核心记忆修复',
                    'success': has_core_data,
                    'core_memory_available': has_core_data
                })
            else:
                logger.error(f"获取核心记忆失败: {result.get('message')}")
                self.test_results.append({
                    'test_name': '核心记忆修复',
                    'success': False,
                    'error': result.get('message')
                })
                
        except Exception as e:
            logger.error(f"核心记忆修复测试失败: {e}")
            self.test_results.append({
                'test_name': '核心记忆修复',
                'success': False,
                'error': str(e)
            })
    
    def print_test_results(self):
        """打印测试结果"""
        logger.info("\n" + "="*60)
        logger.info("测试结果汇总")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get('success', False))
        
        for i, result in enumerate(self.test_results, 1):
            status = "✅ 通过" if result.get('success', False) else "❌ 失败"
            logger.info(f"{i}. {result['test_name']}: {status}")
            
            if not result.get('success', False) and 'error' in result:
                logger.info(f"   错误: {result['error']}")
        
        logger.info(f"\n总计: {passed_tests}/{total_tests} 测试通过")
        logger.info("="*60)
        
        # LangSmith监控提示
        logger.info("\n📊 LangSmith监控信息:")
        logger.info(f"项目: {os.environ.get('LANGSMITH_PROJECT')}")
        logger.info(f"端点: {os.environ.get('LANGSMITH_ENDPOINT')}")
        logger.info("请在LangSmith平台查看完整的记忆组装过程和LLM调用详情")


async def main():
    """主函数"""
    logger.info("启动记忆系统功能测试")
    
    # 创建测试实例
    test = MemoryFeatureTest()
    
    try:
        # 运行所有测试
        await test.run_all_tests()
        
        logger.info("\n🎉 所有测试完成！")
        logger.info("请检查:")
        logger.info("1. 后端日志中的完整提示词内容")
        logger.info("2. LangSmith平台上的记忆组装监控数据")
        logger.info("3. 定时器功能是否正常运行")
        logger.info("4. 核心记忆是否能正常获取")
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        raise


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
