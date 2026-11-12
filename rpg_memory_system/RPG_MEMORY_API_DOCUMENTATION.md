# RPG记忆系统提示词版本管理API文档

## 📋 概述

RPG记忆系统提示词版本管理API为前端提供完整的LLM提示词版本管理功能，支持对5个核心提示词模板进行创建、编辑、发布、回滚等操作。

## 🚀 快速开始

### 启动API服务

```bash
cd /home/shengchan/prodev/AIgame/rpg_memory_system
python rpg_memory_api_server.py
```

服务默认运行在 `http://localhost:8888`

### 健康检查

```bash
curl http://localhost:8888/health
```

### API文档

- **Swagger UI**: http://localhost:8888/docs
- **ReDoc**: http://localhost:8888/redoc

## 📝 API端点

### 1. 基础信息

#### 1.1 健康检查
```http
GET /health
```

**响应示例:**
```json
{
  "status": "healthy",
  "service": "RPG记忆系统API",
  "version": "1.0.0",
  "database": "connected"
}
```

#### 1.2 服务信息
```http
GET /
```

### 2. 模板管理

#### 2.1 获取所有RPG提示词模板
```http
GET /api/rpg-memory-prompts/templates
```

**响应示例:**
```json
[
  {
    "id": 287,
    "template_key": "rpg_extract_user_profile",
    "template_name": "RPG记忆系统-用户画像提取",
    "template_type": "memory_user_profile",
    "category": "rpg_memory",
    "description": "从对话历史中提取用户的个人特征、性格、兴趣爱好等画像信息",
    "created_at": "2025-09-13T10:48:47",
    "current_version": "v1.0",
    "total_versions": 1
  }
]
```

#### 2.2 获取指定模板详情
```http
GET /api/rpg-memory-prompts/templates/{template_key}
```

**参数:**
- `template_key`: 模板键名 (rpg_extract_user_profile, rpg_extract_events, etc.)

### 3. 版本管理

#### 3.1 获取模板的所有版本
```http
GET /api/rpg-memory-prompts/templates/{template_key}/versions
```

**响应示例:**
```json
[
  {
    "id": 446,
    "template_key": "rpg_extract_user_profile",
    "version_number": "v1.0",
    "version_name": "用户画像提取-初始版本",
    "content": "请分析以下对话历史，提取用户以下信息：...",
    "variables": {
      "temperature": 0.3,
      "system_message": "你是一个专业的用户画像分析师..."
    },
    "status": "published",
    "is_current_published": true,
    "change_notes": "从RPG记忆系统迁移的初始版本",
    "created_by": "system",
    "created_at": "2025-09-13T10:50:41",
    "published_at": "2025-09-13T10:50:41"
  }
]
```

#### 3.2 获取当前发布版本
```http
GET /api/rpg-memory-prompts/templates/{template_key}/current
```

#### 3.3 创建新版本
```http
POST /api/rpg-memory-prompts/templates/{template_key}/versions
```

**请求体:**
```json
{
  "version_number": "v1.1",
  "version_name": "优化版本",
  "content": "这里是新的提示词内容...",
  "variables": {
    "temperature": 0.2,
    "system_message": "新的系统消息",
    "max_tokens": 1000
  },
  "change_notes": "优化了提取精度",
  "created_by": "admin"
}
```

#### 3.4 更新版本内容
```http
PUT /api/rpg-memory-prompts/versions/{version_id}
```

**请求体:**
```json
{
  "version_name": "已更新的版本名称",
  "content": "更新后的提示词内容...",
  "variables": {
    "temperature": 0.3,
    "system_message": "更新后的系统消息"
  },
  "change_notes": "更新说明"
}
```

#### 3.5 发布版本
```http
POST /api/rpg-memory-prompts/versions/{version_id}/publish
```

**请求体:**
```json
{
  "published_by": "admin",
  "change_notes": "发布v1.1版本"
}
```

#### 3.6 删除版本
```http
DELETE /api/rpg-memory-prompts/versions/{version_id}
```

**注意:** 只能删除草稿或已保存状态的版本，无法删除已发布的版本

### 4. 变量配置

#### 4.1 获取模板变量配置
```http
GET /api/rpg-memory-prompts/templates/{template_key}/variables
```

**响应示例:**
```json
{
  "template_key": "rpg_extract_user_profile",
  "variables": {
    "temperature": 0.3,
    "system_message": "你是一个专业的用户画像分析师...",
    "max_tokens": 1000
  },
  "variable_descriptions": {
    "temperature": "LLM温度参数，控制生成文本的随机性（0.0-1.0）",
    "system_message": "系统提示消息，定义AI助手的角色和行为准则",
    "max_tokens": "最大token数限制，控制生成文本的长度"
  }
}
```

### 5. 批量操作

#### 5.1 获取所有当前版本概览
```http
GET /api/rpg-memory-prompts/all-current-versions
```

**响应示例:**
```json
{
  "total_templates": 5,
  "current_versions": [
    {
      "template_key": "rpg_extract_user_profile",
      "template_name": "RPG记忆系统-用户画像提取",
      "version_number": "v1.0",
      "status": "published",
      "published_at": "2025-09-13T10:50:41",
      "created_by": "system"
    }
  ]
}
```

#### 5.2 清理LLM缓存
```http
POST /api/rpg-memory-prompts/clear-cache
```

## 🎯 5个核心提示词模板

| 模板键 | 模板名称 | 功能描述 |
|-------|---------|----------|
| `rpg_extract_user_profile` | 用户画像提取 | 从对话历史中提取用户的个人特征、性格、兴趣爱好等 |
| `rpg_extract_events` | 事件提取 | 识别和分类重要事件，区分核心事件和实体事件 |
| `rpg_generate_reflection` | 反思生成 | 基于对话历史生成AI角色的反思记忆 |
| `rpg_consolidate_memories` | 记忆整合 | 整合和优化核心记忆内容，消除冗余 |
| `rpg_generate_npc_response` | NPC回复生成 | 基于记忆上下文生成AI NPC的个性化回复 |

## 📊 版本状态

- **draft**: 草稿状态，可编辑
- **saved**: 已保存，可编辑
- **published**: 已发布，不可编辑，作为当前生产版本
- **archived**: 已归档，之前的发布版本

## 🔧 前端集成示例

### JavaScript/TypeScript示例

```javascript
// 获取所有模板
async function getTemplates() {
  const response = await fetch('/api/rpg-memory-prompts/templates');
  return await response.json();
}

// 获取特定模板的版本列表
async function getVersions(templateKey) {
  const response = await fetch(`/api/rpg-memory-prompts/templates/${templateKey}/versions`);
  return await response.json();
}

// 创建新版本
async function createVersion(templateKey, versionData) {
  const response = await fetch(`/api/rpg-memory-prompts/templates/${templateKey}/versions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(versionData)
  });
  return await response.json();
}

// 发布版本
async function publishVersion(versionId, publishData) {
  const response = await fetch(`/api/rpg-memory-prompts/versions/${versionId}/publish`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(publishData)
  });
  return await response.json();
}
```

### React Hook示例

```javascript
import { useState, useEffect } from 'react';

function useRPGPromptTemplates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/rpg-memory-prompts/templates')
      .then(response => response.json())
      .then(data => {
        setTemplates(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, []);

  return { templates, loading, error };
}
```

## 🧪 测试

### 运行测试脚本

```bash
cd /home/shengchan/prodev/AIgame/rpg_memory_system
python test_rpg_memory_api.py
```

### 测试涵盖范围

- ✅ 健康检查
- ✅ 获取所有模板
- ✅ 获取模板详情
- ✅ 获取版本列表
- ✅ 获取当前版本
- ✅ 创建新版本
- ✅ 更新版本
- ✅ 发布版本
- ✅ 删除版本
- ✅ 获取变量配置
- ✅ 批量操作

## ⚠️ 注意事项

### 1. 权限控制
- 当前API未实现权限认证，在生产环境中需要添加适当的认证机制
- 建议为不同操作设置不同的权限级别

### 2. 数据安全
- 确保数据库连接安全
- 在生产环境中使用HTTPS
- 考虑对敏感配置进行加密

### 3. 性能考虑
- API支持分页，但当前未实现，建议在模板数量较多时添加分页功能
- 考虑添加缓存机制以提高响应速度

### 4. 错误处理
- API提供详细的错误信息
- 建议前端实现适当的错误提示和重试机制

## 📈 扩展功能

### 未来可能的增强

1. **权限管理**: 添加用户角色和权限控制
2. **审批流程**: 版本发布前的审批机制
3. **A/B测试**: 支持多版本并行测试
4. **变更历史**: 详细的变更记录和对比功能
5. **模板克隆**: 复制现有模板创建新模板
6. **批量导入导出**: 支持批量管理多个模板

## 🆘 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查MySQL服务是否运行
   - 验证数据库连接配置

2. **API服务无法启动**
   - 检查端口8888是否被占用
   - 确认所有依赖包已安装

3. **版本创建失败**
   - 检查版本号是否重复
   - 验证JSON格式是否正确

### 联系支持

如遇到问题，请检查：
1. 服务器日志
2. 数据库连接状态
3. API请求格式是否正确

完成版本管理API后，您可以通过前端界面轻松管理RPG记忆系统的所有LLM提示词！🎉