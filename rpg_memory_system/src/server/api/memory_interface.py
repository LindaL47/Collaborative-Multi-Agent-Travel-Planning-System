#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RPG记忆系统 - 语聊模块接口

本模块为语聊系统提供直接调用的函数接口，无需通过FastAPI。
包含两个核心函数：
1. add_dialogue_to_memory - 添加对话到记忆系统
2. get_memory_context_for_chat - 获取记忆上下文用于生成回复
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from .controllers.memory_manager import memory_manager
from .models.llm_client import llm_client

# 配置日志记录器
logger = logging.getLogger(__name__)


async def add_dialogue_to_memory(
    user_id: str, 
    project_id: str, 
    role: str, 
    content: str
) -> Dict[str, Any]:
    """
    添加对话到记忆系统
    
    功能说明：
    - 将用户和NPC的对话内容添加到记忆系统的短期记忆中
    - 自动管理短期记忆大小（最多保存60轮对话）
    - 当对话轮数达到60轮时，自动触发记忆处理流水线
    - 记忆处理包括：用户画像更新、事件提取、反思生成
    
    参数说明：
    - user_id (str): 用户唯一标识符，用于区分不同用户的记忆
    - project_id (str): 项目/游戏标识符，用于区分不同游戏场景
    - role (str): 对话角色，"user"表示用户消息，"assistant"表示NPC回复
    - content (str): 对话内容文本
    
    返回数据格式：
    {
        "status": "success",              # 操作状态："success" 或 "error"
        "dialogue_count": 45,             # 当前短期记忆中的对话轮数
        "should_process_memory": false,   # 是否触发了记忆处理
        "memory_processing": {            # 如果触发记忆处理，包含处理结果
            "status": "success",
            "processed_events": 3,
            "processed_reflections": 2
        }
    }
    
    使用示例：
    # 添加用户消息
    result = await add_dialogue_to_memory(
        user_id="user_123",
        project_id="game_world_1", 
        role="user",
        content="你好，我想了解这个世界的历史"
    )
    
    # 添加NPC回复
    result = await add_dialogue_to_memory(
        user_id="user_123",
        project_id="game_world_1",
        role="assistant", 
        content="欢迎来到艾莉亚的世界..."
    )
    """
    try:
        result = await memory_manager.add_dialogue(
            user_id, project_id, role, content
        )
        
        # 记录成功日志
        dialogue_count = result.get('dialogue_count', 0)
        should_process = result.get('should_process_memory', False)
        logger.info(f"记忆插入成功 - 用户ID: {user_id}, 项目ID: {project_id}, "
                   f"角色: {role}, 对话数量: {dialogue_count}, "
                   f"是否触发记忆处理: {should_process}")
        
        # 如果需要处理记忆，自动触发
        if should_process:
            process_result = await memory_manager.process_memory(
                user_id, project_id
            )
            result['memory_processing'] = process_result
            logger.info(f"记忆处理完成 - 用户ID: {user_id}, 项目ID: {project_id}, "
                       f"处理状态: {process_result.get('status')}")
            
        return result
    except Exception as e:
        return {
            'status': 'error', 
            'message': f'添加对话失败: {str(e)}'
        }


async def get_memory_context_for_chat(
    user_id: str, 
    project_id: str, 
    query: str
) -> Dict[str, Any]:
    """
    根据userid和projectid获取记忆上下文
    
    功能说明：
    - 获取用户的短期记忆（最近60轮对话）
    - 获取核心记忆（用户画像、重要事件、核心反思）
    - 基于用户查询进行长期记忆RAG检索
    - 返回格式化的记忆上下文，可直接注入到LLM提示词中
    
    参数说明：
    - user_id (str): 用户唯一标识符
    - project_id (str): 项目/游戏标识符
    - query (str): 用户当前的消息内容，用于触发相关记忆的RAG检索
    
    返回数据格式：
    {
        "status": "success",
        "short_term_memory": [           # 短期记忆：最近的对话历史
            {
                "role": "user",
                "content": "你好，我想了解一下这个世界的历史",
                "timestamp": "1703123456"
            },
            {
                "role": "assistant", 
                "content": "欢迎来到艾莉亚的世界...",
                "timestamp": "1703123460"
            }
        ],
        "core_memory": {                 # 核心记忆：用户画像和重要信息
            "user_profile": {
                "personality": {
                    "curiosity_level": "high",
                    "preferred_interaction_style": "friendly"
                },
                "interests": ["history", "magic", "adventure"],
                "behavior_patterns": {
                    "question_frequency": "high",
                    "exploration_tendency": "strong"
                }
            },
            "core_events": [
                "用户表现出对世界历史的强烈兴趣",
                "用户选择了法师职业路径"
            ],
            "core_reflections": [
                "这个用户似乎是一个知识探索者，喜欢深入了解背景故事"
            ],
            "last_updated": "2023-12-21T10:30:45"
        },
        "long_term_memory_retrieval": {  # 长期记忆：RAG检索结果
            "npc_stories": [
                {
                    "content": "艾莉亚出生在一个古老的魔法家族...",
                    "similarity": 0.89
                }
            ],
            "dialogue_logs": [
                {
                    "content": "之前关于魔法历史的对话片段",
                    "similarity": 0.85
                }
            ],
            "entity_events": [
                {
                    "content": "用户曾经询问过类似的历史问题",
                    "similarity": 0.82
                }
            ],
            "long_term_reflections": [
                {
                    "content": "用户对历史类话题的反应模式分析",
                    "similarity": 0.78
                }
            ]
        },
        "formatted_context_text": "..."  # 格式化的记忆上下文文本，可直接注入提示词
    }
    
    使用示例：
    # 获取记忆上下文
    memory_context = await get_memory_context_for_chat(
        user_id="user_123",
        project_id="game_world_1",
        query="我想了解更多关于魔法的知识"
    )
    
    # 使用格式化的上下文文本
    if memory_context["status"] == "success":
        context_text = memory_context["formatted_context_text"]
        # 将context_text注入到你的LLM提示词中
    """
    try:
        # 记录开始日志
        start_time = time.time()
        query_preview = query[:50] + "..." if len(query) > 50 else query
        logger.info(f"开始获取记忆上下文 - 用户ID: {user_id}, 项目ID: {project_id}, 查询: {query_preview}")
        
        # 获取原始记忆上下文
        logger.info(f"正在从记忆管理器检索记忆 - 用户ID: {user_id}")
        result = await memory_manager.get_memory_context(
            user_id, project_id, query
        )
        
        if result.get('status') != 'success':
            logger.warning(f"记忆管理器检索失败 - 用户ID: {user_id}, 错误: {result.get('message', '未知错误')}")
            return result
        
        # 提取各部分记忆
        short_term_memory = result.get('short_term_memory', [])
        core_memory = result.get('core_memory', {})
        long_term_memory_retrieval = result.get('long_term_memory_retrieval', {})
        
        # 记录检索结果统计
        short_term_count = len(short_term_memory)
        
        # 分析核心记忆组件
        user_profile_available = bool(core_memory.get('user_profile'))
        core_events_count = len(core_memory.get('core_events', []))
        core_reflections_count = len(core_memory.get('core_reflections', []))
        
        # 分析长期记忆检索结果
        entity_events_count = len(long_term_memory_retrieval.get('entity_events', []))
        dialogue_logs_count = len(long_term_memory_retrieval.get('dialogue_logs', []))
        long_term_reflections_count = len(long_term_memory_retrieval.get('long_term_reflections', []))
        npc_stories_count = len(long_term_memory_retrieval.get('npc_stories', []))
        
        logger.info(f"记忆检索统计 - 用户ID: {user_id}, "
                   f"短期记忆: {short_term_count}条, "
                   f"用户画像: {'可用' if user_profile_available else '不可用'}, "
                   f"核心事件: {core_events_count}条, "
                   f"核心反思: {core_reflections_count}条")
                   
        logger.info(f"长期记忆RAG检索统计 - 用户ID: {user_id}, "
                   f"相关事件: {entity_events_count}条, "
                   f"历史对话: {dialogue_logs_count}条, "
                   f"长期反思: {long_term_reflections_count}条, "
                   f"NPC故事: {npc_stories_count}条")
        
        # 构建完整的记忆上下文
        full_memory_context = {
            'core_memory': core_memory,
            **long_term_memory_retrieval  # 展开长期记忆检索结果
        }
        
        # 生成格式化的记忆上下文文本（基于llm_client.py中的逻辑）
        format_start_time = time.time()
        logger.info(f"开始格式化记忆上下文文本 - 用户ID: {user_id}")
        formatted_context_text = _build_formatted_context_text(full_memory_context)
        format_time = time.time() - format_start_time
        
        # 计算总执行时间
        total_time = time.time() - start_time
        context_text_length = len(formatted_context_text)
        
        logger.info(f"记忆上下文获取完成 - 用户ID: {user_id}, "
                   f"格式化文本长度: {context_text_length}字符, "
                   f"格式化耗时: {format_time:.3f}秒, "
                   f"总耗时: {total_time:.3f}秒")
        
        return {
            'status': 'success',
            'short_term_memory': short_term_memory,
            'core_memory': core_memory,
            'long_term_memory_retrieval': long_term_memory_retrieval,
            'formatted_context_text': formatted_context_text
        }
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"获取记忆上下文异常 - 用户ID: {user_id}, 项目ID: {project_id}, 错误: {error_message}")
        return {
            'status': 'error', 
            'message': f'获取记忆上下文失败: {error_message}'
        }


def _build_formatted_context_text(memory_context: Dict[str, Any]) -> str:
    """
    构建格式化的记忆上下文文本
    
    这个函数复制了llm_client.py中第205-267行的记忆上下文构建逻辑，
    生成可以直接注入到LLM提示词中的格式化文本。
    """
    context_text = ""
    if memory_context:
        # 1. 核心记忆（直接注入，无选择性）
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
        
        # 2. 长期记忆RAG检索结果
        context_text += "=== 相关长期记忆 ===\n"
        
        # 相关实体事件
        if memory_context.get('entity_events'):
            context_text += "相关事件记忆:\n"
            for event in memory_context['entity_events'][:10]:  # 只取前10个
                similarity = event.get('similarity', 0)
                context_text += f"- {event['content']} (相似度: {similarity:.2f})\n"
        
        # 相关历史对话记录（上下文对话组）
        if memory_context.get('dialogue_logs'):
            context_text += "\n相关历史对话（上下文连贯）:\n"
            
            # 按锚点对话分组显示，每个锚点及其上下文为一组
            dialogue_logs = memory_context['dialogue_logs']
            anchor_indices = []
            
            # 找到所有锚点对话的索引
            for i, dialogue in enumerate(dialogue_logs):
                if dialogue.get('is_anchor', False):
                    anchor_indices.append(i)
            
            # 按锚点分组显示，最多显示3组
            max_groups = min(3, len(anchor_indices))
            
            for group_idx in range(max_groups):
                anchor_idx = anchor_indices[group_idx]
                
                # 确定当前组的范围：以锚点为中心的上下文对话
                # 向前找4条，向后找5条（包含锚点）
                start_idx = max(0, anchor_idx - 4)
                end_idx = min(len(dialogue_logs), anchor_idx + 6)  # +6是因为包含锚点后还要5条
                
                # 但是要确保不超过10条
                if end_idx - start_idx > 10:
                    if anchor_idx - start_idx >= 4:  # 如果前面有足够的4条
                        end_idx = start_idx + 10
                    else:  # 如果前面不够4条，从锚点开始向后取
                        start_idx = max(0, end_idx - 10)
                
                group_dialogues = dialogue_logs[start_idx:end_idx]
                
                context_text += f"\n对话组 {group_idx + 1}:\n"
                
                for msg in group_dialogues:
                    role_name = "游戏玩家" if msg['role'] == 'user' else "Aliya"
                    similarity = msg.get('similarity', 0)
                    anchor_mark = " [相关]" if msg.get('is_anchor', False) else ""
                    
                    if similarity > 0:
                        context_text += f"  {role_name}: {msg['content']} (相似度: {similarity:.2f}){anchor_mark}\n"
                    else:
                        context_text += f"  {role_name}: {msg['content']}{anchor_mark}\n"
        
        # 相关反思记忆
        if memory_context.get('long_term_reflections'):
            context_text += "\n相关反思记忆:\n"
            for reflection in memory_context['long_term_reflections'][:8]:
                similarity = reflection.get('similarity', 0)
                context_text += f"- {reflection['content']} (相似度: {similarity:.2f})\n"
        
        # 相关NPC故事
        if memory_context.get('npc_stories'):
            context_text += "\n相关NPC故事:\n"
            for story in memory_context['npc_stories'][:2]:
                similarity = story.get('similarity', 0)
                context_text += f"- {story['content']} (相似度: {similarity:.2f})\n"
    
    return context_text


async def initialize_user_memory(user_id: str, project_id: str) -> Dict[str, Any]:
    """
    初始化用户记忆（可选函数）
    
    功能说明：
    - 为新用户初始化记忆系统
    - 创建基础的用户画像和记忆结构
    - 通常在用户首次进入游戏时调用
    
    参数说明：
    - user_id (str): 用户唯一标识符
    - project_id (str): 项目/游戏标识符
    
    返回数据格式：
    {
        "status": "success",
        "message": "用户记忆初始化完成"
    }
    """
    try:
        result = await memory_manager.initialize_user_memory(user_id, project_id)
        return result
    except Exception as e:
        return {
            'status': 'error', 
            'message': f'初始化用户记忆失败: {str(e)}'
        }


# 同步版本的函数（如果语聊系统不支持异步）
def add_dialogue_to_memory_sync(
    user_id: str, 
    project_id: str, 
    role: str, 
    content: str
) -> Dict[str, Any]:
    """
    添加对话到记忆系统（同步版本）
    
    参数和返回值与异步版本相同，适用于不支持异步的语聊系统。
    """
    logger.info(f"开始同步记忆插入 - 用户ID: {user_id}, 项目ID: {project_id}, 角色: {role}")
    result = asyncio.run(add_dialogue_to_memory(user_id, project_id, role, content))
    logger.info(f"同步记忆插入完成 - 用户ID: {user_id}, 状态: {result.get('status')}")
    return result


def get_memory_context_for_chat_sync(
    user_id: str, 
    project_id: str, 
    query: str
) -> Dict[str, Any]:
    """
    获取记忆上下文用于生成NPC回复（同步版本）
    
    参数和返回值与异步版本相同，适用于不支持异步的语聊系统。
    """
    query_preview = query[:50] + "..." if len(query) > 50 else query
    logger.info(f"开始同步获取记忆上下文 - 用户ID: {user_id}, 项目ID: {project_id}, 查询: {query_preview}")
    
    start_time = time.time()
    result = asyncio.run(get_memory_context_for_chat(user_id, project_id, query))
    total_time = time.time() - start_time
    
    status = result.get('status', 'unknown')
    context_length = len(result.get('formatted_context_text', '')) if result.get('formatted_context_text') else 0
    
    logger.info(f"同步获取记忆上下文完成 - 用户ID: {user_id}, "
               f"状态: {status}, "
               f"上下文长度: {context_length}字符, "
               f"总耗时: {total_time:.3f}秒")
    
    return result


def initialize_user_memory_sync(user_id: str, project_id: str) -> Dict[str, Any]:
    """
    初始化用户记忆（同步版本）
    
    参数和返回值与异步版本相同，适用于不支持异步的语聊系统。
    """
    return asyncio.run(initialize_user_memory(user_id, project_id))


# # 使用示例
# if __name__ == "__main__":
#     # 异步使用示例
#     async def example_usage():
#         # 1. 初始化用户记忆
#         init_result = await initialize_user_memory("user_123", "game_world_1")
#         print(f"初始化结果: {init_result}")
        
#         # 2. 添加用户消息
#         add_result = await add_dialogue_to_memory(
#             "user_123", "game_world_1", "user", "你好，我想了解这个世界的历史"
#         )
#         print(f"添加对话结果: {add_result}")
        
#         # 3. 获取记忆上下文
#         context_result = await get_memory_context_for_chat(
#             "user_123", "game_world_1", "你好，我想了解这个世界的历史"
#         )
#         print(f"记忆上下文: {context_result['formatted_context_text']}")
        
#         # 4. 添加NPC回复
#         npc_result = await add_dialogue_to_memory(
#             "user_123", "game_world_1", "assistant", "欢迎来到艾莉亚的世界..."
#         )
#         print(f"添加NPC回复结果: {npc_result}")
    
#     # 同步使用示例
#     def sync_example_usage():
#         # 1. 初始化用户记忆
#         init_result = initialize_user_memory_sync("user_123", "game_world_1")
#         print(f"初始化结果: {init_result}")
        
#         # 2. 添加用户消息
#         add_result = add_dialogue_to_memory_sync(
#             "user_123", "game_world_1", "user", "你好，我想了解这个世界的历史"
#         )
#         print(f"添加对话结果: {add_result}")
        
#         # 3. 获取记忆上下文
#         context_result = get_memory_context_for_chat_sync(
#             "user_123", "game_world_1", "你好，我想了解这个世界的历史"
#         )
#         print(f"记忆上下文: {context_result['formatted_context_text']}")
    
    # 运行示例
    # asyncio.run(example_usage())  # 异步版本
    # sync_example_usage()  # 同步版本