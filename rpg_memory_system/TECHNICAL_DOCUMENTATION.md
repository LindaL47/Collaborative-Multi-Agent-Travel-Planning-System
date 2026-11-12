# RPG 记忆系统技术文档

## 🎯 系统概述

RPG记忆系统是一个基于三层记忆架构的智能AI游戏记忆管理系统，专为RPG游戏中的AI角色提供智能记忆管理和检索能力。系统实现了短期记忆、核心记忆和长期记忆的分层管理，支持并行处理和RAG检索，让AI角色拥有真正的记忆能力。

## 🏗️ 系统架构

### 核心架构设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              API 接口层                                  │
│                   (memory_interface.py / FastAPI)                       │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────────────┐
│                         记忆管理器层                                      │
│                    (MemoryManager)                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │   记忆处理器     │  │   RAG检索器     │  │   核心记忆管理   │          │
│  │MemoryProcessor │  │  RAGRetriever   │  │   CoreMemory    │          │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘          │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────────────┐
│                         三层记忆存储                                      │
│ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│ │   短期记忆       │  │   核心记忆       │  │   长期记忆       │           │
│ │   (Redis)       │  │(内存+数据库)     │  │ (PostgreSQL)    │           │
│ │                 │  │                 │  │                 │           │
│ │ • 对话历史       │  │ • 用户画像       │  │ • 实体事件       │           │
│ │ • 临时状态       │  │ • 重大事件       │  │ • 对话记录       │           │
│ │ • 会话上下文     │  │ • 重大反思       │  │ • 长期反思       │           │
│ │                 │  │                 │  │ • NPC故事       │           │
│ └─────────────────┘  └─────────────────┘  └─────────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 三层记忆架构详解

#### 1. 短期记忆 (Short-term Memory)
- **存储介质**: Redis
- **存储内容**: 最近60轮对话历史
- **生命周期**: 会话级别，可设置过期时间
- **特点**: 
  - 高速读写访问
  - 滑动窗口管理
  - 自动容量控制

#### 2. 核心记忆 (Core Memory)  
- **存储介质**: 内存 + PostgreSQL
- **存储内容**: 
  - 用户画像 (User Profile)
  - 重大事件 (Core Events) 
  - 重大反思 (Core Reflections)
- **特点**:
  - 直接注入到LLM提示词
  - 不通过RAG检索
  - 影响AI角色的核心认知

#### 3. 长期记忆 (Long-term Memory)
- **存储介质**: PostgreSQL + pgvector
- **存储内容**:
  - 实体事件 (Entity Events)
  - 历史对话记录 (Dialogue Logs) 
  - 长期反思 (Long-term Reflections)
  - NPC故事背景 (NPC Stories)
- **特点**:
  - 向量化存储
  - 语义相似度检索
  - 支持大规模记忆搜索

## 🔧 核心模块详解

### 1. 记忆接口层 (memory_interface.py)

这是系统对外的主要接口，提供同步和异步两种调用方式：

#### 核心函数

##### `add_dialogue_to_memory()`
- **功能**: 添加对话到记忆系统
- **参数**:
  - `user_id` (str): 用户唯一标识符
  - `project_id` (str): 项目/游戏标识符，用于区分不同游戏场景
  - `role` (str): 对话角色，"user"表示用户消息，"assistant"表示NPC回复
  - `content` (str): 对话内容文本

- **处理流程**:
  ```python
  用户消息 → 添加到短期记忆 → 检查对话轮数 → 触发记忆处理(60轮)
  ```

- **返回格式**:
  ```json
  {
    "status": "success",
    "dialogue_count": 45,
    "should_process_memory": false,
    "memory_processing": {
      "status": "success", 
      "processed_events": 3,
      "processed_reflections": 2
    }
  }
  ```

##### `get_memory_context_for_chat()`
- **功能**: 获取记忆上下文用于生成AI回复
- **参数**:
  - `user_id` (str): 用户唯一标识符
  - `project_id` (str): 项目/游戏标识符
  - `query` (str): 用户当前消息内容，用于RAG检索

- **处理流程**:
  ```python
  用户查询 → 获取短期记忆 → 获取核心记忆 → RAG检索长期记忆 → 格式化上下文
  ```

- **返回数据结构**:
  ```json
  {
    "status": "success",
    "short_term_memory": [...],        // 短期记忆对话历史
    "core_memory": {...},              // 核心记忆(用户画像+重大事件+反思)
    "long_term_memory_retrieval": {...}, // RAG检索的长期记忆
    "formatted_context_text": "..."    // 格式化的上下文文本
  }
  ```

#### 使用示例

```python
# 异步调用示例
async def chat_with_ai():
    # 1. 用户发送消息
    user_result = await add_dialogue_to_memory(
        user_id="player_001",
        project_id="fantasy_world",
        role="user", 
        content="告诉我关于这个世界的魔法系统"
    )
    
    # 2. 获取记忆上下文
    memory_context = await get_memory_context_for_chat(
        user_id="player_001",
        project_id="fantasy_world",
        query="告诉我关于这个世界的魔法系统"
    )
    
    # 3. 使用上下文生成AI回复
    context_text = memory_context["formatted_context_text"]
    ai_response = generate_ai_response(context_text, user_query)
    
    # 4. 保存AI回复到记忆
    ai_result = await add_dialogue_to_memory(
        user_id="player_001", 
        project_id="fantasy_world",
        role="assistant",
        content=ai_response
    )

# 同步调用示例  
def chat_with_ai_sync():
    # 使用同步版本的函数
    user_result = add_dialogue_to_memory_sync(
        user_id="player_001",
        project_id="fantasy_world", 
        role="user",
        content="告诉我关于这个世界的魔法系统"
    )
```

### 2. 记忆管理器 (MemoryManager)

记忆管理器是系统的核心协调层，负责统一管理三层记忆的读写操作：

#### 核心职责

1. **短期记忆管理**
   - 维护对话历史的滑动窗口
   - 自动触发记忆处理阈值检查
   - 控制内存使用量

2. **记忆处理协调** 
   - 当对话达到60轮时自动触发记忆处理
   - 协调记忆处理器和RAG检索器
   - 管理核心记忆的更新

3. **上下文生成**
   - 整合短期、核心、长期三层记忆
   - 生成格式化的提示词上下文
   - 控制上下文的长度和质量

#### 关键方法

```python
class MemoryManager:
    async def add_dialogue(user_id, project_id, role, content):
        """添加对话到短期记忆，检查是否需要触发记忆处理"""
        
    async def process_memory(user_id, project_id): 
        """触发记忆处理流水线"""
        
    async def get_memory_context(user_id, project_id, query):
        """获取完整的记忆上下文"""
        
    async def initialize_user_memory(user_id, project_id):
        """初始化新用户的记忆结构"""
```

### 3. 记忆处理器 (MemoryProcessor)

记忆处理器负责分析对话历史，使用LLM提取结构化的记忆信息：

#### 处理流程

```mermaid
graph TD
    A[获取60轮对话历史] --> B[并行LLM处理]
    B --> C[提取用户画像]
    B --> D[提取重大事件] 
    B --> E[提取实体事件]
    B --> F[生成重大反思]
    B --> G[生成长期反思]
    
    C --> H[更新核心记忆]
    D --> H
    F --> H
    
    E --> I[存储到长期记忆]
    G --> I
    
    H --> J[返回处理结果]
    I --> J
```

#### 提取的记忆类型

1. **用户画像 (User Profile)**
   ```json
   {
     "personality": {
       "curiosity_level": "high",
       "preferred_interaction_style": "analytical"
     },
     "interests": ["magic", "history", "combat"],
     "behavior_patterns": {
       "question_frequency": "high",
       "exploration_tendency": "strong"
     }
   }
   ```

2. **重大事件 (Core Events)**
   - 与主要剧情高度相关的核心事件
   - 直接注入到提示词中
   - 影响AI角色的核心认知

3. **实体事件 (Entity Events)** 
   - 用户与特定实体的互动记录
   - 存储在长期记忆中
   - 通过RAG检索获取

4. **重大反思 (Core Reflections)**
   - 对用户行为模式的深度分析
   - 影响AI角色对用户的整体认知

5. **长期反思 (Long-term Reflections)**
   - 一般性的反思和观察
   - 存储在长期记忆中

### 4. RAG检索器 (RAGRetriever)

RAG检索器负责从长期记忆中检索与当前查询相关的记忆片段：

#### 检索类型

1. **实体事件检索**
   - 基于语义相似度检索相关的实体互动记录
   - 使用向量相似度算法

2. **对话记录检索**
   - 检索历史上相似的对话片段
   - 帮助AI角色保持对话一致性

3. **长期反思检索**
   - 检索相关的分析和观察记录
   - 提供深层的用户理解

4. **NPC故事检索**
   - 检索相关的背景故事和世界观信息
   - 丰富对话内容

#### 检索策略

```python
# 并行检索示例
async def retrieve_relevant_memories(query: str, user_id: str, project_id: str):
    # 生成查询向量
    query_embedding = await generate_embedding(query)
    
    # 并行检索不同类型的记忆
    tasks = [
        retrieve_entity_events(query_embedding, user_id, project_id),
        retrieve_dialogue_logs(query_embedding, user_id, project_id), 
        retrieve_long_term_reflections(query_embedding, user_id, project_id),
        retrieve_npc_stories(query_embedding, project_id)
    ]
    
    results = await asyncio.gather(*tasks)
    return format_retrieval_results(results)
```

## 📊 数据模型设计

### 数据库表结构

#### 用户画像表 (user_profiles)
```sql
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    profile_data JSONB NOT NULL,        -- 用户画像JSON数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, project_id)
);
```

#### 核心事件表 (core_events)
```sql
CREATE TABLE core_events (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    event_text TEXT NOT NULL,           -- 事件描述
    importance_score FLOAT DEFAULT 0.0, -- 重要性评分
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 核心反思表 (core_reflections)
```sql
CREATE TABLE core_reflections (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    reflection_text TEXT NOT NULL,      -- 反思内容
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 长期记忆表 (long_term_memories)
```sql
CREATE TABLE long_term_memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,   -- 记忆类型
    content TEXT NOT NULL,              -- 记忆内容
    embedding vector(1536),             -- 向量嵌入
    metadata JSONB,                     -- 元数据
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建向量索引
CREATE INDEX ON long_term_memories USING ivfflat (embedding vector_cosine_ops);
```

#### NPC故事表 (npc_stories)
```sql
CREATE TABLE npc_stories (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    npc_name VARCHAR(255),
    story_content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Redis数据结构

#### 短期记忆存储格式
```python
# Redis Key: "short_term:{user_id}:{project_id}"
# 存储格式: JSON字符串
{
    "messages": [
        {
            "role": "user",
            "content": "用户消息内容",
            "timestamp": "1703123456"
        },
        {
            "role": "assistant", 
            "content": "AI回复内容",
            "timestamp": "1703123460"
        }
    ],
    "last_updated": "1703123460"
}
```

## 🔄 系统工作流程

### 完整的对话处理流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as API接口
    participant MM as 记忆管理器
    participant RC as Redis缓存
    participant MP as 记忆处理器
    participant RAG as RAG检索器
    participant DB as 数据库
    participant LLM as LLM服务

    U->>API: 发送消息
    API->>MM: add_dialogue()
    MM->>RC: 获取短期记忆
    MM->>RC: 添加新消息
    MM->>MM: 检查是否达到60轮
    
    alt 达到60轮触发记忆处理
        MM->>MP: 触发记忆处理
        MP->>LLM: 并行提取记忆信息
        MP->>DB: 更新核心记忆
        MP->>DB: 存储长期记忆
        MP->>MM: 返回处理结果
    end
    
    MM->>API: 返回添加结果
    API->>U: 响应添加成功
    
    U->>API: 请求获取记忆上下文
    API->>MM: get_memory_context()
    MM->>RC: 获取短期记忆
    MM->>DB: 获取核心记忆
    MM->>RAG: RAG检索长期记忆
    RAG->>DB: 向量相似度搜索
    RAG->>MM: 返回检索结果
    MM->>MM: 格式化上下文
    MM->>API: 返回记忆上下文
    API->>U: 返回格式化的记忆上下文
```

### 记忆处理详细流程

```mermaid
graph TD
    A[获取60轮对话历史] --> B{启动并行处理}
    
    B --> C[Task 1: 用户画像提取]
    B --> D[Task 2: 重大事件提取] 
    B --> E[Task 3: 实体事件提取]
    B --> F[Task 4: 重大反思生成]
    B --> G[Task 5: 长期反思生成]
    
    C --> H[LLM分析用户行为模式]
    D --> I[LLM识别关键剧情事件]
    E --> J[LLM提取实体互动记录]
    F --> K[LLM生成深度反思]
    G --> L[LLM生成一般观察]
    
    H --> M[更新用户画像]
    I --> N[存储核心事件]
    K --> O[存储核心反思]
    
    J --> P[向量化实体事件]
    L --> Q[向量化长期反思]
    
    P --> R[存储到长期记忆表]
    Q --> R
    
    M --> S[返回处理结果]
    N --> S
    O --> S
    R --> S
```

## 🚀 部署和配置

### 环境配置

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/rpg_memory
REDIS_URL=redis://localhost:6379/0

# LLM配置 (豆包模型)
DOUBAO_API_KEY=your_doubao_api_key_here
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL_NAME=ep-20241201193721-8xvxz
DOUBAO_EMBEDDING_MODEL=ep-20241201193721-8xvxz

# 记忆系统配置
MEMORY_PROCESSING_TRIGGER_ROUNDS=60    # 触发记忆处理的对话轮数
RAG_RETRIEVAL_TOP_K=5                  # RAG检索返回的记录数
SHORT_TERM_MEMORY_SIZE=60              # 短期记忆容量

# Langsmith配置 (可选)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=rpg-memory-system
```

### 使用管理脚本部署

```bash
# 完整设置
python run.py setup

# 启动API服务
python run.py server

# 检查系统状态
python run.py check
```

### Docker部署

```bash
# 启动数据库服务
docker-compose up -d

# 初始化数据库
python run.py db-init

# 导入NPC故事数据
python run.py npc-init
```

## 📈 性能优化策略

### 1. 数据库优化

#### 向量索引优化
```sql
-- 使用IVFFlat索引加速向量搜索
CREATE INDEX CONCURRENTLY idx_long_term_memories_embedding 
ON long_term_memories USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 定期维护索引
REINDEX INDEX idx_long_term_memories_embedding;
```

#### 查询优化
```python
# 使用异步连接池
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30

# 批量操作
async def batch_insert_memories(memories: List[Dict]):
    async with get_async_db() as db:
        db.add_all([LongTermMemory(**mem) for mem in memories])
        await db.commit()
```

### 2. 内存优化

#### Redis配置优化
```redis.conf
# 内存使用限制
maxmemory 2gb
maxmemory-policy allkeys-lru

# 持久化策略
save 900 1
save 300 10
save 60 10000
```

#### 短期记忆管理
```python
# 动态调整短期记忆大小
def adjust_memory_size_based_on_usage():
    if memory_usage > 0.8:
        return min(SHORT_TERM_MEMORY_SIZE - 10, 20)
    return SHORT_TERM_MEMORY_SIZE
```

### 3. 并发优化

#### 异步处理
```python
# 使用信号量控制并发
MEMORY_PROCESSING_SEMAPHORE = asyncio.Semaphore(5)

async def process_memory_with_limit(user_id, project_id):
    async with MEMORY_PROCESSING_SEMAPHORE:
        return await memory_processor.process_memory(user_id, project_id)
```

#### 任务队列
```python
# 使用后台任务处理记忆
from celery import Celery

celery_app = Celery('memory_processor')

@celery_app.task
def process_memory_background(user_id: str, project_id: str):
    return asyncio.run(memory_processor.process_memory(user_id, project_id))
```

## 🔍 监控和调试

### 日志配置

```python
import logging

# 配置记忆系统专用日志
logger = logging.getLogger('rpg_memory_system')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# 关键操作日志
logger.info(f"用户 {user_id} 触发记忆处理，对话轮数: {dialogue_count}")
logger.info(f"RAG检索返回 {len(results)} 条记录，查询: {query[:50]}...")
```

### 性能监控

```python
import time
from functools import wraps

def monitor_performance(func_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.info(f"{func_name} 执行耗时: {duration:.2f}秒")
            return result
        return wrapper
    return decorator

@monitor_performance("记忆处理")
async def process_memory(self, user_id: str, project_id: str):
    # 记忆处理逻辑
    pass
```

### 错误处理和恢复

```python
class MemorySystemError(Exception):
    """记忆系统基础异常"""
    pass

class MemoryProcessingError(MemorySystemError):
    """记忆处理异常"""
    pass

class RAGRetrievalError(MemorySystemError):
    """RAG检索异常"""
    pass

async def robust_memory_processing(user_id: str, project_id: str, max_retries: int = 3):
    """带重试机制的记忆处理"""
    for attempt in range(max_retries):
        try:
            return await memory_processor.process_memory(user_id, project_id)
        except MemoryProcessingError as e:
            if attempt == max_retries - 1:
                logger.error(f"记忆处理失败，已重试 {max_retries} 次: {e}")
                raise
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

## 🧪 测试策略

### 单元测试

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

class TestMemoryManager:
    @pytest.fixture
    async def memory_manager(self):
        return MemoryManager()
    
    @pytest.mark.asyncio
    async def test_add_dialogue(self, memory_manager):
        # 测试添加对话功能
        result = await memory_manager.add_dialogue(
            "test_user", "test_project", "user", "测试消息"
        )
        
        assert result["status"] == "success"
        assert result["dialogue_count"] > 0
    
    @pytest.mark.asyncio
    async def test_memory_processing_trigger(self, memory_manager):
        # 测试记忆处理触发
        with patch.object(memory_manager, 'memory_threshold', 2):
            for i in range(3):
                result = await memory_manager.add_dialogue(
                    "test_user", "test_project", "user", f"消息{i}"
                )
            
            assert result["should_process_memory"] == True
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_full_memory_pipeline():
    """测试完整的记忆处理流水线"""
    user_id = "integration_test_user"
    project_id = "test_project"
    
    # 1. 初始化用户记忆
    init_result = await initialize_user_memory(user_id, project_id)
    assert init_result["status"] == "success"
    
    # 2. 添加60轮对话
    for i in range(60):
        await add_dialogue_to_memory(
            user_id, project_id, "user", f"用户消息 {i}"
        )
        await add_dialogue_to_memory(
            user_id, project_id, "assistant", f"AI回复 {i}" 
        )
    
    # 3. 验证记忆处理被触发
    result = await add_dialogue_to_memory(
        user_id, project_id, "user", "触发记忆处理的消息"
    )
    
    assert result["should_process_memory"] == True
    assert "memory_processing" in result
    
    # 4. 验证记忆上下文获取
    context = await get_memory_context_for_chat(
        user_id, project_id, "查询测试"
    )
    
    assert context["status"] == "success"
    assert "core_memory" in context
    assert "long_term_memory_retrieval" in context
```

### 压力测试

```python
import asyncio
import aiohttp
import time

async def stress_test_memory_system():
    """记忆系统压力测试"""
    base_url = "http://localhost:8000"
    concurrent_users = 50
    messages_per_user = 100
    
    async with aiohttp.ClientSession() as session:
        # 创建并发用户
        tasks = []
        for user_id in range(concurrent_users):
            task = simulate_user_interaction(
                session, base_url, f"user_{user_id}", messages_per_user
            )
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        
        print(f"压力测试结果:")
        print(f"总耗时: {duration:.2f}秒")
        print(f"成功率: {success_count}/{concurrent_users} ({success_count/concurrent_users*100:.1f}%)")
        print(f"平均QPS: {(concurrent_users * messages_per_user) / duration:.2f}")

async def simulate_user_interaction(session, base_url, user_id, message_count):
    """模拟用户交互"""
    for i in range(message_count):
        # 添加用户消息
        await session.post(f"{base_url}/api/memory/dialogue", json={
            "user_id": user_id,
            "project_id": "stress_test",
            "role": "user", 
            "content": f"压力测试消息 {i}"
        })
        
        # 获取记忆上下文
        await session.post(f"{base_url}/api/memory/context", json={
            "user_id": user_id,
            "project_id": "stress_test",
            "query": f"压力测试查询 {i}"
        })
        
        await asyncio.sleep(0.01)  # 避免过快请求
```

## 🔧 自定义和扩展

### 添加新的记忆类型

1. **扩展数据模型**
```python
# 在 models/database.py 中添加新表
class CustomMemoryType(Base):
    __tablename__ = "custom_memories"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    project_id = Column(String(255), nullable=False)
    custom_content = Column(Text, nullable=False)
    custom_metadata = Column(JSON)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. **扩展RAG检索器**
```python
# 在 rag_retriever.py 中添加新的检索方法
async def retrieve_custom_memories(
    self, query_embedding: List[float], user_id: str, project_id: str
) -> List[Dict[str, Any]]:
    async with get_async_db() as db:
        results = await db.execute(
            select(CustomMemoryType)
            .where(
                and_(
                    CustomMemoryType.user_id == user_id,
                    CustomMemoryType.project_id == project_id
                )
            )
            .order_by(CustomMemoryType.embedding.cosine_distance(query_embedding))
            .limit(self.retrieval_limit)
        )
        
        return [
            {
                "content": row.custom_content,
                "metadata": row.custom_metadata,
                "similarity": calculate_similarity(query_embedding, row.embedding)
            }
            for row in results.scalars()
        ]
```

3. **集成到记忆管理器**
```python
# 在 memory_manager.py 中集成新的记忆类型
async def get_memory_context(self, user_id: str, project_id: str, query: str):
    # ... 现有逻辑 ...
    
    # 添加自定义记忆检索
    custom_memories = await self.rag_retriever.retrieve_custom_memories(
        query_embedding, user_id, project_id
    )
    
    result["custom_memories"] = custom_memories
    return result
```

### 自定义LLM提示词

编辑 `models/llm_client.py` 中的提示词模板：

```python
# 自定义用户画像提取提示词
CUSTOM_USER_PROFILE_PROMPT = """
基于以下对话历史，分析用户的个性特征：

对话历史：
{dialogue_history}

请从以下维度分析用户：
1. 性格特征（内向/外向、理性/感性等）
2. 兴趣爱好和偏好
3. 互动风格和沟通习惯
4. 决策模式和行为模式
5. 学习和探索倾向

返回JSON格式的分析结果。
"""

# 自定义事件提取提示词  
CUSTOM_EVENT_EXTRACTION_PROMPT = """
从以下对话中提取重要的游戏事件：

对话记录：
{dialogue_history}

提取原则：
1. 与游戏剧情发展直接相关的事件
2. 用户做出的重要决策
3. 重要的物品获得、技能学习
4. 关键的NPC互动
5. 世界观相关的发现

按重要性排序，返回事件列表。
"""
```

### 性能调优配置

```python
# config/performance.py
class PerformanceConfig:
    # 数据库连接池
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 30
    DB_POOL_TIMEOUT = 30
    
    # Redis配置
    REDIS_MAX_CONNECTIONS = 50
    REDIS_CONNECTION_TIMEOUT = 5
    
    # 记忆处理
    MAX_PARALLEL_MEMORY_PROCESSING = 5
    MEMORY_PROCESSING_TIMEOUT = 300
    
    # RAG检索
    RAG_RETRIEVAL_TIMEOUT = 10
    MAX_PARALLEL_RAG_QUERIES = 10
    
    # LLM调用
    LLM_REQUEST_TIMEOUT = 30
    LLM_MAX_RETRIES = 3
    LLM_RETRY_DELAY = 1.0

# 应用配置
def apply_performance_config():
    import asyncio
    
    # 设置异步任务限制
    asyncio.get_event_loop().set_default_executor(
        concurrent.futures.ThreadPoolExecutor(max_workers=20)
    )
```

## 📚 API参考

### REST API接口

#### POST /api/memory/initialize
初始化用户记忆

**请求体:**
```json
{
  "user_id": "string",
  "project_id": "string"
}
```

**响应:**
```json
{
  "status": "success",
  "message": "用户记忆初始化完成"
}
```

#### POST /api/memory/dialogue
添加对话到记忆系统

**请求体:**
```json
{
  "user_id": "string", 
  "project_id": "string",
  "role": "user|assistant",
  "content": "string"
}
```

**响应:**
```json
{
  "status": "success",
  "dialogue_count": 45,
  "should_process_memory": false,
  "memory_processing": {
    "status": "success",
    "processed_events": 3,
    "processed_reflections": 2
  }
}
```

#### POST /api/memory/context  
获取记忆上下文

**请求体:**
```json
{
  "user_id": "string",
  "project_id": "string", 
  "query": "string"
}
```

**响应:**
```json
{
  "status": "success",
  "short_term_memory": [...],
  "core_memory": {...},
  "long_term_memory_retrieval": {...},
  "formatted_context_text": "string"
}
```

#### POST /api/memory/process
手动触发记忆处理

**请求体:**
```json
{
  "user_id": "string",
  "project_id": "string"
}
```

**响应:**
```json
{
  "status": "success", 
  "processed_events": 3,
  "processed_reflections": 2,
  "processing_time": 15.5
}
```

### 函数接口

#### 异步接口

```python
# 添加对话
async def add_dialogue_to_memory(
    user_id: str, 
    project_id: str, 
    role: str, 
    content: str
) -> Dict[str, Any]

# 获取记忆上下文
async def get_memory_context_for_chat(
    user_id: str, 
    project_id: str, 
    query: str
) -> Dict[str, Any]

# 初始化用户记忆
async def initialize_user_memory(
    user_id: str, 
    project_id: str
) -> Dict[str, Any]
```

#### 同步接口

```python
# 同步版本（适用于不支持异步的系统）
def add_dialogue_to_memory_sync(
    user_id: str, 
    project_id: str, 
    role: str, 
    content: str
) -> Dict[str, Any]

def get_memory_context_for_chat_sync(
    user_id: str, 
    project_id: str, 
    query: str  
) -> Dict[str, Any]

def initialize_user_memory_sync(
    user_id: str, 
    project_id: str
) -> Dict[str, Any]
```

## 🚨 故障排除

### 常见问题和解决方案

#### 1. 数据库连接问题

**症状**: `连接数据库失败` 错误

**解决方案**:
```bash
# 检查数据库服务状态
docker-compose ps

# 重启数据库服务  
docker-compose restart postgres

# 检查数据库日志
docker-compose logs postgres

# 验证数据库连接
python -c "
import asyncio
from src.server.api.models.database import test_db_connection
asyncio.run(test_db_connection())
"
```

#### 2. Redis连接问题

**症状**: `Redis连接超时` 错误

**解决方案**:
```bash
# 检查Redis服务
docker-compose ps redis

# 测试Redis连接
redis-cli ping

# 清理Redis缓存
redis-cli flushall
```

#### 3. 记忆处理超时

**症状**: `记忆处理超时` 错误

**解决方案**:
```python
# 调整超时配置
MEMORY_PROCESSING_TIMEOUT = 600  # 增加到10分钟

# 减少并行处理数量
MAX_PARALLEL_MEMORY_PROCESSING = 3

# 检查LLM API状态
async def check_llm_api():
    try:
        response = await llm_client.simple_call("测试")
        print(f"LLM API正常: {response[:50]}...")
    except Exception as e:
        print(f"LLM API异常: {e}")
```

#### 4. 向量检索性能问题

**症状**: RAG检索响应缓慢

**解决方案**:
```sql
-- 重建向量索引
REINDEX INDEX idx_long_term_memories_embedding;

-- 更新表统计信息  
ANALYZE long_term_memories;

-- 检查索引使用情况
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM long_term_memories 
ORDER BY embedding <-> '[0.1,0.2,...]' 
LIMIT 5;
```

#### 5. 内存使用过高

**症状**: 系统内存占用持续增长

**解决方案**:
```python
# 监控内存使用
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    print(f"RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.1f} MB")
    
    # 强制垃圾回收
    gc.collect()

# 定期清理短期记忆
async def cleanup_old_memories():
    # 删除超过7天的短期记忆
    cutoff_time = time.time() - (7 * 24 * 3600)
    pattern = "short_term:*"
    
    async for key in redis_client.scan_iter(match=pattern):
        data = await redis_client.get(key)
        if data and data.get('last_updated', 0) < cutoff_time:
            await redis_client.delete(key)
```

### 日志分析

#### 启用详细日志

```python
import logging

# 设置详细日志级别
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

# 特定模块日志
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)  # SQL查询日志
logging.getLogger('aioredis').setLevel(logging.DEBUG)          # Redis操作日志
```

#### 关键指标监控

```python
import time
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record_operation(self, operation_name: str, duration: float):
        self.metrics[operation_name].append(duration)
    
    def get_stats(self):
        stats = {}
        for operation, durations in self.metrics.items():
            if durations:
                stats[operation] = {
                    'count': len(durations),
                    'avg': sum(durations) / len(durations),
                    'min': min(durations),
                    'max': max(durations)
                }
        return stats

# 使用示例
monitor = PerformanceMonitor()

@monitor_operation("memory_processing")
async def process_memory_with_monitoring(user_id, project_id):
    start_time = time.time()
    try:
        result = await memory_processor.process_memory(user_id, project_id)
        return result
    finally:
        duration = time.time() - start_time
        monitor.record_operation("memory_processing", duration)
```

## 📖 最佳实践

### 1. 记忆设计原则

- **渐进式记忆构建**: 从简单的用户偏好开始，逐步构建复杂的用户画像
- **记忆优先级**: 核心记忆 > 长期记忆检索 > 短期记忆，确保重要信息优先展示
- **上下文平衡**: 控制注入到LLM的上下文长度，避免信息过载

### 2. 性能优化建议

- **批量操作**: 尽量批量处理数据库操作，减少网络往返
- **异步优先**: 使用异步接口提高并发处理能力  
- **缓存策略**: 合理使用Redis缓存热点数据

### 3. 数据质量保证

- **输入验证**: 严格验证用户输入，防止注入攻击
- **数据清洗**: 定期清理无效或过期的记忆数据
- **一致性检查**: 定期检查记忆数据的一致性

### 4. 监控和告警

- **关键指标**: 记忆处理延迟、RAG检索成功率、数据库连接状态
- **告警机制**: 设置合理的告警阈值，及时发现系统异常
- **日志分析**: 定期分析日志，识别潜在问题

## 🎯 总结

RPG记忆系统通过三层记忆架构为AI游戏角色提供了强大的记忆管理能力：

- **短期记忆**提供快速的会话上下文访问
- **核心记忆**确保重要用户信息直接影响AI行为  
- **长期记忆**通过RAG检索提供丰富的背景信息

系统采用现代化的异步架构，支持高并发访问，通过合理的性能优化策略确保在大规模部署环境下的稳定运行。

完善的测试体系和监控机制保证了系统的可靠性，灵活的扩展接口支持根据具体游戏需求进行定制开发。

---

*本文档持续更新中，如有问题请提交Issue或联系开发团队。*