-- 启用pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建索引以提高向量搜索性能
-- 注意：这些索引会在SQLAlchemy创建表后自动应用

-- 为user_events表的embedding字段创建索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS user_events_embedding_idx ON user_events USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 为reflections表的embedding字段创建索引  
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS reflections_embedding_idx ON reflections USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 为npc_stories表的embedding字段创建索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS npc_stories_embedding_idx ON npc_stories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 为dialogue_logs表的embedding字段创建索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS dialogue_logs_embedding_idx ON dialogue_logs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 设置数据库配置以优化向量操作
ALTER SYSTEM SET shared_preload_libraries = 'vector';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- 重新加载配置
SELECT pg_reload_conf();

-- 创建用于向量搜索的函数（可选）
CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector)
RETURNS float AS $$
BEGIN
    RETURN 1 - (a <=> b);
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL with pgvector extension initialized successfully!';
    RAISE NOTICE 'Database: mydatabase';
    RAISE NOTICE 'User: user';
    RAISE NOTICE 'Vector extension enabled: %', (SELECT extname FROM pg_extension WHERE extname = 'vector');
END $$;