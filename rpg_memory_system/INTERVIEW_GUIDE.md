# RPG Memory System 面试说明文档

本文档面向大厂面试答辩使用。它不是普通 README，而是帮助你把这个项目讲清楚、讲深入、经得住追问的技术说明稿。

你可以把这个项目概括为：

> 我实现了一个面向 AI RPG 角色的三层记忆系统。系统会把玩家和 NPC 的对话先缓存在 Redis 中，当对话达到阈值后，异步调用大模型提取用户画像、关键事件和角色反思，并持久化到 MySQL。后续生成回复时，系统会结合短期对话、核心记忆和基于 embedding 相似度检索出的长期记忆，为 NPC 生成更连贯、更个性化的回复。

## 1. 项目解决的问题

普通 LLM 聊天有一个明显问题：模型本身没有稳定记忆。上下文窗口一旦超过限制，早期对话就会丢失，NPC 会忘记玩家偏好、重要剧情选择和历史互动。

这个项目的目标是给 AI 游戏角色提供一套外部记忆系统，让角色能够：

- 记住玩家近期对话。
- 沉淀玩家画像，例如性格、偏好、习惯、重要经历。
- 记住关键剧情事件。
- 通过 RAG 找回历史对话、长期事件、NPC 背景故事。
- 在生成回复时把相关记忆重新注入提示词。

系统不是直接把所有历史聊天拼给大模型，而是按重要性和时效性分层管理。

## 2. 总体架构

系统可以拆成 5 层：

| 层级 | 主要文件 | 作用 |
| --- | --- | --- |
| API 层 | `src/server/api/api_layer/main.py` | 对外提供 FastAPI 接口 |
| 业务编排层 | `controllers/memory_manager.py` | 统一调度短期记忆、长期记忆处理和检索 |
| 记忆处理层 | `controllers/memory_processor.py` | 调用 LLM 提取画像、事件、反思，并写库 |
| RAG 检索层 | `controllers/rag_retriever.py` | 基于 embedding 相似度检索长期记忆 |
| 基础设施层 | `models/mysql_database.py`、`redis_client.py`、`llm_client.py` | MySQL、Redis、LLM 客户端封装 |

核心依赖：

- FastAPI：提供 HTTP API。
- Redis：保存短期记忆和核心记忆缓存。
- MySQL：保存用户画像、事件、反思、历史对话、NPC 故事。
- OpenAI-compatible LLM API：生成 embedding、提取记忆、生成回复。
- Langfuse：用于 LLM 调用观测。
- SQLAlchemy：ORM 和数据库连接管理。

注意：项目早期文档中提到 PostgreSQL + pgvector，但当前主业务代码实际使用 MySQL，并把 embedding 存为 JSON。`database.py`、`init.sql`、`docker-compose.yml` 仍保留 PostgreSQL 版本痕迹。

## 3. 三层记忆设计

### 3.1 短期记忆

短期记忆保存在 Redis 中，对应最近一段对话。

代码位置：

- `models/redis_client.py`
- `controllers/memory_manager.py`

Redis key：

```text
short_term:{user_id}:{project_id}
```

特点：

- 存储当前用户和当前项目下的近期对话。
- 默认 1 小时过期。
- 达到数量阈值后触发长期记忆处理。
- 适合保存高频、临时、最近上下文。

短期记忆的数据格式大致是：

```json
[
  {
    "role": "user",
    "content": "你好，我想了解飞船发生了什么",
    "timestamp": "1750000000"
  },
  {
    "role": "assistant",
    "content": "我还在努力恢复系统日志...",
    "timestamp": "1750000001"
  }
]
```

### 3.2 核心记忆

核心记忆指最重要、生成回复时应该直接注入的内容。

包含：

- 用户画像：`Memory_user_profiles`
- 核心事件：`Memory_core_events`
- 核心反思：`Memory_core_reflections`

核心记忆同时存在 MySQL 和 Redis：

- MySQL 是权威存储。
- Redis 是加速读取的缓存。

Redis key：

```text
core_memory:{user_id}:{project_id}
```

生成回复时，核心记忆会直接拼入 prompt，不需要 RAG 筛选。

### 3.3 长期记忆

长期记忆指数量可能较多、需要按相关性召回的内容。

包含：

- 实体事件：`Memory_entity_events`
- 长期反思：`Memory_long_term_reflections`
- 对话日志：`Memory_dialogue_logs`
- NPC 故事：`Memory_npc_stories`

长期记忆都会保存 embedding。检索时，系统会给用户当前 query 生成 embedding，然后和数据库里保存的 embedding 算余弦相似度，取 top K。

## 4. 数据库表设计

当前主线数据模型在 `src/server/api/models/mysql_database.py`。

| 表名 | ORM 类 | 作用 |
| --- | --- | --- |
| `Memory_user_profiles` | `UserProfile` | 保存用户画像 JSON、对话计数 |
| `Memory_core_events` | `CoreEvent` | 保存重大剧情/用户事件 |
| `Memory_entity_events` | `EntityEvent` | 保存普通实体事件，带 embedding |
| `Memory_core_reflections` | `CoreReflection` | 保存重要反思 |
| `Memory_long_term_reflections` | `LongTermReflection` | 保存普通长期反思，带 embedding |
| `Memory_npc_stories` | `NpcStory` | 保存 NPC 背景故事，带 embedding |
| `Memory_dialogue_logs` | `DialogueLog` | 保存完整历史对话，带 embedding |

重点字段：

- `user_id`：区分不同玩家。
- `project_id`：区分不同游戏/世界/项目。
- `content`：记忆文本内容。
- `embedding`：文本向量，MySQL JSON 格式保存。
- `profile_json`：用户画像结构化 JSON。
- `dialogue_count`：累计处理过的对话数，用来触发核心记忆整合。

`UserProfile` 对 `user_id + project_id` 加了唯一约束，保证同一个用户在同一个项目下只有一份画像。

## 5. 写入链路：一句对话如何变成记忆

入口：

```text
POST /api/memory/dialogue
```

对应代码：

- `api_layer/main.py` 的 `add_dialogue`
- `memory_manager.py` 的 `add_dialogue`

流程：

1. API 接收 `user_id`、`project_id`、`role`、`content`。
2. `MemoryManager.add_dialogue()` 从 Redis 读取当前短期记忆。
3. 把新消息 append 到列表末尾。
4. 如果超过 `SHORT_TERM_MEMORY_SIZE`，只保留最后 N 条。
5. 写回 Redis。
6. 如果短期记忆数量达到 `MEMORY_THRESHOLD`，返回 `should_process_memory = true`。
7. API 层发现需要处理，则自动调用 `process_memory()`。

阈值来自环境变量：

```text
MEMORY_THRESHOLD
SHORT_TERM_MEMORY_SIZE
MEMORY_CONSOLIDATION_TRIGGER_ROUNDS
```

代码默认值：

- 记忆处理阈值：60
- 短期记忆长度：60
- 核心记忆整合触发轮数：240

## 6. 记忆处理链路

入口：

```text
POST /api/memory/process
```

核心代码：

- `MemoryManager.process_memory()`
- `MemoryProcessor.process_memory_pipeline()`

处理流程：

1. 从 Redis 读取短期记忆。
2. 检查用户画像是否存在，不存在则提示先初始化用户。
3. 更新用户的 `dialogue_count`。
4. 并行执行 3 个 LLM 任务：
   - `extract_user_profile()`：提取用户画像。
   - `extract_events()`：提取核心事件和实体事件。
   - `generate_reflection()`：生成核心反思和长期反思。
5. 把成功结果写入 MySQL。
6. 给长期记忆类型生成 embedding。
7. 清空 Redis 中的短期记忆。
8. 从 MySQL 重新聚合核心记忆并写入 Redis。
9. 如果累计对话数达到整合阈值，则调用 LLM 合并核心事件和核心反思。

这里有一个面试亮点：记忆处理不是一次只做一个 LLM 调用，而是用 `asyncio.gather()` 并行调用画像、事件、反思三个任务，减少总耗时。

同时，代码用 `return_exceptions=True`，某一个 LLM 任务失败时，不会让整个流水线完全失败，而是保留其他成功结果。这是降级设计。

## 7. LLM 在系统中的职责

LLM 不是只用来聊天，而是承担了 5 类任务：

| 方法 | 作用 |
| --- | --- |
| `generate_embedding()` | 生成文本向量 |
| `extract_user_profile()` | 从对话中抽取用户画像 |
| `extract_events()` | 抽取核心事件和实体事件 |
| `generate_reflection()` | 生成核心反思和长期反思 |
| `consolidate_memories()` | 合并过多的核心记忆 |
| `generate_npc_response()` | 结合记忆上下文生成回复 |

代码位置：

- `models/llm_client.py`
- `models/llm_client_database.py`

`llm_client.py` 里 prompt 写死在代码中。

`llm_client_database.py` 是升级版本，可以从数据库读取 prompt 模板，支持版本管理。它依赖：

- `prompt_templates`
- `prompt_versions`

对应管理接口在 `routes/rpg_memory_prompts.py`。

## 8. 记忆上下文获取与 RAG 检索链路

入口：

```text
POST /api/memory/context
```

核心代码：

- `MemoryManager.get_memory_context()`
- `RAGRetriever.retrieve_long_term_memory()`

这里要区分两个概念：

- 广义的“记忆上下文获取”：为本轮回复组装所有可用记忆，包括短期记忆、核心记忆和长期记忆。
- 狭义的“RAG 检索”：只针对长期记忆，根据 query embedding 做相似度召回。

所以读取 Redis 短期记忆和核心记忆不是 RAGRetriever 的职责，而是 `MemoryManager.get_memory_context()` 在组装完整上下文时做的事情。

完整上下文获取流程：

1. 读取 Redis 短期记忆。
2. 读取 Redis 核心记忆。
3. 调用 `RAGRetriever.retrieve_long_term_memory()` 检索长期记忆。

狭义 RAG 检索流程：

1. 对当前 query 调用 embedding 模型。
2. 并行检索四类长期记忆：
   - 实体事件
   - 历史对话
   - 长期反思
   - NPC 故事
3. 对每条候选记忆计算余弦相似度。
4. 按相似度倒序排序。
5. 返回 top K 结果。

余弦相似度公式：

```text
similarity = dot(vec1, vec2) / (norm(vec1) * norm(vec2))
```

代码中会把结果裁剪到 `[0, 1]` 范围，避免异常值影响排序。

## 9. 对话日志的上下文召回

普通 RAG 只召回单条最相似文本，但单条历史对话可能缺上下文。

这个项目对历史对话做了增强：

1. 先找出最相似的历史对话，称为 anchor。
2. 对每个 anchor，向前取 4 条、向后取 5 条。
3. 形成一组上下文连贯的历史对话。

这样生成回复时，模型看到的不是孤立一句话，而是一段有前因后果的聊天片段。

这是一个很好讲的亮点：

> 我没有只做 naive top-k 检索，而是针对对话型数据做了上下文窗口召回，避免模型只看到片段导致误解。

## 10. 生成回复链路

入口：

```text
POST /api/memory/generate_response
```

对应代码：

- `api_layer/main.py` 的 `generate_response`
- `llm_client.py` 的 `generate_npc_response`

流程：

1. 先用用户最新消息作为 query 获取记忆上下文。
2. 拆出短期记忆、核心记忆、长期记忆检索结果。
3. 拼接完整 prompt：
   - 对话历史
   - 核心记忆
   - 相关长期记忆
   - 用户最新消息
4. 调 LLM 生成 NPC 回复。
5. 把 NPC 回复再写入短期记忆。

注意：这个 API 会自动保存 assistant 回复，所以用户消息和 NPC 回复都能进入记忆系统。

## 11. 初始化用户记忆

入口：

```text
POST /api/memory/initialize
```

作用：

- 如果用户画像不存在，就创建一条空画像。
- 初始化 Redis 短期记忆为空列表。
- 初始化 Redis 核心记忆。

面试时可以说：

> 我把用户记忆空间按 `user_id + project_id` 隔离，避免不同玩家或不同游戏世界的记忆串台。

## 12. Prompt 版本管理模块

除主记忆服务外，项目还有一套提示词版本管理服务。

启动文件：

```text
rpg_memory_api_server.py
```

路由文件：

```text
src/server/api/routes/rpg_memory_prompts.py
```

默认端口：

```text
8888
```

管理的 5 个 prompt：

| key | 作用 |
| --- | --- |
| `rpg_extract_user_profile` | 用户画像提取 |
| `rpg_extract_events` | 事件提取 |
| `rpg_generate_reflection` | 反思生成 |
| `rpg_consolidate_memories` | 记忆整合 |
| `rpg_generate_npc_response` | NPC 回复生成 |

支持能力：

- 查询所有模板。
- 查询某个模板的版本。
- 查询当前发布版本。
- 创建新版本。
- 修改未发布版本。
- 发布版本。
- 删除未发布版本。
- 清理 LLM prompt 缓存。

面试价值：

> 这部分体现了 prompt 工程的工程化，不是把提示词硬编码后不可维护，而是支持版本、发布和回滚。

## 13. 文件结构说明

### 13.1 核心业务代码

```text
src/server/api/api_layer/main.py
```

FastAPI 主入口，定义记忆系统 REST API。

```text
src/server/api/memory_interface.py
```

给其他模块直接调用的 Python 接口，不需要走 HTTP。

```text
src/server/api/controllers/memory_manager.py
```

记忆系统总调度器，负责短期记忆写入、触发处理、上下文聚合、初始化。

```text
src/server/api/controllers/memory_processor.py
```

记忆处理流水线，负责调用 LLM 提取信息、生成 embedding、写入 MySQL、核心记忆整合。

```text
src/server/api/controllers/rag_retriever.py
```

长期记忆检索器，负责 embedding 检索、相似度计算、上下文对话召回。

### 13.2 基础设施代码

```text
src/server/api/models/mysql_database.py
```

当前主线数据库模型，使用 MySQL。

```text
src/server/api/models/database.py
```

旧 PostgreSQL + pgvector 版本模型，当前不是主线。

```text
src/server/api/models/redis_client.py
```

Redis 封装，保存短期记忆和核心记忆缓存。

```text
src/server/api/models/llm_client.py
```

LLM 客户端，prompt 写在代码里。

```text
src/server/api/models/llm_client_database.py
```

LLM 客户端增强版，从数据库加载 prompt 模板。

### 13.3 脚本和工具

```text
run.py
```

项目管理脚本，包含安装、启动、初始化、测试命令。但其中部分逻辑仍偏 PostgreSQL 旧版本。

```text
setup_mysql_database.py
```

MySQL 初始化脚本，创建数据库和表。

```text
update_user_profile_table.py
```

给 `Memory_user_profiles` 补 `dialogue_count` 字段。

```text
import_csv_to_memory.py
```

从 `rowData.csv` 导入历史聊天数据到记忆系统。

```text
verify_import.py
```

验证 CSV 导入后是否能检索到相关记忆。

```text
scripts/init_npc_stories.py
```

读取 `Aliya长期记忆.md`，切块后写入 NPC 故事记忆表。

```text
scripts/test_chunking.py
```

测试 Markdown 切块策略。

```text
pocketflow.py
```

一个轻量流程编排框架，但当前业务主链路未实际使用。

### 13.4 测试文件

```text
run_tests.py
```

统一测试入口。

```text
test_quick_memory_check.py
```

快速检查 Redis、MySQL、初始化、对话写入、上下文获取。

```text
test_comprehensive_memory_system.py
```

综合测试，覆盖连接、初始化、处理流水线、RAG、缓存、并发和一致性。

```text
test_memory_performance.py
```

性能测试，关注响应时间、吞吐、并发、缓存、LLM 调用耗时。

```text
test_memory_interface.py
```

测试直接调用版接口。

```text
test_memory_features.py
```

偏调试型测试，打印完整 prompt 和记忆上下文。

```text
test_memory_consolidation.py
```

测试核心记忆过多后的整合能力。

```text
test_context_dialogue_retrieval.py
```

测试历史对话上下文窗口召回。

```text
test_database_prompts.py
test_database_prompts_simple.py
test_rpg_memory_api.py
```

测试数据库 prompt 管理和提示词版本管理 API。

## 14. 并发与异步设计

项目中主要使用 Python `asyncio`。

并发点：

1. 记忆处理时，用户画像、事件提取、反思生成并行执行。
2. RAG 检索时，实体事件、对话日志、长期反思、NPC 故事并行检索。
3. Redis 使用异步客户端。
4. API 层使用 FastAPI async endpoint。

面试时可以这样讲：

> 这个系统的耗时瓶颈主要在 LLM 调用和 embedding 生成，所以我把互不依赖的任务并行化。例如画像提取、事件提取、反思生成可以并行执行，不需要串行等待。

需要注意：

- 代码中 MySQL 很多地方使用同步 Session，会阻塞事件循环。
- 真正高并发下应该全面使用 AsyncSession，或者把同步数据库操作放到线程池。

这也是一个可优化点。

## 15. 缓存一致性

核心记忆的权威数据在 MySQL，Redis 只是缓存。

写入记忆后，系统会调用 `_update_core_memory()`：

1. 从 MySQL 查用户画像。
2. 查最近核心事件。
3. 查最近核心反思。
4. 组装成 `core_memory`。
5. 写入 Redis。

这样下次获取上下文时不需要频繁查核心表。

潜在问题：

- 如果 `_update_core_memory()` 失败，MySQL 已经更新，但 Redis 仍是旧缓存。
- 当前代码没有强制缓存失效机制，也没有版本号。

优化方案：

- 增加缓存版本号或更新时间校验。
- Redis 读取失败时回源 MySQL。
- 写库和缓存更新失败时记录补偿任务。

## 16. 记忆整合机制

核心事件和核心反思不能无限增长，否则 prompt 会越来越长。

项目通过 `dialogue_count` 触发整合：

```text
MEMORY_CONSOLIDATION_TRIGGER_ROUNDS
```

默认达到 240 条处理过的对话后，调用：

```text
MemoryProcessor.consolidate_core_memories()
```

整合逻辑：

1. 查询核心事件数量。
2. 如果超过限制，取出所有内容。
3. 调 LLM 合并相似项、去重、精简。
4. 删除旧记录。
5. 插入合并后的新记录。
6. 核心反思同理。

这是防止核心记忆无限膨胀的机制。

## 17. 错误处理与降级

系统有一些降级策略：

- Redis 操作失败时返回空列表或空字典。
- embedding 生成失败时返回空向量。
- LLM 提取失败时返回空结果。
- RAG 某一路检索失败时返回空列表，不影响其他路。
- 记忆处理流水线中单个 LLM 任务失败，不一定导致整体失败。

面试时可以讲：

> 记忆系统是增强模块，不应该因为某一类记忆检索失败就阻断主聊天流程，所以设计上尽量让失败局部化。

但也要承认不足：

- 当前多处只是 `print` 错误，没有统一日志和告警。
- 缺少重试队列。
- 缺少失败任务补偿机制。

## 18. 性能分析

主要耗时来源：

1. LLM 生成回复。
2. LLM 提取画像、事件、反思。
3. embedding 生成。
4. RAG 检索时遍历 MySQL 中所有 embedding 并在 Python 中算相似度。

当前 RAG 的时间复杂度：

```text
O(N * D)
```

其中：

- N 是候选记忆数量。
- D 是 embedding 维度。

这意味着数据量大时会变慢。

当前实现优点：

- 简单直观。
- MySQL 即可落地。
- 方便调试。

当前实现缺点：

- 没有真正使用向量索引。
- 每次检索都要取出所有候选 embedding。
- 大规模用户和大规模历史对话下性能会下降。

优化方案：

- 使用 Milvus、Qdrant、FAISS、pgvector、Elasticsearch dense vector。
- 在 MySQL 侧增加粗筛条件，例如时间、类型、用户、关键词。
- embedding 批量生成，减少 LLM API 调用次数。
- 对 NPC 故事这种全局静态数据做内存缓存。
- 给历史对话做分块摘要，减少对话日志数量。

## 19. 安全与工程风险

当前项目存在一些面试官可能追问的问题：

### 19.1 配置安全

部分脚本中存在硬编码数据库连接、监控平台密钥或类似敏感配置。

生产环境应该：

- 全部放入环境变量或密钥管理系统。
- 不把密钥提交到 Git。
- 区分 dev、test、prod 配置。

### 19.2 数据库版本不一致

项目有 MySQL 和 PostgreSQL 两套痕迹。

当前实际主线是：

```text
mysql_database.py
```

旧版本残留：

```text
database.py
init.sql
docker-compose.yml
scripts/init_database.py
```

面试时可以解释：

> 这个项目经历过从 PostgreSQL/pgvector 到 MySQL 的迁移，目前主业务链路已切到 MySQL，但文档和部分脚本还保留旧版本痕迹。后续工程化会清理旧入口，避免部署混乱。

### 19.3 依赖不完整

当前代码使用 `aiomysql`、`pymysql`，但 `requirements.txt` 中不一定完整体现。

优化：

- 补齐依赖。
- 增加启动前依赖检查。
- 使用 lock 文件保证环境可复现。

### 19.4 异步和同步混用

FastAPI endpoint 是 async，但部分数据库操作使用同步 Session。

风险：

- 高并发下阻塞事件循环。

优化：

- 全面迁移到 AsyncSession。
- 或将同步 DB 操作放入线程池。

## 20. 项目亮点总结

面试时可以重点讲这些：

1. 三层记忆架构：Redis 短期记忆、MySQL 核心记忆、embedding 长期记忆。
2. LLM 不只生成回复，还承担结构化记忆抽取任务。
3. 使用 `user_id + project_id` 做记忆隔离。
4. 对核心记忆和长期记忆采用不同策略：核心直接注入，长期 RAG 检索。
5. 记忆处理使用并发 LLM 调用降低耗时。
6. 对历史对话不是只召回单条，而是召回上下文窗口。
7. 有核心记忆整合机制，防止 prompt 膨胀。
8. 有 prompt 数据库版本管理，支持提示词工程化。
9. 有测试体系，覆盖快速检查、综合功能、性能和 prompt API。

## 21. 面试自我介绍口径

可以这样讲：

> 我做的是一个面向 AI RPG 的记忆系统。核心问题是大模型上下文有限，NPC 容易忘记玩家的历史选择和偏好。所以我设计了三层记忆：Redis 保存最近对话，MySQL 保存用户画像和核心事件，长期记忆通过 embedding 检索。玩家对话达到阈值后，系统会并发调用 LLM 提取画像、事件和反思，并持久化。回复生成时，会先聚合短期记忆、核心记忆和 RAG 检索出的长期记忆，再交给 LLM 生成更个性化的 NPC 回复。为了避免核心记忆无限增长，我还实现了基于 LLM 的记忆整合机制。

## 22. 常见面试追问与回答

### Q1：为什么要分短期记忆、核心记忆、长期记忆？

答：

短期记忆解决最近上下文问题，要求读写快，所以放 Redis。核心记忆是对玩家长期稳定的重要认知，例如画像、重大事件、关键反思，生成回复时必须直接注入。长期记忆数量大，不适合全量注入，所以用 embedding 做相关性检索。三层分开可以控制 prompt 长度，也能平衡实时性和长期一致性。

### Q2：为什么核心记忆不走 RAG？

答：

核心记忆是高优先级信息，例如玩家身份、长期偏好、重大剧情选择。如果也走 RAG，可能因为 query 不相似而漏掉，导致 NPC 忘记关键事实。所以核心记忆直接注入，长期记忆才按相关性召回。

### Q3：RAG 是怎么做的？

答：

写入长期记忆时先生成 embedding，保存到 MySQL JSON 字段。检索时给用户当前 query 生成 embedding，然后读取候选记忆，计算余弦相似度，按分数排序取 top K。对历史对话还做了上下文窗口召回，命中 anchor 后取前 4 条和后 5 条，保证对话片段连贯。

### Q4：当前 RAG 有什么性能瓶颈？

答：

当前实现是在 Python 中遍历候选 embedding 计算相似度，数据量大时是 O(N * D)，不适合大规模生产。后续可以迁移到向量数据库或 pgvector，通过向量索引把检索复杂度降下来，也可以增加关键词、时间、类型等粗筛条件。

### Q5：为什么使用 Redis？

答：

短期对话读写频率高、生命周期短、对实时性要求高，Redis 很适合做缓存。它可以快速 append/读取近期对话，并设置过期时间，避免短期上下文长期占用数据库。

### Q6：为什么用户画像用 JSON？

答：

用户画像字段是半结构化的，例如性格、兴趣、偏好、社交关系等，不同玩家可能字段不完全一致。用 JSON 可以灵活扩展，避免频繁改表。后续如果某些字段变成强查询需求，可以再拆成结构化列。

### Q7：如何避免记忆无限增长？

答：

短期记忆通过 `SHORT_TERM_MEMORY_SIZE` 截断。核心记忆通过 `MEMORY_CONSOLIDATION_TRIGGER_ROUNDS` 触发 LLM 整合，合并相似项、删除冗余项。长期记忆目前主要持久保存，后续可以增加摘要、过期、重要性评分和冷热分层。

### Q8：如果 LLM 记忆提取失败怎么办？

答：

当前流水线用 `asyncio.gather(return_exceptions=True)`，单个任务失败不会拖垮所有任务。失败的任务返回空结果，成功的画像、事件或反思仍然会入库。这样保证记忆系统有降级能力。

### Q9：如何保证记忆不串用户？

答：

所有记忆表和 Redis key 都包含 `user_id` 和 `project_id`。MySQL 查询也按这两个字段过滤。用户画像表还对 `user_id + project_id` 加了唯一约束，保证每个玩家在每个项目下只有一份画像。

### Q10：系统怎么观测 LLM 调用？

答：

LLM 客户端接入了 Langfuse，关键方法上有 observe 标记，可以追踪画像提取、事件提取、反思生成、记忆整合和回复生成等调用，便于排查 prompt、耗时和输出质量问题。

### Q11：这个项目最大的问题是什么？

答：

如果从工程化角度看，主要问题有三个：第一，MySQL 和 PostgreSQL 两套历史实现并存，文档需要清理；第二，RAG 目前没有真正使用向量索引，大规模性能不够；第三，部分异步接口内部使用同步数据库会话，高并发下可能阻塞。后续我会优先统一数据库方案、引入向量索引、重构异步数据库访问。

### Q12：如果让你重构，你会怎么做？

答：

我会按优先级做：

1. 清理旧 PostgreSQL 入口或明确双版本支持。
2. 补齐依赖和环境配置，移除硬编码敏感信息。
3. 把 MySQL 同步 Session 全部换成 AsyncSession。
4. 引入向量数据库或 pgvector。
5. 给记忆增加重要性评分、时间衰减和摘要层。
6. 增加后台任务队列，例如 Celery/RQ，避免 API 请求同步等待记忆处理。
7. 增加结构化日志、指标监控和失败重试。

## 23. 可优化方向

### 23.1 架构优化

- 记忆处理改成后台任务队列。
- 主聊天链路只写短期记忆，不阻塞用户回复。
- 后台异步做记忆抽取、embedding 和入库。

### 23.2 检索优化

- 引入向量数据库。
- 支持 hybrid search：关键词检索 + 向量检索。
- 增加 recency bias，让近期记忆更容易被召回。
- 增加 memory importance score。

### 23.3 Prompt 优化

- 统一使用数据库 prompt 版本管理。
- 给 prompt 增加灰度发布和回滚。
- 对 LLM 输出 JSON 增加 schema 校验。
- JSON 解析失败时做自动修复。

### 23.4 数据治理

- 增加用户数据删除能力。
- 增加敏感信息过滤。
- 增加记忆来源追踪。
- 为每条记忆记录置信度。

### 23.5 测试优化

- 区分单元测试和集成测试。
- Mock LLM，降低测试成本。
- CI 中只跑不依赖外部服务的测试。
- 单独提供需要 MySQL、Redis、LLM 的集成测试 profile。

## 24. 你需要真正理解的代码调用关系

最重要的一条写入链：

```text
main.py:add_dialogue
  -> memory_manager.add_dialogue
  -> redis_client.get_short_term_memory
  -> redis_client.store_short_term_memory
  -> memory_manager.process_memory
  -> memory_processor.process_memory_pipeline
  -> llm_client.extract_user_profile
  -> llm_client.extract_events
  -> llm_client.generate_reflection
  -> memory_processor._store_memory
  -> mysql_database tables
  -> memory_manager._update_core_memory
  -> redis_client.store_core_memory
```

最重要的一条读取链：

```text
main.py:get_memory_context
  -> memory_manager.get_memory_context
  -> redis_client.get_short_term_memory
  -> redis_client.get_core_memory
  -> rag_retriever.retrieve_long_term_memory
  -> llm_client.generate_embedding
  -> _retrieve_entity_events
  -> _retrieve_dialogue_logs
  -> _retrieve_long_term_reflections
  -> _retrieve_npc_stories
  -> return memory context
```

生成回复链：

```text
main.py:generate_response
  -> memory_manager.get_memory_context
  -> llm_client.generate_npc_response
  -> memory_manager.add_dialogue(role="assistant")
```

## 25. 面试讲解顺序建议

建议你按这个顺序讲：

1. 先讲业务背景：AI NPC 容易失忆。
2. 再讲总体方案：三层记忆 + RAG + LLM 抽取。
3. 讲写入流程：对话进入 Redis，达到阈值后抽取长期记忆。
4. 讲读取流程：短期 + 核心 + RAG 长期记忆一起组成上下文。
5. 讲一个技术亮点：上下文对话召回、记忆整合、prompt 版本管理任选两个。
6. 主动讲不足：向量检索性能、同步 DB、文档旧版本残留。
7. 最后讲优化方向：向量数据库、后台任务、异步 DB、观测和数据治理。

主动说不足并给出方案，会比只说项目完美更可信。

## 26. 一句话总结

这个项目的核心价值不是“调了一个聊天接口”，而是把 AI 角色长期记忆工程化了：通过分层存储、LLM 结构化抽取、embedding 检索、核心记忆缓存和 prompt 版本管理，让 NPC 能够持续记住玩家，并在后续对话中用得上这些记忆。
