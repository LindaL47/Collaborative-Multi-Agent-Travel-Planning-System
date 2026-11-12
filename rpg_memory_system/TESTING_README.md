# RPG记忆系统测试指南

本文档介绍如何使用记忆系统的测试套件来验证系统功能和性能。

## 📋 测试文件概览

### 1. 测试运行器
- **`run_tests.py`** - 统一的测试入口，提供交互式菜单和命令行接口

### 2. 功能测试文件
- **`test_quick_memory_check.py`** - 快速检查测试，验证基础功能
- **`test_comprehensive_memory_system.py`** - 综合功能测试，全面验证所有模块
- **`test_memory_performance.py`** - 性能基准测试，评估系统性能指标

### 3. 现有测试文件
- **`test_memory_features.py`** - 记忆功能测试（包含Langfuse监控）
- **`test_memory_interface.py`** - 记忆接口测试
- **`test_memory_consolidation.py`** - 记忆整合测试

## 🚀 快速开始

### 方法1: 使用测试运行器（推荐）

```bash
# 进入项目目录
cd /path/to/rpg_memory_system

# 运行交互式测试菜单
python run_tests.py

# 或直接运行特定测试
python run_tests.py quick          # 快速检查
python run_tests.py comprehensive  # 综合测试
python run_tests.py performance    # 性能测试
python run_tests.py all           # 所有测试
```

### 方法2: 直接运行测试文件

```bash
# 快速检查测试
python test_quick_memory_check.py

# 综合功能测试
python test_comprehensive_memory_system.py

# 性能基准测试
python test_memory_performance.py
```

## 📊 测试类型详解

### 1. 快速检查测试 (Quick Check)

**用途**: 日常开发中的快速验证
**耗时**: 1-2分钟
**测试内容**:
- Redis和MySQL连接检查
- 用户记忆初始化
- 基本对话流程
- 记忆上下文获取

**适用场景**:
- 代码修改后的快速验证
- 部署前的基础检查
- 开发环境的健康检查

```bash
python run_tests.py quick
```

### 2. 综合功能测试 (Comprehensive)

**用途**: 全面验证系统功能
**耗时**: 10-15分钟
**测试内容**:
- 所有核心功能模块
- 错误处理和异常情况
- 数据一致性验证
- 并发操作测试
- 边界条件测试

**测试模块**:
- 基础连接测试
- 用户记忆初始化测试
- 对话添加功能测试
- 记忆上下文获取测试
- 记忆处理流水线测试
- LLM客户端功能测试
- RAG检索功能测试
- 定时器功能测试
- 数据库操作测试
- Redis缓存测试
- 错误处理测试
- 性能压力测试
- 数据一致性测试
- 并发操作测试

```bash
python run_tests.py comprehensive
```

### 3. 性能基准测试 (Performance)

**用途**: 评估系统性能指标
**耗时**: 15-20分钟
**测试内容**:
- 响应时间测试
- 吞吐量测试
- 并发性能测试
- 内存使用测试
- 缓存性能测试
- LLM调用性能测试

**输出**:
- 详细的性能报告JSON文件
- 性能指标统计
- 系统资源使用情况

```bash
python run_tests.py performance
```

## 🔧 环境配置

### 必需的环境变量

```bash
# 数据库连接
export DATABASE_URL="mysql+aiomysql://aigame_user:aigame_strong_password_123@121.40.249.125:3306/aigame_db"

# Langfuse配置（可选，用于监控）
export LANGFUSE_SECRET_KEY="your_secret_key"
export LANGFUSE_PUBLIC_KEY="your_public_key"
export LANGFUSE_HOST="your_langfuse_host"
```

### 依赖检查

确保以下服务正常运行：
- MySQL数据库服务
- Redis缓存服务
- 网络连接（用于LLM API调用）

## 📈 测试结果解读

### 成功标准

- **快速检查**: 所有基础功能正常
- **综合测试**: 成功率 ≥ 80%
- **性能测试**: 生成完整的性能报告

### 常见问题排查

#### 1. 连接失败
```
❌ Redis连接失败
❌ MySQL连接失败
```
**解决方案**:
- 检查服务是否启动
- 验证连接配置
- 检查网络连通性

#### 2. LLM调用失败
```
❌ LLM客户端功能测试失败
```
**解决方案**:
- 检查API密钥配置
- 验证网络连接
- 确认API配额

#### 3. 内存不足
```
❌ 性能测试内存使用异常
```
**解决方案**:
- 增加系统内存
- 调整测试参数
- 检查内存泄漏

## 📝 自定义测试

### 添加新的测试用例

1. 在相应的测试文件中添加新的测试方法
2. 遵循现有的测试模式
3. 添加适当的日志和错误处理

示例：
```python
async def test_custom_feature(self) -> bool:
    """测试自定义功能"""
    try:
        # 测试逻辑
        result = await some_function()
        
        if result['status'] == 'success':
            logger.info("✅ 自定义功能测试成功")
            return True
        else:
            logger.error("❌ 自定义功能测试失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 自定义功能测试异常: {str(e)}")
        return False
```

### 修改测试参数

可以通过修改测试类的初始化参数来调整测试行为：

```python
# 在测试类的__init__方法中
self.test_user_id = f"custom_test_{int(time.time())}"
self.test_project_id = f"custom_project_{int(time.time())}"

# 调整测试数据量
self.test_dialogues = [...] # 自定义对话数据
```

## 🔍 调试和日志

### 日志级别

```python
# 修改日志级别以获得更详细的输出
logging.basicConfig(level=logging.DEBUG)
```

### 调试模式

```python
# 在测试文件中启用调试模式
os.environ["DEBUG"] = "true"
```

## 📊 性能报告

性能测试会生成详细的JSON报告，包含：

- 系统信息
- 响应时间统计
- 吞吐量指标
- 并发性能数据
- 内存使用情况
- 缓存性能指标
- LLM调用性能

报告文件命名格式：`memory_performance_report_[timestamp].json`

## 🚨 注意事项

1. **测试数据隔离**: 每次测试使用唯一的用户ID和项目ID
2. **资源清理**: 测试完成后会自动清理临时数据
3. **并发限制**: 避免同时运行多个性能测试
4. **网络依赖**: 某些测试需要稳定的网络连接
5. **API配额**: 注意LLM API的调用限制

## 🤝 贡献指南

如果您想为测试套件做出贡献：

1. 遵循现有的代码风格
2. 添加适当的文档和注释
3. 确保新测试的稳定性
4. 更新相关文档

## 📞 支持

如果在使用测试套件时遇到问题：

1. 检查本文档的常见问题部分
2. 查看测试日志输出
3. 验证环境配置
4. 联系开发团队

---

**最后更新**: 2024年12月
**版本**: 1.0.0