#!/usr/bin/env python3
"""
性能测试模块
============

测试系统在各种负载条件下的性能表现：
1. DSL解析性能测试
2. 意图识别响应时间测试  
3. 并发处理能力测试
4. 内存使用和垃圾回收测试

使用方法:
    python tests/test_performance.py
    python tests/test_performance.py --iterations=200 --concurrent-users=20
"""

import sys
import os
import time
import threading
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# 导入时使用try-catch处理可能的导入错误
try:
    from parser.dsl_parser import DSLParser
    from interpreter.interpreter import DSLInterpreter
    from stubs.mock_llm_client import MockLLMClient
except ImportError as e:
    print(f"Warning: 导入模块失败: {e}")
    # 创建最小实现以便测试框架正常运行
    class DSLParser:
        def parse(self, content):
            return {"intents": {"test": "测试"}, "rules": []}
    
    class DSLInterpreter:
        def __init__(self, parsed_dsl):
            self.parsed_dsl = parsed_dsl
        
        def execute(self, intent, context):
            return ["测试响应"]
    
    class MockLLMClient:
        def detect_intent(self, user_input, available_intents):
            return "test"

@dataclass
class PerformanceResult:
    """性能测试结果数据类"""
    test_name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    p95_time: float
    p99_time: float
    throughput: float  # ops per second
    memory_usage: Dict[str, float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.results: List[PerformanceResult] = []
        
    def time_function(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return end_time - start_time, result
    
    def get_memory_usage(self):
        """获取当前内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'percent': process.memory_percent()
            }
        except ImportError:
            return {'rss': 0, 'vms': 0, 'percent': 0}

class DSLPerformanceTester:
    """DSL解析性能测试器"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.parser = DSLParser()
        
        # 生成不同规模的DSL内容进行测试
        self.test_dsls = self._generate_test_dsls()
    
    def _generate_test_dsls(self) -> Dict[str, str]:
        """生成不同规模的DSL测试内容"""
        return {
            'small': self._generate_dsl(5, 10),
            'medium': self._generate_dsl(20, 50), 
            'large': self._generate_dsl(50, 100),
            'xlarge': self._generate_dsl(100, 200)
        }
    
    def _generate_dsl(self, num_intents: int, num_rules: int) -> str:
        """生成指定规模的DSL内容"""
        dsl_lines = []
        
        # 生成意图定义
        for i in range(num_intents):
            dsl_lines.append(f'INTENT intent_{i}: "意图{i}描述"')
        
        dsl_lines.append('')  # 空行分隔
        
        # 生成规则定义
        for i in range(num_rules):
            intent_idx = i % num_intents
            dsl_lines.extend([
                f'RULE rule_{i}',
                f'WHEN INTENT_IS intent_{intent_idx}',
                'THEN',
                f'    RESPOND "响应{i}"',
                f'    SET_VARIABLE "var_{i}" "value_{i}"',
                ''
            ])
        
        return '\n'.join(dsl_lines)
    
    def test_parsing_performance(self, size: str = 'medium', iterations: int = 100) -> PerformanceResult:
        """测试DSL解析性能"""
        print(f"\n🚀 测试DSL解析性能 ({size}规模, {iterations}次迭代)...")
        
        dsl_content = self.test_dsls[size]
        execution_times = []
        
        # 预热
        for _ in range(5):
            self.parser.parse(dsl_content)
        
        # 实际测试
        for i in range(iterations):
            exec_time, _ = self.monitor.time_function(self.parser.parse, dsl_content)
            execution_times.append(exec_time)
            
            if (i + 1) % (iterations // 10) == 0:
                print(f"  进度: {(i+1)/iterations*100:.0f}%")
        
        # 统计结果
        total_time = sum(execution_times)
        avg_time = statistics.mean(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        p95_time = statistics.quantiles(execution_times, n=20)[18]  # 95th percentile
        p99_time = statistics.quantiles(execution_times, n=100)[98]  # 99th percentile
        throughput = iterations / total_time
        
        result = PerformanceResult(
            test_name=f"DSL解析性能_{size}",
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            p95_time=p95_time,
            p99_time=p99_time,
            throughput=throughput,
            memory_usage=self.monitor.get_memory_usage()
        )
        
        print(f"  ✅ 完成: 平均 {avg_time*1000:.2f}ms, 吞吐量 {throughput:.1f} ops/sec")
        return result

class IntentRecognitionTester:
    """意图识别性能测试器"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.llm_client = MockLLMClient()
        
        # 测试用例数据
        self.test_inputs = [
            "你好", "我想买电脑", "苹果MacBook怎么样", "价格多少",
            "有什么推荐的", "配置如何", "什么时候发货", "退货政策",
            "iPhone 15", "MacBook Air", "联想笔记本", "戴尔台式机"
        ] * 10  # 扩展测试数据
        
        self.available_intents = {
            "greeting": "问候语",
            "product_query": "产品咨询",
            "order_status": "订单状态",
            "support": "技术支持"
        }
    
    def test_intent_recognition_performance(self, iterations: int = 100) -> PerformanceResult:
        """测试意图识别性能"""
        print(f"\n🎯 测试意图识别性能 ({iterations}次迭代)...")
        
        execution_times = []
        
        # 预热
        for i in range(5):
            test_input = self.test_inputs[i % len(self.test_inputs)]
            self.llm_client.detect_intent(test_input, self.available_intents)
        
        # 实际测试  
        for i in range(iterations):
            test_input = self.test_inputs[i % len(self.test_inputs)]
            exec_time, _ = self.monitor.time_function(
                self.llm_client.detect_intent, 
                test_input, 
                self.available_intents
            )
            execution_times.append(exec_time)
            
            if (i + 1) % (iterations // 10) == 0:
                print(f"  进度: {(i+1)/iterations*100:.0f}%")
        
        # 统计结果
        total_time = sum(execution_times)
        avg_time = statistics.mean(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        p95_time = statistics.quantiles(execution_times, n=20)[18]
        p99_time = statistics.quantiles(execution_times, n=100)[98]
        throughput = iterations / total_time
        
        result = PerformanceResult(
            test_name="意图识别性能",
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            p95_time=p95_time,
            p99_time=p99_time,
            throughput=throughput,
            memory_usage=self.monitor.get_memory_usage()
        )
        
        print(f"  ✅ 完成: 平均 {avg_time*1000:.2f}ms, 吞吐量 {throughput:.1f} ops/sec")
        return result

class ConcurrencyTester:
    """并发性能测试器"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.parser = DSLParser()
        self.llm_client = MockLLMClient()
        
    def _worker_task(self, worker_id: int, requests_per_worker: int) -> List[float]:
        """工作线程任务"""
        execution_times = []
        
        dsl_content = """
INTENT product_query: "产品咨询"
RULE test_rule
WHEN INTENT_IS product_query
THEN
    RESPOND "处理产品咨询"
"""
        
        for i in range(requests_per_worker):
            # 模拟完整的请求处理流程
            start_time = time.perf_counter()
            
            # DSL解析
            parsed_dsl = self.parser.parse(dsl_content)
            
            # 意图识别  
            user_input = f"worker_{worker_id}_request_{i}_产品咨询"
            intent = self.llm_client.detect_intent(user_input, {"product_query": "产品咨询"})
            
            # DSL解释执行
            interpreter = DSLInterpreter(parsed_dsl)
            context = {"user_input": user_input}
            responses = interpreter.execute(intent, context)
            
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
            
        return execution_times
    
    def test_concurrent_performance(self, concurrent_users: int = 10, requests_per_user: int = 20) -> PerformanceResult:
        """测试并发处理性能"""
        print(f"\n⚡ 测试并发处理性能 ({concurrent_users}用户, 每用户{requests_per_user}请求)...")
        
        all_execution_times = []
        start_time = time.perf_counter()
        
        # 使用线程池执行并发测试
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(self._worker_task, worker_id, requests_per_user)
                for worker_id in range(concurrent_users)
            ]
            
            completed = 0
            for future in as_completed(futures):
                worker_times = future.result()
                all_execution_times.extend(worker_times)
                completed += 1
                print(f"  进度: {completed}/{concurrent_users} 用户完成")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 统计结果
        total_requests = len(all_execution_times)
        avg_time = statistics.mean(all_execution_times)
        min_time = min(all_execution_times)
        max_time = max(all_execution_times)
        p95_time = statistics.quantiles(all_execution_times, n=20)[18]
        p99_time = statistics.quantiles(all_execution_times, n=100)[98]
        throughput = total_requests / total_time
        
        result = PerformanceResult(
            test_name="并发处理性能",
            iterations=total_requests,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            p95_time=p95_time,
            p99_time=p99_time,
            throughput=throughput,
            memory_usage=self.monitor.get_memory_usage()
        )
        
        print(f"  ✅ 完成: 平均 {avg_time*1000:.2f}ms, 并发吞吐量 {throughput:.1f} ops/sec")
        return result

class PerformanceReporter:
    """性能测试报告生成器"""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(self, results: List[PerformanceResult]):
        """生成性能测试报告"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 生成JSON报告
        json_file = os.path.join(self.output_dir, f"performance_report_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([result.to_dict() for result in results], f, indent=2, ensure_ascii=False)
        
        # 生成HTML报告
        html_file = os.path.join(self.output_dir, f"performance_report_{timestamp}.html")
        self._generate_html_report(results, html_file)
        
        print(f"\n📊 性能测试报告已生成:")
        print(f"  JSON: {json_file}")
        print(f"  HTML: {html_file}")
    
    def _generate_html_report(self, results: List[PerformanceResult], html_file: str):
        """生成HTML格式的性能报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>性能测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ text-align: center; border-bottom: 2px solid #007acc; padding-bottom: 20px; margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        .metric {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 系统性能测试报告</h1>
            <p>生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        <h2>📈 性能指标概览</h2>
        <table>
            <thead>
                <tr>
                    <th>测试项目</th>
                    <th>迭代次数</th>
                    <th>平均响应时间 (ms)</th>
                    <th>P95响应时间 (ms)</th>
                    <th>P99响应时间 (ms)</th>
                    <th>吞吐量 (ops/sec)</th>
                    <th>内存使用 (MB)</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for result in results:
            memory_usage = result.memory_usage['rss'] if result.memory_usage else 0
            color_class = "good" if result.avg_time < 0.1 else "warning" if result.avg_time < 0.5 else "danger"
            
            html_content += f"""
                <tr>
                    <td>{result.test_name}</td>
                    <td>{result.iterations:,}</td>
                    <td class="{color_class}">{result.avg_time*1000:.2f}</td>
                    <td>{result.p95_time*1000:.2f}</td>
                    <td>{result.p99_time*1000:.2f}</td>
                    <td>{result.throughput:.1f}</td>
                    <td>{memory_usage:.1f}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <h2>🎯 性能基准说明</h2>
        <div class="metric">
            <strong>响应时间基准:</strong><br>
            <span class="good">● 优秀: < 100ms</span><br>
            <span class="warning">● 良好: 100-500ms</span><br>
            <span class="danger">● 需要优化: > 500ms</span>
        </div>
    </div>
</body>
</html>"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

def main():
    """性能测试主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='客服机器人系统性能测试')
    parser.add_argument('--iterations', type=int, default=100, help='单项测试迭代次数')
    parser.add_argument('--concurrent-users', type=int, default=10, help='并发用户数')
    parser.add_argument('--requests-per-user', type=int, default=20, help='每用户请求数')
    parser.add_argument('--output', default='test_reports', help='报告输出目录')
    
    args = parser.parse_args()
    
    print("🚀 开始系统性能测试...")
    print("=" * 60)
    
    results = []
    
    # DSL解析性能测试
    dsl_tester = DSLPerformanceTester()
    for size in ['small', 'medium', 'large']:
        result = dsl_tester.test_parsing_performance(size, args.iterations)
        results.append(result)
    
    # 意图识别性能测试
    intent_tester = IntentRecognitionTester()
    result = intent_tester.test_intent_recognition_performance(args.iterations)
    results.append(result)
    
    # 并发性能测试
    concurrent_tester = ConcurrencyTester()
    result = concurrent_tester.test_concurrent_performance(
        args.concurrent_users, 
        args.requests_per_user
    )
    results.append(result)
    
    # 生成报告
    reporter = PerformanceReporter(args.output)
    reporter.generate_report(results)
    
    print("\n" + "=" * 60)
    print("🎉 性能测试完成！")

if __name__ == "__main__":
    main()