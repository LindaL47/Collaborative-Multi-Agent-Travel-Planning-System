#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整提示词打印功能
这个脚本用于快速测试新添加的print_complete_prompt方法
"""

import asyncio
import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from test_memory_interface import MemoryInterfaceTest
    print("[OK] 成功导入测试类")
except ImportError as e:
    print(f"[ERROR] 导入测试类失败: {e}")
    sys.exit(1)

async def test_prompt_printing():
    """测试提示词打印功能"""
    print("开始测试完整提示词打印功能...")
    
    # 创建测试实例
    test_instance = MemoryInterfaceTest()
    
    try:
        # 手动初始化Redis连接
        await test_instance._init_redis()
        print("[OK] Redis连接初始化成功")
        
        # 运行记忆上下文获取测试（这会触发完整提示词打印）
        print("\n" + "="*60)
        print("开始测试记忆上下文获取和提示词打印...")
        print("="*60)
        
        success = await test_instance.test_get_memory_context()
        
        if success:
            print("\n✅ 提示词打印功能测试成功！")
        else:
            print("\n❌ 提示词打印功能测试失败！")
            
    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("完整提示词打印功能测试")
    print("="*50)
    
    try:
        asyncio.run(test_prompt_printing())
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()