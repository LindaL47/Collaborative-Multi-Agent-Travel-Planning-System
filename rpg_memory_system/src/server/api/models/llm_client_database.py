import os
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json
# from langsmith import traceable
# from langsmith.wrappers import wrap_openai
from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
from langfuse.decorators import observe

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

class DatabasePromptManager:
    """数据库提示词管理器"""
    
    def __init__(self):
        self.prompt_cache = {}
        
    async def get_prompt_from_database(self, template_key: str) -> Optional[Dict[str, Any]]:
        """从数据库获取提示词模板"""
        try:
            # 导入数据库连接（避免循环导入）
            from ..models.mysql_database import get_db
            
            db = next(get_db())
            
            # 查询当前发布的提示词版本
            query = """
            SELECT 
                pt.template_key,
                pt.template_name,
                pt.template_type,
                pv.content,
                pv.variables,
                pv.version_number
            FROM prompt_templates pt
            JOIN prompt_versions pv ON pt.id = pv.template_id
            WHERE pt.template_key = %s 
              AND pv.is_current_published = 1
            """
            
            result = db.execute(query, (template_key,)).fetchone()
            
            if result:
                # 解析variables JSON
                variables = {}
                if result[4]:  # variables字段
                    try:
                        variables = json.loads(result[4])
                    except json.JSONDecodeError:
                        variables = {}
                
                return {
                    'template_key': result[0],
                    'template_name': result[1],
                    'template_type': result[2],
                    'content': result[3],
                    'variables': variables,
                    'version_number': result[5]
                }
            else:
                print(f"未找到提示词模板: {template_key}")
                return None
                
        except Exception as e:
            print(f"从数据库获取提示词失败 {template_key}: {e}")
            return None
    
    async def get_cached_prompt(self, template_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的提示词，如果不存在则从数据库加载"""
        if template_key not in self.prompt_cache:
            prompt_data = await self.get_prompt_from_database(template_key)
            if prompt_data:
                self.prompt_cache[template_key] = prompt_data
        
        return self.prompt_cache.get(template_key)
    
    def clear_cache(self):
        """清理提示词缓存"""
        self.prompt_cache.clear()


class LLMClient:
    """LLM客户端，用于调用豆包模型 - 支持数据库提示词"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("OPENAI_MODEL")
        self.emb_model = os.getenv("EMB_MODEL") or os.getenv("EMBEDDING_MODEL")
        
        # 创建OpenAI客户端并用Langfuse包装
        self.client = LangfuseAsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=30.0,  # 设置30秒超时
            max_retries=2   # 最多重试2次
        )
        
        # 初始化数据库提示词管理器
        self.prompt_manager = DatabasePromptManager()
        
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
    
    async def _call_llm_with_prompt_template(self, template_key: str, variables: Dict[str, Any]) -> str:
        """使用数据库提示词模板调用LLM"""
        try:
            # 从数据库获取提示词模板
            prompt_data = await self.prompt_manager.get_cached_prompt(template_key)
            if not prompt_data:
                raise Exception(f"未找到提示词模板: {template_key}")
            
            # 格式化提示词内容
            prompt_content = prompt_data['content']
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                prompt_content = prompt_content.replace(placeholder, str(var_value))
            
            # 获取模板配置的变量
            template_vars = prompt_data.get('variables', {})
            system_message = template_vars.get('system_message', '')
            temperature = template_vars.get('temperature', 0.7)
            max_tokens = template_vars.get('max_tokens')
            response_format = template_vars.get('response_format')
            
            # 构建消息
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt_content})
            
            # 构建请求参数
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "extra_body": {"thinking": {"type": "disabled"}}
            }
            
            # 可选参数
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            if response_format:
                if isinstance(response_format, str):
                    request_params["response_format"] = json.loads(response_format)
                else:
                    request_params["response_format"] = response_format
            
            # 调用LLM
            response = await self.client.chat.completions.create(**request_params)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"使用提示词模板调用LLM失败 {template_key}: {e}")
            raise
            
    @observe(name="提取用户画像LLM")
    async def extract_user_profile(self, dialogue_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从对话历史中提取用户画像 - 使用数据库提示词"""
        try:
            # 构建对话历史文本
            dialogue_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in dialogue_history
            ])
            
            # 使用数据库提示词模板
            response_text = await self._call_llm_with_prompt_template(
                'rpg_extract_user_profile',
                {'dialogue_text': dialogue_text}
            )
            
            return json.loads(response_text)
            
        except Exception as e:
            print(f"提取用户画像失败: {e}")
            return {}
            
    @observe(name="提取事件LLM")
    async def extract_events(self, dialogue_history: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """从对话历史中提取重大事件和实体事件 - 使用数据库提示词"""
        try:
            dialogue_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in dialogue_history
            ])
            
            # 使用数据库提示词模板
            response_text = await self._call_llm_with_prompt_template(
                'rpg_extract_events',
                {'dialogue_text': dialogue_text}
            )
            
            events_data = json.loads(response_text)
            return {
                'core_events': events_data.get('core_events', []),
                'entity_events': events_data.get('entity_events', [])
            }
            
        except Exception as e:
            print(f"提取事件失败: {e}")
            return {'core_events': [], 'entity_events': []}
            
    @observe(name="反思LLM")
    async def generate_reflection(self, dialogue_history: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """生成反思记忆 - 使用数据库提示词"""
        try:
            dialogue_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in dialogue_history
            ])
            
            # 使用数据库提示词模板
            response_text = await self._call_llm_with_prompt_template(
                'rpg_generate_reflection',
                {'dialogue_text': dialogue_text}
            )
            
            reflections_data = json.loads(response_text)
            return {
                'core_reflections': reflections_data.get('core_reflections', []),
                'long_term_reflections': reflections_data.get('long_term_reflections', [])
            }
            
        except Exception as e:
            print(f"生成反思失败: {e}")
            return {'core_reflections': [], 'long_term_reflections': []}

    @observe(name="总结凝练核心反思/事件LLM")
    async def consolidate_memories(self, memories: List[str], memory_type: str) -> List[str]:
        """使用LLM整合核心记忆 - 使用数据库提示词"""
        if not memories:
            return []

        try:
            memory_list_str = "\n".join(f"- {item}" for item in memories)
            
            # 使用数据库提示词模板
            response_text = await self._call_llm_with_prompt_template(
                'rpg_consolidate_memories',
                {
                    'memory_type': memory_type,
                    'memory_list': memory_list_str
                }
            )
            
            result_json = json.loads(response_text)
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
        """生成NPC回复 - 使用数据库提示词"""
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
            
            # 使用数据库提示词模板
            response_text = await self._call_llm_with_prompt_template(
                'rpg_generate_npc_response',
                {
                    'history_text': history_text,
                    'context_text': context_text,
                    'user_message': user_message
                }
            )
            
            return response_text
            
        except Exception as e:
            print(f"生成NPC回复失败: {e}")
            return "抱歉，我现在无法回复。请稍后再试。"
    
    def clear_prompt_cache(self):
        """清理提示词缓存"""
        self.prompt_manager.clear_cache()
        print("提示词缓存已清理")

# 全局LLM客户端实例
llm_client = LLMClient()