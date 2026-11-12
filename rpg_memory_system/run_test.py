#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统测试运行脚本

使用方法:
python run_test.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置LangSmith环境变量
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_PROJECT"] = "pr-sunny-improvement-17"

# 配置数据库连接
os.environ["DATABASE_URL"] = "mysql+aiomysql://aigame_user:aigame_strong_password_123@121.40.249.125:3306/aigame_db"

# 确保必要的环境变量存在
required_env_vars = [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL", 
    "OPENAI_MODEL",
    "DATABASE_URL",
    "REDIS_URL"
]

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
        print("请检查 .env 文件配置")
        return False
    
    print("✅ 环境配置检查通过")
    
    # 打印LangSmith配置
    print("\n📊 LangSmith配置:")
    print(f"   - 追踪: {os.environ.get('LANGSMITH_TRACING')}")
    print(f"   - 项目: {os.environ.get('LANGSMITH_PROJECT')}")
    print(f"   - 端点: {os.environ.get('LANGSMITH_ENDPOINT')}")
    print(f"   - API密钥: {'已配置' if os.environ.get('LANGSMITH_API_KEY') else '未配置'}")
    
    return True

async def run_tests():
    """运行测试"""
    try:
        # 导入测试模块
        from test_memory_features import MemoryFeatureTest
        
        print("\n🚀 启动记忆系统功能测试")
        print("="*60)
        
        # 创建测试实例
        test = MemoryFeatureTest()
        
        # 运行所有测试
        await test.run_all_tests()
        
        print("\n🎉 测试完成！")
        print("\n📋 检查清单:")
        print("1. ✅ 查看上方的后端日志输出")
        print("2. ✅ 检查LangSmith平台的监控数据")
        print("3. ✅ 验证定时器功能是否正常")
        print("4. ✅ 确认核心记忆修复是否生效")
        
        print("\n🔗 LangSmith链接:")
        print(f"   https://smith.langchain.com/projects/{os.environ.get('LANGSMITH_PROJECT')}")
        
    except ImportError as e:
        print(f"❌ 导入测试模块失败: {e}")
        print("请确保项目路径配置正确")
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        raise

def main():
    """主函数"""
    print("记忆系统功能测试")
    print("="*40)
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    # 运行测试
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
