#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证CSV数据导入结果
检查记忆系统中是否正确存储了导入的数据
"""

import asyncio
import sys
import os

# 添加项目路径到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    # 导入记忆接口函数
    from src.server.api.memory_interface import (
        get_memory_context_for_chat
    )
    # 导入Redis客户端
    from src.server.api.models.redis_client import redis_client
    print("[OK] 成功导入记忆接口函数")
except ImportError as e:
    print(f"[ERROR] 导入记忆接口函数失败: {e}")
    print("[INFO] 请确保在rpg_memory_system目录下运行此脚本")
    sys.exit(1)

class ImportVerifier:
    def __init__(self):
        """初始化验证器"""
        self.user_id = "user_1756607314172_cc521arfp"
        self.project_id = f"project_{self.user_id}"
        
        # 初始化Redis连接
        asyncio.run(self._init_redis())
    
    async def _init_redis(self):
        """初始化Redis连接"""
        try:
            await redis_client.connect()
            print("[OK] Redis连接成功")
        except Exception as e:
            print(f"[ERROR] Redis连接失败: {e}")
            raise
    
    async def verify_memory_content(self):
        """验证记忆内容"""
        print("\n" + "="*60)
        print("验证导入的记忆内容")
        print("="*60)
        
        # 测试查询列表
        test_queries = [
            "Kane",
            "Aliya",
            "飞船",
            "动力室",
            "制氧机",
            "培育室",
            "科朗2-B",
            "星球",
            "互联网",
            "哲学",
            "兔子狗",
            "COSMOS"
        ]
        
        try:
            for i, query in enumerate(test_queries):
                print(f"\n[{i+1}/{len(test_queries)}] 查询: '{query}'")
                
                result = await get_memory_context_for_chat(
                    self.user_id, self.project_id, query
                )
                
                if result.get('status') == 'success':
                    context = result.get('context', {})
                    
                    # 短期记忆
                    short_term = context.get('short_term_memory', [])
                    print(f"  短期记忆: {len(short_term)} 条")
                    
                    # 长期记忆检索
                    long_term = context.get('long_term_memory_retrieval', [])
                    print(f"  长期记忆检索: {len(long_term)} 条")
                    
                    # 核心记忆
                    core_memory = context.get('core_memory', {})
                    if core_memory:
                        user_profile = core_memory.get('user_profile', {})
                        important_events = core_memory.get('important_events', [])
                        core_reflections = core_memory.get('core_reflections', [])
                        
                        print(f"  核心记忆 - 用户画像: {'有' if user_profile else '无'}")
                        print(f"  核心记忆 - 重要事件: {len(important_events)} 个")
                        print(f"  核心记忆 - 核心反思: {len(core_reflections)} 个")
                    
                    # 显示一些具体内容
                    if short_term:
                        latest = short_term[-1]
                        content = latest.get('content', '')[:100]
                        print(f"  最新对话预览: {content}...")
                    
                    if long_term:
                        for j, memory in enumerate(long_term[:2]):
                            if isinstance(memory, dict):
                                mem_content = str(memory.get('content', ''))[:80]
                                print(f"  相关记忆{j+1}: {mem_content}...")
                    
                else:
                    print(f"  [ERROR] 查询失败: {result.get('message')}")
                
                # 短暂暂停
                await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 验证过程异常: {e}")
            return False
    
    async def get_memory_statistics(self):
        """获取记忆统计信息"""
        print("\n" + "="*60)
        print("记忆系统统计信息")
        print("="*60)
        
        try:
            # 使用一个通用查询来获取完整的记忆上下文
            result = await get_memory_context_for_chat(
                self.user_id, self.project_id, "总结一下我们的对话"
            )
            
            if result.get('status') == 'success':
                context = result.get('context', {})
                
                # 统计各类记忆数量
                short_term = context.get('short_term_memory', [])
                long_term = context.get('long_term_memory_retrieval', [])
                core_memory = context.get('core_memory', {})
                
                print(f"短期记忆总数: {len(short_term)}")
                print(f"长期记忆检索结果: {len(long_term)}")
                
                if core_memory:
                    user_profile = core_memory.get('user_profile', {})
                    important_events = core_memory.get('important_events', [])
                    core_reflections = core_memory.get('core_reflections', [])
                    
                    print(f"用户画像: {'已生成' if user_profile else '未生成'}")
                    print(f"重要事件数: {len(important_events)}")
                    print(f"核心反思数: {len(core_reflections)}")
                    
                    # 显示用户画像内容
                    if user_profile:
                        print("\n用户画像内容:")
                        for key, value in user_profile.items():
                            print(f"  {key}: {str(value)[:200]}...")
                    
                    # 显示重要事件
                    if important_events:
                        print("\n重要事件:")
                        for i, event in enumerate(important_events[:3]):
                            print(f"  {i+1}. {str(event)[:150]}...")
                    
                    # 显示核心反思
                    if core_reflections:
                        print("\n核心反思:")
                        for i, reflection in enumerate(core_reflections[:3]):
                            print(f"  {i+1}. {str(reflection)[:150]}...")
                
                # 显示格式化文本长度
                formatted_text = context.get('formatted_context_text', '')
                print(f"\n格式化记忆文本长度: {len(formatted_text)} 字符")
                
                return True
            else:
                print(f"[ERROR] 获取统计信息失败: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 统计信息获取异常: {e}")
            return False


async def main():
    """主函数"""
    print("CSV导入结果验证程序")
    print(f"验证用户: user_1756607314172_cc521arfp")
    
    verifier = ImportVerifier()
    
    try:
        # 验证记忆内容
        await verifier.verify_memory_content()
        
        # 获取统计信息
        await verifier.get_memory_statistics()
        
        print("\n[SUCCESS] 验证完成！")
        
    except Exception as e:
        print(f"\n[ERROR] 验证异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())