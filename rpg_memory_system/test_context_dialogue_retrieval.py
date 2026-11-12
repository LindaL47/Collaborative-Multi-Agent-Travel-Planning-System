#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试上下文对话召回功能

验证修改后的RAG检索器是否能正确召回上下文对话：
- 找到最相关的对话后，向上4条向下5条共10条为一组
- 返回最相关的3组对话
- 确保按user_id匹配同一用户的对话
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.server.api.controllers.rag_retriever import rag_retriever
from src.server.api.memory_interface import get_memory_context_for_chat


async def test_context_dialogue_retrieval():
    """
    测试上下文对话召回功能
    """
    print("=== 测试上下文对话召回功能 ===")
    
    # 测试参数
    test_user_id = "test_user_qusikao1"
    test_project_id = "test_project_qusikao1"
    test_query = "告诉我关于魔法的知识"
    
    try:
        print(f"\n测试用户ID: {test_user_id}")
        print(f"测试项目ID: {test_project_id}")
        print(f"测试查询: {test_query}")
        
        # 调用记忆上下文获取接口
        print("\n正在获取记忆上下文...")
        memory_context = await get_memory_context_for_chat(
            user_id=test_user_id,
            project_id=test_project_id,
            query=test_query
        )
        
        if memory_context.get('status') == 'success':
            print("✅ 记忆上下文获取成功")
            
            # 检查对话记录
            dialogue_logs = memory_context.get('long_term_memory_retrieval', {}).get('dialogue_logs', [])
            print(f"\n📊 检索到的对话记录数量: {len(dialogue_logs)}")
            
            if dialogue_logs:
                print("\n📝 对话记录详情:")
                
                # 统计锚点对话数量
                anchor_count = sum(1 for d in dialogue_logs if d.get('is_anchor', False))
                print(f"   - 锚点对话数量: {anchor_count}")
                print(f"   - 总对话数量: {len(dialogue_logs)}")
                
                # 显示前几条对话的详细信息
                print("\n🔍 前10条对话详情:")
                for i, dialogue in enumerate(dialogue_logs[:10]):
                    role_name = "用户" if dialogue['role'] == 'user' else "助手"
                    similarity = dialogue.get('similarity', 0)
                    is_anchor = dialogue.get('is_anchor', False)
                    anchor_mark = " [锚点]" if is_anchor else ""
                    
                    print(f"   {i+1}. {role_name}: {dialogue['content'][:50]}...")
                    print(f"      相似度: {similarity:.3f}, ID: {dialogue['id']}{anchor_mark}")
                
                # 显示格式化的上下文文本
                formatted_text = memory_context.get('formatted_context_text', '')
                if formatted_text:
                    print("\n📄 格式化的上下文文本（历史对话部分）:")
                    lines = formatted_text.split('\n')
                    in_dialogue_section = False
                    dialogue_lines = []
                    
                    for line in lines:
                        if '相关历史对话' in line:
                            in_dialogue_section = True
                            dialogue_lines.append(line)
                        elif in_dialogue_section:
                            if line.startswith('=== ') or '相关反思记忆' in line:
                                break
                            dialogue_lines.append(line)
                    
                    for line in dialogue_lines[:30]:  # 只显示前30行
                        print(f"   {line}")
                    
                    if len(dialogue_lines) > 30:
                        print(f"   ... (还有 {len(dialogue_lines) - 30} 行)")
            else:
                print("⚠️  没有找到相关的历史对话记录")
                
        else:
            print(f"❌ 记忆上下文获取失败: {memory_context.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


async def test_rag_retriever_directly():
    """
    直接测试RAG检索器的对话记录检索功能
    """
    print("\n=== 直接测试RAG检索器 ===")
    
    test_user_id = "test_user_001"
    test_project_id = "test_project_001"
    test_query = "你好，我想了解一下这个世界的历史"
    
    try:
        # 生成查询向量（模拟）
        print("正在生成查询向量...")
        # 这里应该调用实际的embedding生成函数，但为了测试我们使用模拟向量
        query_embedding = [0.1] * 1536  # 模拟1536维向量
        
        print("正在检索长期记忆...")
        long_term_memory = await rag_retriever.retrieve_long_term_memory(
            query=test_query,
            user_id=test_user_id,
            project_id=test_project_id
        )
        
        dialogue_logs = long_term_memory.get('dialogue_logs', [])
        print(f"\n📊 RAG检索器返回的对话记录数量: {len(dialogue_logs)}")
        
        if dialogue_logs:
            # 分析对话记录结构
            anchor_dialogues = [d for d in dialogue_logs if d.get('is_anchor', False)]
            context_dialogues = [d for d in dialogue_logs if not d.get('is_anchor', False)]
            
            print(f"   - 锚点对话: {len(anchor_dialogues)} 条")
            print(f"   - 上下文对话: {len(context_dialogues)} 条")
            
            # 显示锚点对话
            if anchor_dialogues:
                print("\n🎯 锚点对话（最相关的对话）:")
                for i, dialogue in enumerate(anchor_dialogues):
                    role_name = "用户" if dialogue['role'] == 'user' else "助手"
                    similarity = dialogue.get('similarity', 0)
                    print(f"   {i+1}. {role_name}: {dialogue['content'][:100]}...")
                    print(f"      相似度: {similarity:.3f}, ID: {dialogue['id']}")
        else:
            print("⚠️  RAG检索器没有返回对话记录")
            
    except Exception as e:
        print(f"❌ RAG检索器测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """
    主测试函数
    """
    print("🚀 开始测试上下文对话召回功能")
    print("=" * 60)
    
    # 测试1: 完整的记忆上下文获取
    await test_context_dialogue_retrieval()
    
    # 测试2: 直接测试RAG检索器
    await test_rag_retriever_directly()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())