# AI游戏记忆系统 (RPG Memory System)

基于memobase思想构建的AI游戏记忆系统，实现了三层记忆架构，为AI游戏角色提供智能的记忆管理和检索能力。

## 🎯 项目特性

### 核心功能
- **三层记忆架构**: 短期记忆(Redis) + 核心记忆(用户画像+重大事件+重大反思) + 长期记忆(PostgreSQL+pgvector)
- **并行处理**: 基于PocketFlow的并行记忆处理和RAG检索
- **智能提取**: LLM驱动的用户画像、事件提取和反思生成
- **向量检索**: 基于pgvector的高效相似度搜索
- **RESTful API**: 完整的记忆管理API接口

### 技术栈
- **后端框架**: FastAPI + Uvicorn
- **数据库**: PostgreSQL + pgvector (向量数据库)
- **缓存**: Redis (短期记忆存储)
- **AI模型**: 豆包大模型 (文本生成和嵌入)
- **工作流引擎**: PocketFlow (并行任务处理)
- **部署**: Docker + Docker Compose

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   短期记忆       │    │   核心记忆       │    │   长期记忆       │
│   (Redis)       │    │ (用户画像/状态)   │    │ (PostgreSQL)    │
│                 │    │                 │    │                 │
│ • 对话历史       │    │ • 用户画像       │    │ • 实体事件       │
│ • 临时状态       │    │ • 重大事件       │    │ • 对话记录       │
│ • 会话上下文     │    │ • 重大反思       │    │ • 长期反思       │
│                 │    │                 │    │ • NPC故事       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  记忆管理器      │
                    │ (MemoryManager) │
                    │                 │
                    │ • 记忆处理       │
                    │ • RAG检索       │
                    │ • 上下文生成     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   API接口       │
                    │  (FastAPI)     │
                    └─────────────────┘
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Docker & Docker Compose
- 豆包模型API密钥

### 1. 克隆项目
```bash
git clone <repository-url>
cd rpg_memory_system
```

### 2. 配置环境
复制并编辑环境配置文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下参数：
```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/rpg_memory
REDIS_URL=redis://localhost:6379/0

# LLM配置 (豆包模型)
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL_NAME=ep-20241201193721-8xvxz
DOUBAO_EMBEDDING_MODEL=ep-20241201193721-8xvxz

# Langsmith配置 (可选)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=rpg-memory-system

# 记忆系统配置
MEMORY_PROCESSING_TRIGGER_ROUNDS=60
RAG_RETRIEVAL_TOP_K=5
SHORT_TERM_MEMORY_SIZE=20
```

### 3. 一键设置
使用项目提供的管理脚本进行完整设置：
```bash
python run.py setup
```

这个命令会自动：
- 安装Python依赖
- 启动数据库服务 (Docker)
- 初始化数据库表结构
- 导入NPC故事数据

### 4. 启动API服务
```bash
python run.py server
```

服务启动后，访问 http://localhost:8000/docs 查看API文档。

## 📖 使用指南

### API接口

#### 1. 初始化用户记忆
```bash
curl -X POST "http://localhost:8000/api/memory/initialize" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "player1", "project_id": "game1"}'
```

#### 2. 添加对话
```bash
curl -X POST "http://localhost:8000/api/memory/dialogue" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "player1",
       "project_id": "game1",
       "role": "user",
       "content": "你好，我想了解这个世界的背景"
     }'
```

#### 3. 获取记忆上下文
```bash
curl -X POST "http://localhost:8000/api/memory/context" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "player1",
       "project_id": "game1",
       "query": "世界背景"
     }'
```

#### 4. 手动触发记忆处理
```bash
curl -X POST "http://localhost:8000/api/memory/process" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "player1", "project_id": "game1"}'
```

### 交互式测试
项目提供了交互式测试工具，方便开发和调试：

```bash
python run.py test-interactive
```

支持的命令：
- `/help` - 显示帮助信息
- `/memory <查询>` - 查询记忆上下文
- `/process` - 手动触发记忆处理
- `/status` - 显示会话状态
- `/quit` - 退出程序

### 批量测试
运行120轮对话的自动化测试：

```bash
python run.py test-batch
```

## 🔧 开发指南

### 项目结构
```
rpg_memory_system/
├── src/
│   └── server/
│       └── api/
│           ├── models/          # 数据模型
│           │   ├── database.py  # 数据库模型
│           │   ├── redis_client.py # Redis客户端
│           │   └── llm_client.py   # LLM客户端
│           ├── controllers/     # 业务逻辑
│           │   ├── memory_processor.py # 记忆处理器
│           │   ├── rag_retriever.py    # RAG检索器
│           │   └── memory_manager.py   # 记忆管理器
│           └── api_layer/       # API层
│               └── main.py      # FastAPI应用
├── scripts/                    # 工具脚本
│   ├── init_database.py       # 数据库初始化
│   └── init_npc_stories.py    # NPC故事初始化
├── tests/                     # 测试文件
│   ├── test_batch_simulation.py    # 批量测试
│   └── test_interactive.py         # 交互式测试
├── docker-compose.yml         # Docker服务配置
├── requirements.txt           # Python依赖
├── .env                      # 环境配置
├── run.py                    # 项目管理脚本
└── README.md                 # 项目文档
```

### 核心组件

#### 1. 记忆处理器 (MemoryProcessor)
负责并行处理对话历史，提取：
- 用户画像 (用户偏好、性格特征)
- 重大事件 (与剧情高度相关的核心事件，直接注入提示词)
- 实体事件 (与用户互动的较小事件，通过RAG检索)
- 重大反思 (核心反思记忆，直接注入提示词)
- 长期反思 (普通反思记忆，通过RAG检索)

#### 2. RAG检索器 (RAGRetriever)
并行检索长期记忆：
- 实体事件检索
- 对话记录检索
- 长期反思检索
- NPC故事检索

#### 3. 记忆管理器 (MemoryManager)
统一的记忆操作接口：
- 短期记忆管理
- 记忆处理触发
- 上下文生成
- 核心记忆更新

### 自定义开发

#### 添加新的记忆类型
1. 在 `database.py` 中定义新的数据模型
2. 在 `rag_retriever.py` 中添加检索逻辑
3. 在 `memory_manager.py` 中集成新的记忆类型

#### 自定义LLM提示词
编辑 `llm_client.py` 中的提示词模板：
- `extract_user_profile_prompt` - 用户画像提取
- `extract_events_prompt` - 事件提取
- `generate_reflection_prompt` - 反思生成

## 🛠️ 管理工具

项目提供了 `run.py` 管理脚本，支持以下命令：

```bash
# 完整设置
python run.py setup

# 安装依赖
python run.py install

# 数据库管理
python run.py db-start    # 启动数据库服务
python run.py db-init     # 初始化数据库

# NPC数据管理
python run.py npc-init    # 初始化NPC故事

# 服务管理
python run.py server      # 启动API服务器

# 测试
python run.py test              # 运行所有测试
python run.py test-batch        # 批量测试
python run.py test-interactive  # 交互式测试

# 系统检查
python run.py check       # 检查系统状态
```

## 🐳 Docker部署

### 启动数据库服务
```bash
docker-compose up -d
```

### 停止服务
```bash
docker-compose down
```

### 查看日志
```bash
docker-compose logs -f
```

## 📊 性能优化

### 数据库优化
- 使用pgvector的IVFFlat索引加速向量搜索
- 合理设置连接池大小
- 定期清理过期的短期记忆

### 内存优化
- 限制短期记忆大小 (默认20条)
- 使用Redis过期策略
- 批量处理向量嵌入

### 并发优化
- PocketFlow并行处理LLM任务
- 异步数据库操作
- 连接池复用

## 🔍 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库服务状态
docker-compose ps

# 查看数据库日志
docker-compose logs postgres

# 重启数据库服务
docker-compose restart postgres
```

#### 2. pgvector扩展未安装
```bash
# 进入数据库容器
docker-compose exec postgres psql -U postgres -d rpg_memory

# 手动创建扩展
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 3. LLM API调用失败
- 检查 `.env` 文件中的API密钥配置
- 确认网络连接正常
- 查看API调用日志

#### 4. 内存不足
- 减少 `SHORT_TERM_MEMORY_SIZE` 配置
- 增加系统内存
- 优化向量维度

### 日志查看
```bash
# API服务日志
python run.py server --log-level debug

# 数据库日志
docker-compose logs postgres

# Redis日志
docker-compose logs redis
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [memobase](https://github.com/memobase/memobase) - 记忆系统设计思想
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL向量扩展
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Python Web框架
- [LangChain](https://langchain.com/) - LLM应用开发框架

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件
- 项目讨论区

---

**AI游戏记忆系统** - 让AI角色拥有真正的记忆 🧠✨