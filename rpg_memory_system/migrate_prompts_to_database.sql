-- =====================================================
-- RPG记忆系统提示词迁移到数据库SQL脚本
-- =====================================================
-- 将RPG记忆系统中的5个LLM提示词迁移到prompt_templates和prompt_versions表中
-- 支持版本管理和可编辑形式

-- 1. 首先扩展template_type枚举，添加记忆系统相关类型
ALTER TABLE prompt_templates 
MODIFY COLUMN template_type ENUM(
    'npc',
    'dialogue', 
    'monitor_jump',
    'recommend_questions',
    'affection_rating',
    'system',
    'ui_message',
    'scenario',
    'memory_user_profile',      -- 用户画像提取
    'memory_event_extraction',  -- 事件提取
    'memory_reflection',        -- 反思生成
    'memory_consolidation',     -- 记忆整合
    'memory_npc_response'       -- NPC回复生成
) NOT NULL;

-- 2. 插入5个记忆系统提示词模板
-- =====================================================

-- 2.1 用户画像提取提示词模板
INSERT INTO prompt_templates (
    template_key, 
    template_name, 
    template_type, 
    category, 
    description, 
    created_by
) VALUES (
    'rpg_extract_user_profile',
    'RPG记忆系统-用户画像提取',
    'memory_user_profile',
    'rpg_memory',
    '从对话历史中提取用户的个人特征、性格、兴趣爱好等画像信息',
    'system'
);

-- 2.2 事件提取提示词模板
INSERT INTO prompt_templates (
    template_key, 
    template_name, 
    template_type, 
    category, 
    description, 
    created_by
) VALUES (
    'rpg_extract_events',
    'RPG记忆系统-事件提取',
    'memory_event_extraction',
    'rpg_memory',
    '从对话历史中识别和分类重要事件，区分核心事件和实体事件',
    'system'
);

-- 2.3 反思生成提示词模板
INSERT INTO prompt_templates (
    template_key, 
    template_name, 
    template_type, 
    category, 
    description, 
    created_by
) VALUES (
    'rpg_generate_reflection',
    'RPG记忆系统-反思生成',
    'memory_reflection',
    'rpg_memory',
    '基于对话历史生成AI角色的反思记忆，包括核心反思和长期反思',
    'system'
);

-- 2.4 记忆整合提示词模板
INSERT INTO prompt_templates (
    template_key, 
    template_name, 
    template_type, 
    category, 
    description, 
    created_by
) VALUES (
    'rpg_consolidate_memories',
    'RPG记忆系统-记忆整合',
    'memory_consolidation',
    'rpg_memory',
    '整合和优化核心记忆内容，消除冗余，合并相似记忆',
    'system'
);

-- 2.5 NPC回复生成提示词模板
INSERT INTO prompt_templates (
    template_key, 
    template_name, 
    template_type, 
    category, 
    description, 
    created_by
) VALUES (
    'rpg_generate_npc_response',
    'RPG记忆系统-NPC回复生成',
    'memory_npc_response',
    'rpg_memory',
    '基于记忆上下文生成AI NPC的个性化回复',
    'system'
);

-- 3. 为每个提示词创建初始版本 (v1.0)
-- =====================================================

-- 3.1 用户画像提取提示词内容
INSERT INTO prompt_versions (
    template_id, 
    version_number, 
    version_name, 
    content, 
    variables, 
    status, 
    is_current_published, 
    change_notes, 
    created_by, 
    published_by, 
    published_at
) VALUES (
    (SELECT id FROM prompt_templates WHERE template_key = 'rpg_extract_user_profile'),
    'v1.0',
    '用户画像提取-初始版本',
    '请分析以下对话历史，提取用户以下信息：
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
只返回JSON，不要其他内容。',
    JSON_OBJECT(
        'dialogue_text', '对话历史文本变量',
        'system_message', '你是一个专业的用户画像分析师，擅长从对话中提取用户特征。',
        'temperature', 0.3
    ),
    'published',
    1,
    '从RPG记忆系统llm_client.py迁移的初始版本',
    'system',
    'system',
    NOW()
);

-- 3.2 事件提取提示词内容
INSERT INTO prompt_versions (
    template_id, 
    version_number, 
    version_name, 
    content, 
    variables, 
    status, 
    is_current_published, 
    change_notes, 
    created_by, 
    published_by, 
    published_at
) VALUES (
    (SELECT id FROM prompt_templates WHERE template_key = 'rpg_extract_events'),
    'v1.0',
    '事件提取-初始版本',
    '分析对话，精准提取重要的事件并分类：

{dialogue_text}

要求：
- 只提取真正重要且具体的事件，避免泛泛而谈
- 每类事件最多3-5条，优先质量而非数量
- 事件描述要简洁明确，一句话概括

分类：
1. core_events：与剧情高度相关或用户之间的重大事件，必须是重要的、影响深远的事件
2. entity_events：与用户互动之间的较小事件、日常互动、具体的实体信息等

返回JSON：
{
  "core_events": ["关键事件1"],
  "entity_events": ["具体互动1"]
}

只返回JSON，不要其他内容。',
    JSON_OBJECT(
        'dialogue_text', '对话历史文本变量',
        'system_message', '你是一个专业的事件提取分析师，擅长从对话中识别和分类重要事件。',
        'temperature', 0.3
    ),
    'published',
    1,
    '从RPG记忆系统llm_client.py迁移的初始版本',
    'system',
    'system',
    NOW()
);

-- 3.3 反思生成提示词内容
INSERT INTO prompt_versions (
    template_id, 
    version_number, 
    version_name, 
    content, 
    variables, 
    status, 
    is_current_published, 
    change_notes, 
    created_by, 
    published_by, 
    published_at
) VALUES (
    (SELECT id FROM prompt_templates WHERE template_key = 'rpg_generate_reflection'),
    'v1.0',
    '反思生成-初始版本',
    '请基于以下我与玩家真实的互动历史，以我的口吻和视角，生成自然、简要且带有个人感受的反思，就像真人回忆那样，不夸大不编造：

对话历史：
{dialogue_text}

请生成两类高度凝练的反思：
1. 核心反思（core_reflections）：针对重大事件，反思用户表现出的深层行为模式、关键转变或重大决策
2. 长期反思（long_term_reflections）：基于日常互动的一般性反思，关于用户偏好、习惯、日常行为等

要求：
反思应使用自然口语，带有些许主观但不出事实范围；内容基于真实对话，不抽象过度或偏离原意；每条尽量简短像一闪而过的念头，但切中要害。

请以JSON格式返回，格式如下：
{
  "core_reflections": ["核心反思1", "核心反思2"],
  "long_term_reflections": ["长期反思1", "长期反思2"]
}

只返回JSON，不要其他内容。',
    JSON_OBJECT(
        'dialogue_text', '对话历史文本变量',
        'system_message', '我是Aliya，一个被困在太空等待救援的少女。我会从我们的互动中真诚地回想和总结，形成带有个人视角但尊重事实的反思。',
        'temperature', 0.7
    ),
    'published',
    1,
    '从RPG记忆系统llm_client.py迁移的初始版本',
    'system',
    'system',
    NOW()
);

-- 3.4 记忆整合提示词内容
INSERT INTO prompt_versions (
    template_id, 
    version_number, 
    version_name, 
    content, 
    variables, 
    status, 
    is_current_published, 
    change_notes, 
    created_by, 
    published_by, 
    published_at
) VALUES (
    (SELECT id FROM prompt_templates WHERE template_key = 'rpg_consolidate_memories'),
    'v1.0',
    '记忆整合-初始版本',
    '你是一个AI记忆管理专家。你的任务是分析、合并和提炼一个关于用户的记忆列表。
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
{"consolidated_memories": ["合并后的{memory_type}1", "合并后的{memory_type}2", ...]}',
    JSON_OBJECT(
        'memory_type', '记忆类型变量（事件或反思）',
        'memory_list', '记忆列表文本变量',
        'temperature', 0.2,
        'response_format', '{"type": "json_object"}'
    ),
    'published',
    1,
    '从RPG记忆系统llm_client.py迁移的初始版本',
    'system',
    'system',
    NOW()
);

-- 3.5 NPC回复生成提示词内容
INSERT INTO prompt_versions (
    template_id, 
    version_number, 
    version_name, 
    content, 
    variables, 
    status, 
    is_current_published, 
    change_notes, 
    created_by, 
    published_by, 
    published_at
) VALUES (
    (SELECT id FROM prompt_templates WHERE template_key = 'rpg_generate_npc_response'),
    'v1.0',
    'NPC回复生成-初始版本',
    '对话历史：
{history_text}

记忆上下文：
{context_text}

用户最新消息：{user_message}

请生成合适的回复：',
    JSON_OBJECT(
        'history_text', '对话历史文本变量',
        'context_text', '记忆上下文文本变量',
        'user_message', '用户最新消息变量',
        'system_message', '你是一个智能的AI助手，能够基于对话历史和记忆上下文进行自然对话。请根据用户的消息和提供的上下文信息，生成合适的回复。回复要求：1. 自然、友好、有帮助 2. 基于提供的记忆上下文进行个性化回复 3. 保持对话的连贯性 4. 回复长度适中，不要过长 5. 如果没有足够的上下文，可以询问更多信息',
        'temperature', 0.7,
        'max_tokens', 500
    ),
    'published',
    1,
    '从RPG记忆系统llm_client.py迁移的初始版本',
    'system',
    'system',
    NOW()
);

-- 4. 验证插入结果
-- =====================================================

-- 查看所有RPG记忆系统提示词模板
SELECT 
    pt.template_key,
    pt.template_name,
    pt.template_type,
    pt.category,
    pv.version_number,
    pv.status,
    pv.is_current_published
FROM prompt_templates pt
JOIN prompt_versions pv ON pt.id = pv.template_id
WHERE pt.category = 'rpg_memory'
ORDER BY pt.template_key;

-- 5. 创建提示词获取的便捷视图
-- =====================================================

CREATE OR REPLACE VIEW rpg_memory_prompts AS
SELECT 
    pt.template_key,
    pt.template_name,
    pt.template_type,
    pv.content,
    pv.variables,
    pv.version_number
FROM prompt_templates pt
JOIN prompt_versions pv ON pt.id = pv.template_id
WHERE pt.category = 'rpg_memory' 
  AND pv.is_current_published = 1;

-- 使用示例：
-- SELECT content FROM rpg_memory_prompts WHERE template_key = 'rpg_extract_user_profile';

COMMIT;

-- =====================================================
-- 迁移完成！
-- 
-- 现在RPG记忆系统的5个LLM提示词已经迁移到数据库中：
-- 1. rpg_extract_user_profile - 用户画像提取
-- 2. rpg_extract_events - 事件提取
-- 3. rpg_generate_reflection - 反思生成
-- 4. rpg_consolidate_memories - 记忆整合
-- 5. rpg_generate_npc_response - NPC回复生成
--
-- 特性：
-- - 支持版本管理
-- - 可通过Web界面编辑
-- - 包含变量配置
-- - 支持发布/撤回
-- - 变更记录追踪
-- =====================================================