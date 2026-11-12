-- MySQL数据库初始化脚本
-- 为RPG记忆系统创建数据库和表结构

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS aigame_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE aigame_db;

-- 创建用户画像表
CREATE TABLE IF NOT EXISTS Memory_user_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    profile_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_Memory_user_profiles_user_id (user_id),
    INDEX idx_Memory_user_profiles_project_id (project_id),
    INDEX idx_Memory_user_profiles_user_project (user_id, project_id)
);

-- 创建核心事件表
CREATE TABLE IF NOT EXISTS Memory_core_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_Memory_core_events_user_id (user_id),
    INDEX idx_Memory_core_events_project_id (project_id),
    INDEX idx_Memory_core_events_user_project (user_id, project_id)
);

-- 创建实体事件表
CREATE TABLE IF NOT EXISTS Memory_entity_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_Memory_entity_events_user_id (user_id),
    INDEX idx_Memory_entity_events_project_id (project_id),
    INDEX idx_Memory_entity_events_user_project (user_id, project_id)
);

-- 创建核心反思表
CREATE TABLE IF NOT EXISTS Memory_core_reflections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_Memory_core_reflections_user_id (user_id),
    INDEX idx_Memory_core_reflections_project_id (project_id),
    INDEX idx_Memory_core_reflections_user_project (user_id, project_id)
);

-- 创建长期反思表
CREATE TABLE IF NOT EXISTS Memory_long_term_reflections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_Memory_long_term_reflections_user_id (user_id),
    INDEX idx_Memory_long_term_reflections_project_id (project_id),
    INDEX idx_Memory_long_term_reflections_user_project (user_id, project_id)
);

-- 创建NPC故事表
CREATE TABLE IF NOT EXISTS Memory_npc_stories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    story_name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding JSON,
    INDEX idx_Memory_npc_stories_story_name (story_name)
);

-- 创建对话日志表
CREATE TABLE IF NOT EXISTS Memory_dialogue_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_Memory_dialogue_logs_user_id (user_id),
    INDEX idx_Memory_dialogue_logs_project_id (project_id),
    INDEX idx_Memory_dialogue_logs_user_project (user_id, project_id),
    INDEX idx_Memory_dialogue_logs_role (role),
    INDEX idx_Memory_dialogue_logs_created_at (created_at)
);

-- 显示创建的表
SHOW TABLES;

-- 显示表结构
DESCRIBE Memory_user_profiles;
DESCRIBE Memory_core_events;
DESCRIBE Memory_entity_events;
DESCRIBE Memory_core_reflections;
DESCRIBE Memory_long_term_reflections;
DESCRIBE Memory_npc_stories;
DESCRIBE Memory_dialogue_logs;