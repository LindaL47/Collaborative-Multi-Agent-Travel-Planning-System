import os
import asyncio
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import json
# from langsmith import traceable
# from langsmith.wrappers import wrap_openai
from langfuse.openai import openai
from langfuse import observe

# 加载环境变量
load_dotenv()

# 配置Langfuse
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_HOST"] = os.getenv("LANGFUSE_HOST", "")

# 从主项目.env文件加载Langfuse配置
if not os.environ.get("LANGFUSE_SECRET_KEY"):
    main_env_path = os.path.join(os.path.dirname(__file__), "../../../../../.env")
    if os.path.exists(main_env_path):
        from dotenv import load_dotenv
        load_dotenv(main_env_path)
        os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
        os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        os.environ["LANGFUSE_HOST"] = os.getenv("LANGFUSE_HOST", "")

class LLMClient:
    """LLM客户端，用于调用豆包模型"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("OPENAI_MODEL")
        self.emb_model = os.getenv("EMB_MODEL") or os.getenv("EMBEDDING_MODEL")
        
        # 创建OpenAI客户端并用Langfuse包装
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=30.0,  # 设置30秒超时
            max_retries=2   # 最多重试2次
        )
        
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入向量"""
        try:
            response = await self.client.embeddings.create(
                model=self.emb_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"生成嵌入向量失败: {e}")
            return []
            
    @observe(name="提取用户画像LLM")
    async def extract_user_profile(self, dialogue_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从对话历史中提取用户画像"""
        try:
            # 构建对话历史文本
            dialogue_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in dialogue_history
            ])
            
            prompt = f"""请分析以下对话历史，提取用户以下信息：
-  个人基本信息（如姓名、年龄、性别、家乡、职业、教育背景等）
-  性格特征（如开朗、内向、乐观、谨慎等）
-  兴趣爱好（如运动、音乐、阅读、游戏、旅行等）
-  行为模式（如作息习惯、沟通方式、决策风格等）
-  偏好设置（如喜欢的颜色、食物、风格、品牌等）
-  社交关系（如家庭成员、朋友、同事等重要人际关系）
- 重要生活经历（如重大事件、成就、挫折等）
-  价值观和信念（如人生观、世界观、宗教信仰等）
- 技能和能力（如专业技能、语言能力、特长等）
- 其他特征（如习惯、癖好、特殊标记等）

对话历史：
{dialogue_text}

输出格式：
请返回JSON格式的用户画像，包含以下字段：
- personal_info: 个人基本信息（如姓名、年龄、性别、家乡、职业、教育背景等）
- personality: 性格特征（如开朗、内向、乐观、谨慎等）
- interests: 兴趣爱好（如运动、音乐、阅读、游戏、旅行等）
- behavior_patterns: 行为模式（如作息习惯、沟通方式、决策风格等）
- preferences: 偏好设置（如喜欢的颜色、食物、风格、品牌等）
- social_relationships: 社交关系（如家庭成员、朋友、同事等重要人际关系）
- life_experiences: 重要生活经历（如重大事件、成就、挫折等）
- values_beliefs: 价值观和信念（如人生观、世界观、宗教信仰等）
- skills_abilities: 技能和能力（如专业技能、语言能力、特长等）
- other_traits: 其他特征（如习惯、癖好、特殊标记等）

注意：如果对话中没有明确提到某个字段的信息，请将该字段设为空数组[]或空字符串""。
只返回JSON，不要其他内容。"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的用户画像分析师，擅长从对话中提取用户特征。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                extra_body={"thinking": {"type": "disabled"}}
            )
            
            result = response.choices[0].message.content.strip()
            return json.loads(result)
            
        except Exception as e:
            print(f"提取用户画像失败: {e}")
            return {}
            
    @observe(name="提取事件LLM")
    async def extract_events(self, dialogue_history: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """从对话历史中提取重大事件和实体事件"""
        try:
            dialogue_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in dialogue_history
            ])
            
            prompt = f"""分析对话，精准提取重要的事件并分类：

{dialogue_text}

要求：
- 只提取真正重要且具体的事件，避免泛泛而谈
- 每类事件最多3-5条，优先质量而非数量
- 事件描述要简洁明确，一句话概括

分类：
1. core_events：与剧情高度相关或用户之间的重大事件，必须是重要的、影响深远的事件
2. entity_events：与用户互动之间的较小事件、日常互动、具体的实体信息等

返回JSON：
{{
  "core_events": ["关键事件1"],
  "entity_events": ["具体互动1"]
}}

只返回JSON，不要其他内容。"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的事件提取分析师，擅长从对话中识别和分类重要事件。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                extra_body={"thinking": {"type": "disabled"}}
            )
            
            result = response.choices[0].message.content.strip()
            events_data = json.loads(result)
            return {
                'core_events': events_data.get('core_events', []),
                'entity_events': events_data.get('entity_events', [])
            }
            
        except Exception as e:
            print(f"提取事件失败: {e}")
            return {'core_events': [], 'entity_events': []}
            
    @observe(name="反思LLM")
    async def generate_reflection(self, dialogue_history: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """生成反思记忆 - 仅基于对话历史"""
        try:
            dialogue_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in dialogue_history
            ])
            
            prompt = f"""请基于以下我与玩家真实的互动历史，以我的口吻和视角，生成自然、简要且带有个人感受的反思，就像真人回忆那样，不夸大不编造：

对话历史：
{dialogue_text}

请生成两类高度凝练的反思：
1. 核心反思（core_reflections）：针对重大事件，反思用户表现出的深层行为模式、关键转变或重大决策
2. 长期反思（long_term_reflections）：基于日常互动的一般性反思，关于用户偏好、习惯、日常行为等

要求：
反思应使用自然口语，带有些许主观但不出事实范围；内容基于真实对话，不抽象过度或偏离原意；每条尽量简短像一闪而过的念头，但切中要害。

请以JSON格式返回，格式如下：
{{
  "core_reflections": ["核心反思1", "核心反思2"],
  "long_term_reflections": ["长期反思1", "长期反思2"]
}}

只返回JSON，不要其他内容。"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "我是Aliya，一个被困在太空等待救援的少女。我会从我们的互动中真诚地回想和总结，形成带有个人视角但尊重事实的反思。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                extra_body={"thinking": {"type": "disabled"}}
            )
            
            result = response.choices[0].message.content.strip()
            reflections_data = json.loads(result)
            return {
                'core_reflections': reflections_data.get('core_reflections', []),
                'long_term_reflections': reflections_data.get('long_term_reflections', [])
            }
            
        except Exception as e:
            print(f"生成反思失败: {e}")
            return {'core_reflections': [], 'long_term_reflections': []}

    @observe(name="总结凝练核心反思/事件LLM")
    async def consolidate_memories(self, memories: List[str], memory_type: str) -> List[str]:
        """
        使用LLM整合核心记忆
        :param memories: 记忆列表
        :param memory_type: 记忆类型 ('事件' 或 '反思')
        :return: 整合后的记忆列表
        """
        if not memories:
            return []

        prompt_template = """
        你是一个AI记忆管理专家。你的任务是分析、合并和提炼一个关于用户的记忆列表。
        请遵循以下步骤：
        1.  **合并相似项**: 将描述相似{memory_type}的多个条目合并成一个更全面、更精确的条目。
        2.  **消除冗余**: 移除完全重复或信息量低的{memory_type}。
        3.  **精简表述**: 在不丢失关键信息的前提下，使每个{memory_type}的描述尽可能简洁。
        4.  **保留核心**: 确保最重要的{memory_type}被保留下来。
        5.  **限制数量**: 最终生成的列表不应超过20个条目。如果原始条目超过20个，请进行筛选和合并。

        这是需要处理的{memory_type}列表:
        ---
        {memory_list}
        ---

        请将处理后的结果以JSON格式返回，格式如下:
        {{"consolidated_memories": ["合并后的{memory_type}1", "合并后的{memory_type}2", ...]}}
        """
        
        try:
            memory_list_str = "\n".join(f"- {item}" for item in memories)
            prompt = prompt_template.format(memory_type=memory_type, memory_list=memory_list_str)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                extra_body={"thinking": {"type": "disabled"}}
            )
            
            result_json = json.loads(response.choices[0].message.content)
            consolidated = result_json.get("consolidated_memories", [])
            
            # 双重保障，确保列表不超过40条
            return consolidated[:40]

        except Exception as e:
            print(f"整合记忆失败: {e}")
            # 出错时返回原始列表的前40条作为降级方案
            return memories[:40]

    @observe(name="生成回复")
    async def generate_npc_response(self, user_message: str, dialogue_history: List[Dict[str, Any]], 
                                   memory_context: Dict[str, Any] = None) -> str:
        """生成NPC回复"""
        try:
            # 构建对话历史文本 - 使用完整的短期记忆（最多60轮）
            history_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in dialogue_history  # 使用完整的对话历史
            ])
            
            # 构建记忆上下文文本
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
                    for event in memory_context['entity_events'][:3]:  # 只取前3个
                        similarity = event.get('similarity', 0)
                        context_text += f"- {event['content']} (相似度: {similarity:.2f})\n"
                
                # 相关历史对话记录
                if memory_context.get('dialogue_logs'):
                    context_text += "\n相关历史对话:\n"
                    for dialogue in memory_context['dialogue_logs'][:3]:  # 只取前3个
                        role_name = "用户" if dialogue['role'] == 'user' else "助手"
                        similarity = dialogue.get('similarity', 0)
                        context_text += f"- {role_name}: {dialogue['content']} (相似度: {similarity:.2f})\n"
                
                # 相关反思记忆
                if memory_context.get('long_term_reflections'):
                    context_text += "\n相关反思记忆:\n"
                    for reflection in memory_context['long_term_reflections'][:3]:
                        similarity = reflection.get('similarity', 0)
                        context_text += f"- {reflection['content']} (相似度: {similarity:.2f})\n"
                
                # 相关NPC故事
                if memory_context.get('npc_stories'):
                    context_text += "\n相关NPC故事:\n"
                    for story in memory_context['npc_stories'][:2]:
                        similarity = story.get('similarity', 0)
                        context_text += f"- {story['content']} (相似度: {similarity:.2f})\n"
            
            # 构建系统提示
            system_prompt = """你是一个智能的AI助手，能够基于对话历史和记忆上下文进行自然对话。
请根据用户的消息和提供的上下文信息，生成合适的回复。

回复要求：
1. 自然、友好、有帮助
2. 基于提供的记忆上下文进行个性化回复
3. 保持对话的连贯性
4. 回复长度适中，不要过长
5. 如果没有足够的上下文，可以询问更多信息"""
            
            # 构建用户提示
            user_prompt = f"""对话历史：
{history_text}

记忆上下文：
{context_text}

用户最新消息：{user_message}

请生成合适的回复："""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                extra_body={"thinking": {"type": "disabled"}}
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"生成NPC回复失败: {e}")
            return "抱歉，我现在无法回复。请稍后再试。"

# 全局LLM客户端实例
llm_client = LLMClient()