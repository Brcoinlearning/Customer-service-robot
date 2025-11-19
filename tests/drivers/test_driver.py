"""
测试驱动程序 (Test Driver)

目的：
1. 自动化执行测试用例
2. 收集和汇总测试结果
3. 生成详细的测试报告
4. 支持批量测试和持续集成

功能：
- 测试套件管理和执行
- 测试结果统计和分析
- HTML/JSON格式报告生成
- 测试覆盖率统计
- 性能指标收集
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    test_category: str
    status: str  # "PASS", "FAIL", "ERROR", "SKIP"
    duration: float
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if self.details is None:
            self.details = {}

@dataclass
class TestSuite:
    """测试套件数据类"""
    name: str
    description: str
    tests: List[Callable] = None
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    
    def __post_init__(self):
        if self.tests is None:
            self.tests = []

class TestDriver:
    """
    测试驱动程序
    
    负责执行测试套件、收集结果、生成报告
    """
    
    def __init__(self, output_dir: str = None):
        """
        初始化测试驱动程序
        
        Args:
            output_dir: 测试报告输出目录
        """
        self.output_dir = Path(output_dir) if output_dir else Path("test_reports")
        self.output_dir.mkdir(exist_ok=True)
        
        self.test_suites: List[TestSuite] = []
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # 统计信息
        self.stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'duration': 0.0
        }
    
    def register_test_suite(self, suite: TestSuite):
        """注册测试套件"""
        self.test_suites.append(suite)
    
    def run_all_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """
        运行所有测试套件
        
        Args:
            verbose: 是否显示详细输出
        
        Returns:
            测试执行总结
        """
        print("🚀 开始执行测试驱动程序")
        print(f"📁 报告输出目录: {self.output_dir.absolute()}")
        print("=" * 60)
        
        self.start_time = datetime.now()
        
        for suite in self.test_suites:
            self._run_test_suite(suite, verbose)
        
        self.end_time = datetime.now()
        self._calculate_stats()
        
        # 生成报告
        report_data = self._generate_report_data()
        self._save_json_report(report_data)
        self._save_html_report(report_data)
        
        # 打印总结
        self._print_summary()
        
        return report_data
    
    def _run_test_suite(self, suite: TestSuite, verbose: bool):
        """运行单个测试套件"""
        print(f"\n📦 测试套件: {suite.name}")
        print(f"📝 描述: {suite.description}")
        print("-" * 40)
        
        # 执行setup
        if suite.setup:
            try:
                suite.setup()
                if verbose:
                    print("✅ 测试套件初始化完成")
            except Exception as e:
                print(f"❌ 测试套件初始化失败: {e}")
                return
        
        # 执行测试
        for test_func in suite.tests:
            self._run_single_test(test_func, suite.name, verbose)
        
        # 执行teardown
        if suite.teardown:
            try:
                suite.teardown()
                if verbose:
                    print("✅ 测试套件清理完成")
            except Exception as e:
                print(f"⚠️ 测试套件清理失败: {e}")
    
    def _run_single_test(self, test_func: Callable, suite_name: str, verbose: bool):
        """运行单个测试"""
        test_name = test_func.__name__
        
        start_time = time.time()
        result = TestResult(
            test_name=test_name,
            test_category=suite_name,
            status="UNKNOWN",
            duration=0.0
        )
        
        try:
            if verbose:
                print(f"🧪 运行测试: {test_name}")
            
            # 执行测试函数
            test_result = test_func()
            
            # 处理测试结果
            if test_result is None or test_result is True:
                result.status = "PASS"
                result.message = "测试通过"
                if verbose:
                    print(f"  ✅ {test_name} - 通过")
            elif test_result is False:
                result.status = "FAIL"
                result.message = "测试失败"
                if verbose:
                    print(f"  ❌ {test_name} - 失败")
            else:
                result.status = "PASS"
                result.message = str(test_result)
                if verbose:
                    print(f"  ✅ {test_name} - 通过: {result.message}")
        
        except AssertionError as e:
            result.status = "FAIL"
            result.message = f"断言失败: {str(e)}"
            result.details["traceback"] = traceback.format_exc()
            if verbose:
                print(f"  ❌ {test_name} - 断言失败: {str(e)}")
        
        except Exception as e:
            result.status = "ERROR"
            result.message = f"执行错误: {str(e)}"
            result.details["traceback"] = traceback.format_exc()
            if verbose:
                print(f"  💥 {test_name} - 执行错误: {str(e)}")
        
        finally:
            result.duration = time.time() - start_time
            self.results.append(result)
    
    def _calculate_stats(self):
        """计算统计信息"""
        self.stats['total'] = len(self.results)
        
        for result in self.results:
            if result.status == "PASS":
                self.stats['passed'] += 1
            elif result.status == "FAIL":
                self.stats['failed'] += 1
            elif result.status == "ERROR":
                self.stats['errors'] += 1
            elif result.status == "SKIP":
                self.stats['skipped'] += 1
        
        if self.start_time and self.end_time:
            self.stats['duration'] = (self.end_time - self.start_time).total_seconds()
    
    def _generate_report_data(self) -> Dict[str, Any]:
        """生成报告数据"""
        return {
            'summary': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration': self.stats['duration'],
                'statistics': self.stats.copy()
            },
            'test_suites': [
                {
                    'name': suite.name,
                    'description': suite.description,
                    'test_count': len(suite.tests)
                }
                for suite in self.test_suites
            ],
            'test_results': [asdict(result) for result in self.results],
            'failed_tests': [
                asdict(result) for result in self.results 
                if result.status in ['FAIL', 'ERROR']
            ]
        }
    
    def _save_json_report(self, report_data: Dict[str, Any]):
        """保存JSON格式报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"test_report_{timestamp}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"📄 JSON报告已保存: {json_file}")
    
    def _save_html_report(self, report_data: Dict[str, Any]):
        """保存HTML格式报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.output_dir / f"test_report_{timestamp}.html"
        
        html_content = self._generate_html_report(report_data)
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🌐 HTML报告已保存: {html_file}")
    
    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """生成HTML报告内容"""
        stats = report_data['summary']['statistics']
        pass_rate = (stats['passed'] / max(stats['total'], 1)) * 100
        
        # 简化的HTML模板
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - 客服机器人系统</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ text-align: center; border-bottom: 2px solid #007acc; padding-bottom: 20px; margin-bottom: 30px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-card {{ background: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; min-width: 120px; }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
        .error {{ color: #fd7e14; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ddd; }}
        .test-result.PASS {{ border-left-color: #28a745; }}
        .test-result.FAIL {{ border-left-color: #dc3545; }}
        .test-result.ERROR {{ border-left-color: #fd7e14; }}
        .progress-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: #28a745; transition: width 0.3s; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 客服机器人系统测试报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>总计</h3>
                <div style="font-size: 2em; font-weight: bold;">{stats['total']}</div>
            </div>
            <div class="stat-card pass">
                <h3>通过</h3>
                <div style="font-size: 2em; font-weight: bold;">{stats['passed']}</div>
            </div>
            <div class="stat-card fail">
                <h3>失败</h3>
                <div style="font-size: 2em; font-weight: bold;">{stats['failed']}</div>
            </div>
            <div class="stat-card error">
                <h3>错误</h3>
                <div style="font-size: 2em; font-weight: bold;">{stats['errors']}</div>
            </div>
        </div>
        
        <div style="margin: 20px 0;">
            <h3>通过率: {pass_rate:.1f}%</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {pass_rate}%;"></div>
            </div>
        </div>
        
        <h2>📊 测试套件</h2>
        <ul>
"""
        
        for suite in report_data['test_suites']:
            html += f"<li><strong>{suite['name']}</strong>: {suite['description']} ({suite['test_count']} 个测试)</li>"
        
        html += """
        </ul>
        
        <h2>🧪 测试结果详情</h2>
"""
        
        for result in report_data['test_results']:
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}.get(result['status'], "❓")
            html += f"""
        <div class="test-result {result['status']}">
            <h4>{status_icon} {result['test_name']} ({result['test_category']})</h4>
            <p><strong>状态:</strong> {result['status']}</p>
            <p><strong>耗时:</strong> {result['duration']:.3f}秒</p>
            <p><strong>消息:</strong> {result['message']}</p>
"""
            if result.get('details', {}).get('traceback'):
                html += f"<pre>{result['details']['traceback']}</pre>"
            
            html += "</div>"
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def _print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("📊 测试执行总结")
        print("=" * 60)
        print(f"总测试数: {self.stats['total']}")
        print(f"✅ 通过: {self.stats['passed']}")
        print(f"❌ 失败: {self.stats['failed']}")
        print(f"💥 错误: {self.stats['errors']}")
        print(f"⏭️ 跳过: {self.stats['skipped']}")
        
        if self.stats['total'] > 0:
            pass_rate = (self.stats['passed'] / self.stats['total']) * 100
            print(f"📈 通过率: {pass_rate:.1f}%")
        
        print(f"⏱️ 总耗时: {self.stats['duration']:.2f}秒")
        
        # 显示失败的测试
        failed_tests = [r for r in self.results if r.status in ['FAIL', 'ERROR']]
        if failed_tests:
            print(f"\n❌ 失败的测试 ({len(failed_tests)}个):")
            for result in failed_tests:
                print(f"  - {result.test_category}.{result.test_name}: {result.message}")


# 便捷函数
def create_test_driver(output_dir: str = None) -> TestDriver:
    """创建测试驱动程序实例"""
    return TestDriver(output_dir)

def run_test_function(func: Callable, name: str = None) -> TestResult:
    """运行单个测试函数并返回结果"""
    driver = TestDriver()
    test_name = name or func.__name__
    
    start_time = time.time()
    result = TestResult(
        test_name=test_name,
        test_category="standalone",
        status="UNKNOWN",
        duration=0.0
    )
    
    try:
        test_result = func()
        if test_result is None or test_result is True:
            result.status = "PASS"
        else:
            result.status = "FAIL"
            result.message = str(test_result)
    except Exception as e:
        result.status = "ERROR"
        result.message = str(e)
        result.details["traceback"] = traceback.format_exc()
    finally:
        result.duration = time.time() - start_time
    
    return result