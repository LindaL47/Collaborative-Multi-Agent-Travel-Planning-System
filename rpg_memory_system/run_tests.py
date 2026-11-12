#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统测试运行器

这个脚本提供了一个统一的入口来运行不同类型的记忆系统测试。
用户可以选择运行：
1. 快速检查测试
2. 综合功能测试
3. 性能基准测试
4. 所有测试

使用方法:
python run_tests.py [test_type]

参数:
- quick: 运行快速检查测试
- comprehensive: 运行综合功能测试
- performance: 运行性能基准测试
- all: 运行所有测试
- 无参数: 显示交互式菜单
"""

import asyncio
import sys
import os
import time
import logging
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestRunner:
    """测试运行器类"""
    
    def __init__(self):
        self.project_root = os.path.dirname(__file__)
        
    def show_banner(self):
        """显示横幅"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    RPG记忆系统测试套件                        ║
║                                                              ║
║  本测试套件包含多种测试类型，用于验证记忆系统的各项功能        ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def show_menu(self):
        """显示测试菜单"""
        menu = """
请选择要运行的测试类型:

1. 快速检查测试 (quick)
   - 验证基础连接和核心功能
   - 适合日常开发检查
   - 预计耗时: 1-2分钟

2. 综合功能测试 (comprehensive)
   - 全面测试所有功能模块
   - 包含错误处理和边界情况
   - 预计耗时: 10-15分钟

3. 性能基准测试 (performance)
   - 评估系统性能指标
   - 生成详细性能报告
   - 预计耗时: 15-20分钟

4. 运行所有测试 (all)
   - 依次运行上述所有测试
   - 生成完整测试报告
   - 预计耗时: 25-35分钟

5. 退出

请输入选项编号 (1-5) 或测试类型名称:
        """
        print(menu)
    
    async def run_quick_test(self):
        """运行快速检查测试"""
        logger.info("🚀 启动快速检查测试...")
        try:
            # 动态导入测试模块
            sys.path.insert(0, self.project_root)
            from test_quick_memory_check import QuickMemoryTest
            
            tester = QuickMemoryTest()
            success = await tester.run_quick_check()
            
            if success:
                logger.info("✅ 快速检查测试完成 - 系统状态良好")
                return True
            else:
                logger.error("❌ 快速检查测试发现问题")
                return False
                
        except Exception as e:
            logger.error(f"❌ 快速检查测试异常: {str(e)}")
            return False
    
    async def run_comprehensive_test(self):
        """运行综合功能测试"""
        logger.info("🔍 启动综合功能测试...")
        try:
            sys.path.insert(0, self.project_root)
            from test_comprehensive_memory_system import ComprehensiveMemorySystemTest
            
            tester = ComprehensiveMemorySystemTest()
            await tester.run_all_tests()
            
            # 检查测试结果
            passed = tester.test_results['passed']
            total = passed + tester.test_results['failed']
            success_rate = (passed / total * 100) if total > 0 else 0
            
            if success_rate >= 80:
                logger.info(f"✅ 综合功能测试完成 - 成功率: {success_rate:.1f}%")
                return True
            else:
                logger.warning(f"⚠️ 综合功能测试完成 - 成功率: {success_rate:.1f}% (低于80%)")
                return False
                
        except Exception as e:
            logger.error(f"❌ 综合功能测试异常: {str(e)}")
            return False
    
    async def run_performance_test(self):
        """运行性能基准测试"""
        logger.info("📊 启动性能基准测试...")
        try:
            sys.path.insert(0, self.project_root)
            from test_memory_performance import MemoryPerformanceTest
            
            tester = MemoryPerformanceTest()
            await tester.run_performance_tests()
            
            logger.info("✅ 性能基准测试完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 性能基准测试异常: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🎯 启动完整测试套件...")
        
        start_time = time.time()
        results = {
            'quick': False,
            'comprehensive': False,
            'performance': False
        }
        
        # 运行快速检查测试
        logger.info("\n" + "="*60)
        logger.info("第1阶段: 快速检查测试")
        logger.info("="*60)
        results['quick'] = await self.run_quick_test()
        
        # 如果快速测试失败，询问是否继续
        if not results['quick']:
            response = input("\n快速检查测试失败，是否继续运行其他测试? (y/N): ")
            if response.lower() != 'y':
                logger.info("测试已中止")
                return False
        
        # 运行综合功能测试
        logger.info("\n" + "="*60)
        logger.info("第2阶段: 综合功能测试")
        logger.info("="*60)
        results['comprehensive'] = await self.run_comprehensive_test()
        
        # 运行性能基准测试
        logger.info("\n" + "="*60)
        logger.info("第3阶段: 性能基准测试")
        logger.info("="*60)
        results['performance'] = await self.run_performance_test()
        
        # 生成总结报告
        total_time = time.time() - start_time
        self._print_final_summary(results, total_time)
        
        return all(results.values())
    
    def _print_final_summary(self, results: dict, total_time: float):
        """打印最终总结"""
        logger.info("\n" + "="*80)
        logger.info("记忆系统完整测试套件总结")
        logger.info("="*80)
        
        logger.info(f"总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
        logger.info("\n测试结果:")
        
        for test_name, success in results.items():
            status = "✅ 通过" if success else "❌ 失败"
            logger.info(f"  {test_name.capitalize()}: {status}")
        
        passed_count = sum(results.values())
        total_count = len(results)
        
        logger.info(f"\n整体结果: {passed_count}/{total_count} 测试通过")
        
        if passed_count == total_count:
            logger.info("🎉 所有测试通过！记忆系统状态优秀！")
        elif passed_count >= total_count * 0.67:
            logger.warning("⚠️ 大部分测试通过，但仍有问题需要关注")
        else:
            logger.error("🚨 多项测试失败，记忆系统存在严重问题！")
        
        logger.info("="*80)
    
    async def run_interactive_mode(self):
        """运行交互模式"""
        self.show_banner()
        
        while True:
            self.show_menu()
            choice = input("请选择: ").strip().lower()
            
            if choice in ['1', 'quick']:
                await self.run_quick_test()
            elif choice in ['2', 'comprehensive']:
                await self.run_comprehensive_test()
            elif choice in ['3', 'performance']:
                await self.run_performance_test()
            elif choice in ['4', 'all']:
                await self.run_all_tests()
            elif choice in ['5', 'exit', 'quit']:
                logger.info("👋 退出测试套件")
                break
            else:
                print("❌ 无效选择，请重新输入")
                continue
            
            # 询问是否继续
            if input("\n是否继续运行其他测试? (y/N): ").lower() != 'y':
                break
    
    async def run_by_argument(self, test_type: str):
        """根据命令行参数运行测试"""
        self.show_banner()
        
        if test_type == 'quick':
            return await self.run_quick_test()
        elif test_type == 'comprehensive':
            return await self.run_comprehensive_test()
        elif test_type == 'performance':
            return await self.run_performance_test()
        elif test_type == 'all':
            return await self.run_all_tests()
        else:
            logger.error(f"❌ 未知的测试类型: {test_type}")
            logger.info("可用的测试类型: quick, comprehensive, performance, all")
            return False

def show_usage():
    """显示使用说明"""
    usage = """
使用方法:
  python run_tests.py [test_type]

参数:
  quick         - 运行快速检查测试
  comprehensive - 运行综合功能测试
  performance   - 运行性能基准测试
  all          - 运行所有测试
  
  无参数        - 显示交互式菜单
  -h, --help   - 显示此帮助信息

示例:
  python run_tests.py quick
  python run_tests.py comprehensive
  python run_tests.py all
    """
    print(usage)

async def main():
    """主函数"""
    runner = TestRunner()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['-h', '--help', 'help']:
            show_usage()
            return
        
        # 运行指定的测试
        success = await runner.run_by_argument(arg)
        sys.exit(0 if success else 1)
    else:
        # 运行交互模式
        await runner.run_interactive_mode()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 用户中断，退出测试")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 测试运行器异常: {str(e)}")
        sys.exit(1)