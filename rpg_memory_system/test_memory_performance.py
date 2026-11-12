#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统性能基准测试

本测试文件专门用于评估记忆系统的性能指标，包括：
1. 响应时间测试
2. 吞吐量测试
3. 并发性能测试
4. 内存使用测试
5. 数据库性能测试
6. 缓存性能测试
7. LLM调用性能测试

测试结果将生成详细的性能报告。
"""

import asyncio
import os
import sys
import time
import logging
import json
import statistics
import psutil
from typing import Dict, Any, List
from datetime import datetime

# 添加项目路径
project_root = os.path.dirname(__file__)
api_path = os.path.join(project_root, 'src', 'server', 'api')
sys.path.insert(0, api_path)

# 配置环境变量
os.environ["DATABASE_URL"] = "mysql+aiomysql://aigame_user:aigame_strong_password_123@121.40.249.125:3306/aigame_db"
os.environ["LANGSMITH_TRACING"] = "false"  # 关闭追踪以获得更准确的性能数据

# 导入记忆系统组件
try:
    from src.server.api.memory_interface import (
        add_dialogue_to_memory,
        get_memory_context_for_chat,
        initialize_user_memory
    )
    from src.server.api.controllers.memory_manager import memory_manager
    from src.server.api.models.redis_client import redis_client
    from src.server.api.models.llm_client import llm_client
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MemoryPerformanceTest:
    """记忆系统性能测试类"""
    
    def __init__(self):
        self.test_user_id = f"perf_test_{int(time.time())}"
        self.test_project_id = f"perf_project_{int(time.time())}"
        self.performance_data = {
            'test_start_time': datetime.now().isoformat(),
            'system_info': self._get_system_info(),
            'test_results': {}
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'python_version': sys.version
        }
    
    async def run_performance_tests(self):
        """运行所有性能测试"""
        logger.info("🚀 开始记忆系统性能基准测试")
        logger.info(f"测试用户: {self.test_user_id}")
        
        # 初始化测试环境
        await self._setup_test_environment()
        
        # 性能测试列表
        tests = [
            ("响应时间测试", self.test_response_times),
            ("吞吐量测试", self.test_throughput),
            ("并发性能测试", self.test_concurrent_performance),
            ("内存使用测试", self.test_memory_usage),
            ("缓存性能测试", self.test_cache_performance),
            ("LLM调用性能测试", self.test_llm_performance)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n📊 开始 {test_name}...")
            try:
                start_time = time.time()
                result = await test_func()
                test_duration = time.time() - start_time
                
                self.performance_data['test_results'][test_name] = {
                    'duration': test_duration,
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"✅ {test_name} 完成 (耗时: {test_duration:.2f}s)")
                
            except Exception as e:
                logger.error(f"❌ {test_name} 失败: {str(e)}")
                self.performance_data['test_results'][test_name] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        # 生成性能报告
        await self._generate_performance_report()
    
    async def _setup_test_environment(self):
        """设置测试环境"""
        logger.info("🔧 设置测试环境...")
        
        # 初始化用户记忆
        await initialize_user_memory(self.test_user_id, self.test_project_id)
        
        # 预热系统 - 添加一些基础对话
        warmup_dialogues = [
            {"role": "user", "content": "性能测试预热消息1"},
            {"role": "assistant", "content": "收到，开始性能测试"},
            {"role": "user", "content": "性能测试预热消息2"},
            {"role": "assistant", "content": "系统已准备就绪"}
        ]
        
        for dialogue in warmup_dialogues:
            await add_dialogue_to_memory(
                self.test_user_id,
                self.test_project_id,
                dialogue['role'],
                dialogue['content']
            )
        
        logger.info("✅ 测试环境设置完成")
    
    async def test_response_times(self) -> Dict[str, Any]:
        """测试响应时间"""
        logger.info("  📏 测试各操作的响应时间...")
        
        response_times = {
            'add_dialogue': [],
            'get_context': [],
            'memory_processing': []
        }
        
        # 测试添加对话的响应时间
        for i in range(50):
            start_time = time.time()
            await add_dialogue_to_memory(
                self.test_user_id,
                self.test_project_id,
                "user" if i % 2 == 0 else "assistant",
                f"响应时间测试消息 {i}"
            )
            response_times['add_dialogue'].append(time.time() - start_time)
        
        # 测试获取上下文的响应时间
        for i in range(20):
            start_time = time.time()
            await get_memory_context_for_chat(
                self.test_user_id,
                self.test_project_id,
                f"响应时间查询 {i}"
            )
            response_times['get_context'].append(time.time() - start_time)
        
        # 测试记忆处理的响应时间
        for i in range(5):
            start_time = time.time()
            await memory_manager.process_memory(self.test_user_id, self.test_project_id)
            response_times['memory_processing'].append(time.time() - start_time)
        
        # 计算统计数据
        stats = {}
        for operation, times in response_times.items():
            if times:
                stats[operation] = {
                    'avg': statistics.mean(times),
                    'min': min(times),
                    'max': max(times),
                    'median': statistics.median(times),
                    'p95': sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
                    'count': len(times)
                }
                
                logger.info(f"    {operation}: 平均 {stats[operation]['avg']:.3f}s, "
                          f"中位数 {stats[operation]['median']:.3f}s, "
                          f"P95 {stats[operation]['p95']:.3f}s")
        
        return stats
    
    async def test_throughput(self) -> Dict[str, Any]:
        """测试吞吐量"""
        logger.info("  🚄 测试系统吞吐量...")
        
        # 测试1分钟内能处理多少对话
        start_time = time.time()
        test_duration = 60  # 60秒
        dialogue_count = 0
        
        while time.time() - start_time < test_duration:
            try:
                await add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    "user" if dialogue_count % 2 == 0 else "assistant",
                    f"吞吐量测试消息 {dialogue_count}"
                )
                dialogue_count += 1
            except Exception as e:
                logger.error(f"吞吐量测试中出现错误: {str(e)}")
                break
        
        actual_duration = time.time() - start_time
        throughput = dialogue_count / actual_duration
        
        logger.info(f"    吞吐量: {throughput:.2f} 对话/秒 ({dialogue_count} 对话 / {actual_duration:.1f}s)")
        
        return {
            'dialogues_per_second': throughput,
            'total_dialogues': dialogue_count,
            'test_duration': actual_duration
        }
    
    async def test_concurrent_performance(self) -> Dict[str, Any]:
        """测试并发性能"""
        logger.info("  🔀 测试并发性能...")
        
        concurrent_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrent_levels:
            logger.info(f"    测试并发级别: {concurrency}")
            
            start_time = time.time()
            
            # 创建并发任务
            tasks = []
            for i in range(concurrency):
                task = add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    "user" if i % 2 == 0 else "assistant",
                    f"并发测试消息 {i} (级别{concurrency})"
                )
                tasks.append(task)
            
            # 执行并发任务
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = time.time() - start_time
            success_count = sum(1 for r in task_results if isinstance(r, dict) and r.get('status') == 'success')
            
            results[f'concurrency_{concurrency}'] = {
                'duration': duration,
                'success_rate': success_count / concurrency,
                'throughput': concurrency / duration,
                'success_count': success_count,
                'total_tasks': concurrency
            }
            
            logger.info(f"      耗时: {duration:.2f}s, 成功率: {success_count/concurrency:.1%}, "
                      f"吞吐量: {concurrency/duration:.2f} 任务/秒")
        
        return results
    
    async def test_memory_usage(self) -> Dict[str, Any]:
        """测试内存使用"""
        logger.info("  💾 测试内存使用情况...")
        
        # 获取初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        memory_snapshots = []
        
        # 添加大量对话并监控内存使用
        for batch in range(10):
            # 每批添加100条对话
            for i in range(100):
                await add_dialogue_to_memory(
                    self.test_user_id,
                    self.test_project_id,
                    "user" if i % 2 == 0 else "assistant",
                    f"内存测试消息 批次{batch} 消息{i}"
                )
            
            # 记录内存快照
            current_memory = process.memory_info().rss
            memory_snapshots.append({
                'batch': batch,
                'memory_mb': current_memory / 1024 / 1024,
                'memory_increase_mb': (current_memory - initial_memory) / 1024 / 1024
            })
            
            logger.info(f"    批次 {batch}: 内存使用 {current_memory/1024/1024:.1f}MB "
                      f"(增加 {(current_memory-initial_memory)/1024/1024:.1f}MB)")
        
        final_memory = process.memory_info().rss
        total_increase = (final_memory - initial_memory) / 1024 / 1024
        
        return {
            'initial_memory_mb': initial_memory / 1024 / 1024,
            'final_memory_mb': final_memory / 1024 / 1024,
            'total_increase_mb': total_increase,
            'memory_snapshots': memory_snapshots
        }
    
    async def test_cache_performance(self) -> Dict[str, Any]:
        """测试缓存性能"""
        logger.info("  🗄️ 测试缓存性能...")
        
        cache_operations = {
            'set_operations': [],
            'get_operations': [],
            'hit_rate': 0
        }
        
        # 测试缓存写入性能
        for i in range(100):
            test_key = f"perf_test_key_{i}"
            test_data = {"test_data": f"value_{i}", "timestamp": time.time()}
            
            start_time = time.time()
            await redis_client.set_cache(test_key, test_data, expire_time=300)
            cache_operations['set_operations'].append(time.time() - start_time)
        
        # 测试缓存读取性能和命中率
        hit_count = 0
        for i in range(100):
            test_key = f"perf_test_key_{i}"
            
            start_time = time.time()
            cached_data = await redis_client.get_cache(test_key)
            cache_operations['get_operations'].append(time.time() - start_time)
            
            if cached_data is not None:
                hit_count += 1
        
        cache_operations['hit_rate'] = hit_count / 100
        
        # 计算统计数据
        set_avg = statistics.mean(cache_operations['set_operations'])
        get_avg = statistics.mean(cache_operations['get_operations'])
        
        logger.info(f"    缓存写入平均时间: {set_avg:.4f}s")
        logger.info(f"    缓存读取平均时间: {get_avg:.4f}s")
        logger.info(f"    缓存命中率: {cache_operations['hit_rate']:.1%}")
        
        return {
            'set_avg_time': set_avg,
            'get_avg_time': get_avg,
            'hit_rate': cache_operations['hit_rate'],
            'operations_tested': 100
        }
    
    async def test_llm_performance(self) -> Dict[str, Any]:
        """测试LLM调用性能"""
        logger.info("  🤖 测试LLM调用性能...")
        
        llm_operations = {
            'embedding_generation': [],
            'user_profile_extraction': [],
            'event_extraction': [],
            'reflection_generation': []
        }
        
        test_text = "这是一个性能测试文本，用于评估LLM调用的响应时间。"
        test_dialogues = [
            {"role": "user", "content": "我是一个测试用户"},
            {"role": "assistant", "content": "你好，很高兴见到你"}
        ]
        
        # 测试嵌入向量生成性能
        for i in range(10):
            start_time = time.time()
            try:
                await llm_client.generate_embedding(f"{test_text} {i}")
                llm_operations['embedding_generation'].append(time.time() - start_time)
            except Exception as e:
                logger.error(f"嵌入向量生成失败: {str(e)}")
        
        # 测试用户画像提取性能
        for i in range(5):
            start_time = time.time()
            try:
                await llm_client.extract_user_profile(test_dialogues)
                llm_operations['user_profile_extraction'].append(time.time() - start_time)
            except Exception as e:
                logger.error(f"用户画像提取失败: {str(e)}")
        
        # 测试事件提取性能
        for i in range(5):
            start_time = time.time()
            try:
                await llm_client.extract_events(test_dialogues)
                llm_operations['event_extraction'].append(time.time() - start_time)
            except Exception as e:
                logger.error(f"事件提取失败: {str(e)}")
        
        # 测试反思生成性能
        for i in range(5):
            start_time = time.time()
            try:
                await llm_client.generate_reflection(test_dialogues)
                llm_operations['reflection_generation'].append(time.time() - start_time)
            except Exception as e:
                logger.error(f"反思生成失败: {str(e)}")
        
        # 计算统计数据
        stats = {}
        for operation, times in llm_operations.items():
            if times:
                avg_time = statistics.mean(times)
                stats[operation] = {
                    'avg_time': avg_time,
                    'min_time': min(times),
                    'max_time': max(times),
                    'count': len(times)
                }
                logger.info(f"    {operation}: 平均 {avg_time:.2f}s")
        
        return stats
    
    async def _generate_performance_report(self):
        """生成性能报告"""
        logger.info("\n📋 生成性能报告...")
        
        self.performance_data['test_end_time'] = datetime.now().isoformat()
        
        # 保存详细报告到文件
        report_filename = f"memory_performance_report_{int(time.time())}.json"
        report_path = os.path.join(project_root, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.performance_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 详细性能报告已保存到: {report_path}")
        
        # 打印摘要报告
        self._print_performance_summary()
    
    def _print_performance_summary(self):
        """打印性能摘要"""
        logger.info("\n" + "="*80)
        logger.info("记忆系统性能测试摘要")
        logger.info("="*80)
        
        test_results = self.performance_data['test_results']
        
        # 响应时间摘要
        if '响应时间测试' in test_results:
            response_data = test_results['响应时间测试']['result']
            logger.info("\n📏 响应时间性能:")
            for operation, stats in response_data.items():
                logger.info(f"  {operation}: 平均 {stats['avg']:.3f}s, P95 {stats['p95']:.3f}s")
        
        # 吞吐量摘要
        if '吞吐量测试' in test_results:
            throughput_data = test_results['吞吐量测试']['result']
            logger.info(f"\n🚄 吞吐量性能: {throughput_data['dialogues_per_second']:.2f} 对话/秒")
        
        # 并发性能摘要
        if '并发性能测试' in test_results:
            concurrent_data = test_results['并发性能测试']['result']
            logger.info("\n🔀 并发性能:")
            for level, stats in concurrent_data.items():
                logger.info(f"  {level}: 成功率 {stats['success_rate']:.1%}, "
                          f"吞吐量 {stats['throughput']:.2f} 任务/秒")
        
        # 内存使用摘要
        if '内存使用测试' in test_results:
            memory_data = test_results['内存使用测试']['result']
            logger.info(f"\n💾 内存使用: 增加 {memory_data['total_increase_mb']:.1f}MB")
        
        # 缓存性能摘要
        if '缓存性能测试' in test_results:
            cache_data = test_results['缓存性能测试']['result']
            logger.info(f"\n🗄️ 缓存性能: 命中率 {cache_data['hit_rate']:.1%}, "
                      f"读取 {cache_data['get_avg_time']:.4f}s, 写入 {cache_data['set_avg_time']:.4f}s")
        
        logger.info("\n" + "="*80)
        logger.info("🎯 性能测试完成！")

async def main():
    """主函数"""
    tester = MemoryPerformanceTest()
    await tester.run_performance_tests()

if __name__ == "__main__":
    asyncio.run(main())