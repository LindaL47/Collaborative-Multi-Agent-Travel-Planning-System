# RPG记忆系统提示词数据库迁移指南

## 📋 概述

本指南说明如何将RPG记忆系统中的5个LLM提示词从硬编码迁移到数据库中，实现可编辑的版本管理系统。

## 🗃️ **迁移的提示词**

### **1. 用户画像提取** (`rpg_extract_user_profile`)
- **功能**: 从对话历史中分析用户的个人特征、性格、兴趣等
- **输出**: JSON格式的用户画像数据
- **模板类型**: `memory_user_profile`

### **2. 事件提取** (`rpg_extract_events`) 
- **功能**: 识别和分类对话中的重要事件
- **输出**: JSON格式的事件分类（核心事件+实体事件）
- **模板类型**: `memory_event_extraction`

### **3. 反思生成** (`rpg_generate_reflection`)
- **功能**: 基于对话历史生成AI角色的反思记忆
- **输出**: JSON格式的反思分类（核心反思+长期反思）
- **模板类型**: `memory_reflection`

### **4. 记忆整合** (`rpg_consolidate_memories`)
- **功能**: 整合和优化核心记忆，消除冗余
- **输出**: JSON格式的整合后记忆列表
- **模板类型**: `memory_consolidation`

### **5. NPC回复生成** (`rpg_generate_npc_response`)
- **功能**: 基于记忆上下文生成个性化AI回复
- **输出**: 自然语言回复
- **模板类型**: `memory_npc_response`

## 🚀 **迁移步骤**

### **步骤1: 执行数据库迁移脚本**

```bash
# 进入RPG记忆系统目录
cd /home/shengchan/prodev/AIgame/rpg_memory_system

# 执行SQL迁移脚本
docker exec -i aigame_mysql mysql -u root -paigame_strong_root_password_123 aigame_db < migrate_prompts_to_database.sql
```

### **步骤2: 验证迁移结果**

```sql
-- 检查是否成功插入5个提示词模板
SELECT 
    template_key,
    template_name,
    template_type,
    category
FROM prompt_templates 
WHERE category = 'rpg_memory';

-- 检查每个模板的发布版本
SELECT 
    pt.template_key,
    pv.version_number,
    pv.status,
    pv.is_current_published
FROM prompt_templates pt
JOIN prompt_versions pv ON pt.id = pv.template_id
WHERE pt.category = 'rpg_memory'
ORDER BY pt.template_key;
```

### **步骤3: 更新LLM客户端代码**

有两种方式更新代码：

#### **方式A: 替换原文件（推荐）**
```bash
# 备份原文件
cp src/server/api/models/llm_client.py src/server/api/models/llm_client_backup.py

# 使用新的数据库版本
cp src/server/api/models/llm_client_database.py src/server/api/models/llm_client.py
```

#### **方式B: 逐步迁移**
保持原文件不变，新建数据库版本进行测试：
```python
# 在需要的地方导入新版本
from .models.llm_client_database import llm_client as db_llm_client
```

### **步骤4: 测试验证**

```python
# 测试数据库提示词是否正常工作
import asyncio
from src.server.api.models.llm_client import llm_client

async def test_database_prompts():
    # 测试数据
    test_dialogue = [
        {"role": "user", "content": "你好，我叫张三"},
        {"role": "assistant", "content": "你好张三，很高兴认识你"}
    ]
    
    # 测试用户画像提取
    profile = await llm_client.extract_user_profile(test_dialogue)
    print("用户画像:", profile)
    
    # 测试事件提取
    events = await llm_client.extract_events(test_dialogue)
    print("事件提取:", events)
    
    # 测试反思生成
    reflections = await llm_client.generate_reflection(test_dialogue)
    print("反思生成:", reflections)

# 运行测试
asyncio.run(test_database_prompts())
```

## 📝 **版本管理功能**

### **创建新版本**

```sql
-- 为用户画像提取创建v1.1版本
INSERT INTO prompt_versions (
    template_id,
    version_number,
    version_name,
    content,
    variables,
    status,
    change_notes,
    created_by
) VALUES (
    (SELECT id FROM prompt_templates WHERE template_key = 'rpg_extract_user_profile'),
    'v1.1',
    '用户画像提取-优化版本',
    '这里是新的提示词内容...',
    JSON_OBJECT('temperature', 0.2, 'system_message', '新的系统消息'),
    'draft',
    '优化了提取精度，调整了温度参数',
    'developer_name'
);
```

### **发布新版本**

```sql
-- 撤回当前发布版本
UPDATE prompt_versions 
SET is_current_published = 0, status = 'archived'
WHERE template_id = (SELECT id FROM prompt_templates WHERE template_key = 'rpg_extract_user_profile')
  AND is_current_published = 1;

-- 发布新版本
UPDATE prompt_versions 
SET is_current_published = 1, status = 'published', published_by = 'admin', published_at = NOW()
WHERE template_id = (SELECT id FROM prompt_templates WHERE template_key = 'rpg_extract_user_profile')
  AND version_number = 'v1.1';
```

### **回滚版本**

```sql
-- 回滚到v1.0版本
UPDATE prompt_versions 
SET is_current_published = 0 
WHERE template_id = (SELECT id FROM prompt_templates WHERE template_key = 'rpg_extract_user_profile');

UPDATE prompt_versions 
SET is_current_published = 1, status = 'published'
WHERE template_id = (SELECT id FROM prompt_templates WHERE template_key = 'rpg_extract_user_profile')
  AND version_number = 'v1.0';
```

## 🔧 **高级配置**

### **变量配置说明**

每个提示词模板的`variables`字段包含配置参数：

```json
{
  "temperature": 0.3,           // LLM温度参数
  "max_tokens": 500,           // 最大token数
  "system_message": "...",     // 系统消息
  "response_format": {...}     // 响应格式配置
}
```

### **缓存管理**

```python
# 清理提示词缓存，强制重新从数据库加载
llm_client.clear_prompt_cache()
```

### **便捷查询视图**

已创建`rpg_memory_prompts`视图方便查询：

```sql
-- 获取所有当前发布的RPG记忆提示词
SELECT * FROM rpg_memory_prompts;

-- 获取特定提示词内容
SELECT content FROM rpg_memory_prompts 
WHERE template_key = 'rpg_extract_user_profile';
```

## ⚠️ **注意事项**

### **1. 数据库连接**
确保RPG记忆系统能访问主项目的MySQL数据库：
```python
# 检查数据库连接配置
DATABASE_URL = "mysql+pymysql://root:aigame_strong_root_password_123@localhost:3306/aigame_db"
```

### **2. 兼容性**
新的LLM客户端保持与原版本完全兼容的API接口，可以无缝替换。

### **3. 错误处理**
如果数据库提示词获取失败，系统会回退到硬编码版本或返回默认错误响应。

### **4. 性能考虑**
- 提示词会被缓存在内存中，避免频繁数据库查询
- 首次加载稍慢，后续访问快速

## 🎯 **优势总结**

### **迁移前（硬编码）**
- ❌ 修改提示词需要改代码
- ❌ 无版本管理
- ❌ 无法回滚  
- ❌ 难以A/B测试

### **迁移后（数据库）**
- ✅ 可通过Web界面编辑
- ✅ 完整版本管理
- ✅ 支持发布/回滚
- ✅ 变更记录追踪
- ✅ 支持A/B测试
- ✅ 团队协作编辑

## 📞 **支持**

如遇问题，请检查：
1. 数据库连接是否正常
2. 提示词模板是否正确插入
3. 版本是否正确发布
4. 缓存是否需要清理

完成迁移后，RPG记忆系统的LLM提示词将具备企业级的版本管理能力！