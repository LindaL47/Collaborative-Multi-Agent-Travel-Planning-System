# MySQL数据库设置指南

## 前提条件

1. **确保MySQL服务已安装并运行**
   - 检查MySQL服务状态
   - 确保可以连接到MySQL服务器

## 步骤1: 创建MySQL用户和数据库

### 方法1: 使用MySQL命令行（推荐）

1. **连接到MySQL服务器**（使用root用户）:
   ```bash
   mysql -u root -p
   ```

2. **创建数据库**:
   ```sql
   CREATE DATABASE IF NOT EXISTS aigame_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **创建用户并授权**:
   ```sql
   CREATE USER IF NOT EXISTS 'aigame_user'@'localhost' IDENTIFIED BY 'aigame_strong_password_123';
   GRANT ALL PRIVILEGES ON aigame_db.* TO 'aigame_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

4. **验证用户创建**:
   ```sql
   SELECT User, Host FROM mysql.user WHERE User = 'aigame_user';
   ```

5. **退出MySQL**:
   ```sql
   EXIT;
   ```

### 方法2: 使用MySQL Workbench或其他图形界面工具

1. 连接到MySQL服务器
2. 创建新的数据库 `aigame_db`
3. 创建新用户 `aigame_user` 密码 `aigame_strong_password_123`
4. 给用户授予对 `aigame_db` 数据库的所有权限

## 步骤2: 测试连接

运行测试脚本验证连接:
```bash
python setup_mysql_database.py
```

如果连接成功，脚本将自动创建所有必要的数据表。

## 步骤3: 验证表结构

运行完整的连接测试:
```bash
python test_mysql_connection.py
```

## 步骤4: 更新环境配置

1. **备份原始配置**:
   ```bash
   copy .env .env.postgresql.backup
   ```

2. **使用MySQL配置**:
   ```bash
   copy .env.mysql .env
   ```

## 步骤5: 数据迁移（可选）

如果需要从PostgreSQL迁移现有数据:
```bash
python migrate_to_mysql.py
```

## 创建的数据表

系统将创建以下带有 `Memory_` 前缀的表:

1. **Memory_user_profiles** - 用户画像
2. **Memory_core_events** - 核心事件
3. **Memory_entity_events** - 实体事件
4. **Memory_core_reflections** - 核心反思
5. **Memory_long_term_reflections** - 长期反思
6. **Memory_npc_stories** - NPC故事
7. **Memory_dialogue_logs** - 对话日志

## 故障排除

### 问题1: 连接被拒绝
```
Access denied for user 'aigame_user'@'localhost'
```

**解决方案**:
- 确保用户已创建
- 检查密码是否正确
- 确保用户有适当的权限

### 问题2: MySQL服务未运行
```
Can't connect to MySQL server
```

**解决方案**:
- 启动MySQL服务
- 检查端口3306是否开放
- 确认MySQL安装正确

### 问题3: 缺少依赖包
```
'cryptography' package is required
```

**解决方案**:
```bash
pip install cryptography aiomysql pymysql
```

## 配置验证

成功设置后，你应该能够:

1. ✅ 连接到MySQL数据库
2. ✅ 看到所有7个Memory_前缀的表
3. ✅ 执行基本的CRUD操作
4. ✅ 运行应用程序的异步数据库操作

## 下一步

1. 重启RPG记忆系统应用
2. 测试所有API接口
3. 验证数据存储和检索功能
4. 监控数据库性能

---

**注意**: 请确保在生产环境中使用更强的密码，并根据安全最佳实践配置MySQL。