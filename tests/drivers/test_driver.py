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

# 尝试导入coverage模块
try:
    import coverage
    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False

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
    
    def __init__(self, output_dir: str = None, enable_coverage: bool = True):
        """
        初始化测试驱动程序
        
        Args:
            output_dir: 测试报告输出目录
            enable_coverage: 是否启用代码覆盖率统计
        """
        self.output_dir = Path(output_dir) if output_dir else Path("test_reports")
        self.output_dir.mkdir(exist_ok=True)
        
        self.test_suites: List[TestSuite] = []
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # 覆盖率相关
        self.enable_coverage = enable_coverage and COVERAGE_AVAILABLE
        self.coverage_instance = None
        self.coverage_data = {}
        
        # 统计信息
        self.stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'duration': 0.0,
            'coverage': {}
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
        if self.enable_coverage:
            print("📊 代码覆盖率统计已启用")
        print("=" * 60)
        
        # 启动覆盖率收集
        if self.enable_coverage:
            self._start_coverage()
        
        self.start_time = datetime.now()
        
        for suite in self.test_suites:
            self._run_test_suite(suite, verbose)
        
        self.end_time = datetime.now()
        
        # 停止覆盖率收集
        if self.enable_coverage:
            self._stop_coverage()
        
        self._calculate_stats()
        
        # 生成报告
        report_data = self._generate_report_data()
        self._save_json_report(report_data)
        self._save_html_report(report_data)
        
        # 生成覆盖率报告
        if self.enable_coverage:
            self._generate_coverage_report()
        
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
    
    def _start_coverage(self):
        """启动代码覆盖率收集"""
        if not COVERAGE_AVAILABLE:
            return
        
        try:
            # 配置覆盖率收集
            self.coverage_instance = coverage.Coverage(
                source=['src'],  # 只统计src目录下的代码
                omit=[
                    '*/tests/*',
                    '*/test_*',
                    '*/__pycache__/*',
                    '*/.*'
                ]
            )
            self.coverage_instance.start()
            print("✅ 代码覆盖率收集已启动")
        except Exception as e:
            print(f"⚠️ 覆盖率收集启动失败: {e}")
            self.enable_coverage = False
    
    def _stop_coverage(self):
        """停止代码覆盖率收集"""
        if not self.coverage_instance:
            return
        
        try:
            self.coverage_instance.stop()
            self.coverage_instance.save()
            print("✅ 代码覆盖率收集已停止")
        except Exception as e:
            print(f"⚠️ 覆盖率收集停止失败: {e}")
    
    def _generate_coverage_report(self):
        """生成覆盖率报告"""
        if not self.coverage_instance:
            return
        
        try:
            # 生成终端报告
            print("\n" + "=" * 60)
            print("📊 代码覆盖率报告")
            print("=" * 60)
            
            # 获取覆盖率数据
            total = self.coverage_instance.report(show_missing=True)
            
            # 生成HTML报告
            html_dir = self.output_dir / "coverage_html"
            self.coverage_instance.html_report(directory=str(html_dir))
            print(f"🌐 HTML覆盖率报告: {html_dir}/index.html")
            
            # 生成XML报告（用于CI）
            xml_file = self.output_dir / "coverage.xml"
            self.coverage_instance.xml_report(outfile=str(xml_file))
            print(f"📄 XML覆盖率报告: {xml_file}")
            
            # 收集覆盖率统计数据
            self.coverage_data = {
                'total_coverage': total,
                'html_report': str(html_dir / "index.html"),
                'xml_report': str(xml_file)
            }
            
            # 更新统计信息
            self.stats['coverage'] = self.coverage_data
            
        except Exception as e:
            print(f"❌ 覆盖率报告生成失败: {e}")
    
    def get_coverage_summary(self) -> Dict[str, Any]:
        """获取覆盖率摘要"""
        if not self.coverage_instance:
            return {"enabled": False}
        
        try:
            # 获取详细的覆盖率数据
            analysis = {}
            for file_path in self.coverage_instance.get_data().measured_files():
                try:
                    file_analysis = self.coverage_instance.analysis2(file_path)
                    analysis[file_path] = {
                        'statements': len(file_analysis.statements),
                        'missing': len(file_analysis.missing),
                        'excluded': len(file_analysis.excluded),
                        'coverage_percent': round(
                            (len(file_analysis.statements) - len(file_analysis.missing)) / 
                            max(len(file_analysis.statements), 1) * 100, 2
                        )
                    }
                except Exception:
                    continue
            
            return {
                "enabled": True,
                "total_coverage": self.coverage_data.get('total_coverage', 0),
                "file_analysis": analysis
            }
        except Exception:
            return {"enabled": True, "error": "Failed to generate coverage summary"}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.results:
            return {}
        
        # 计算执行时间统计
        durations = [result.duration for result in self.results if result.duration > 0]
        
        if not durations:
            return {"total_time": 0, "test_count": len(self.results)}
        
        durations.sort()
        count = len(durations)
        
        return {
            "total_time": sum(durations),
            "average_time": sum(durations) / count,
            "median_time": durations[count // 2],
            "min_time": min(durations),
            "max_time": max(durations),
            "p95_time": durations[int(count * 0.95)] if count > 20 else durations[-1],
            "p99_time": durations[int(count * 0.99)] if count > 100 else durations[-1],
            "test_count": len(self.results),
            "tests_per_second": len(self.results) / sum(durations) if sum(durations) > 0 else 0
        }
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """分析失败的测试用例"""
        failed_tests = [r for r in self.results if r.status == "FAIL"]
        error_tests = [r for r in self.results if r.status == "ERROR"]
        
        # 按测试套件分组失败
        failures_by_suite = {}
        for test in failed_tests:
            suite = test.test_category or "unknown"
            if suite not in failures_by_suite:
                failures_by_suite[suite] = []
            failures_by_suite[suite].append({
                "test_name": test.test_name,
                "message": test.message,
                "details": test.details
            })
        
        # 错误分类
        error_categories = {}
        for test in error_tests:
            error_type = test.details.get('error_type', 'Unknown') if test.details else 'Unknown'
            if error_type not in error_categories:
                error_categories[error_type] = []
            error_categories[error_type].append(test.test_name)
        
        return {
            "total_failures": len(failed_tests),
            "total_errors": len(error_tests),
            "failures_by_suite": failures_by_suite,
            "error_categories": error_categories,
            "failure_rate": len(failed_tests) / max(len(self.results), 1) * 100
        }
    
    def export_junit_xml(self, output_file: str = None) -> str:
        """导出JUnit XML格式报告（用于CI集成）"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"junit_report_{timestamp}.xml"
        
        try:
            import xml.etree.ElementTree as ET
            
            # 创建根元素
            testsuites = ET.Element("testsuites")
            testsuites.set("tests", str(len(self.results)))
            testsuites.set("failures", str(len([r for r in self.results if r.status == "FAIL"])))
            testsuites.set("errors", str(len([r for r in self.results if r.status == "ERROR"])))
            testsuites.set("time", str(sum(r.duration for r in self.results)))
            
            # 按测试套件分组
            suites = {}
            for result in self.results:
                suite_name = result.test_category or "default"
                if suite_name not in suites:
                    suites[suite_name] = []
                suites[suite_name].append(result)
            
            # 为每个测试套件创建testsuite元素
            for suite_name, suite_results in suites.items():
                testsuite = ET.SubElement(testsuites, "testsuite")
                testsuite.set("name", suite_name)
                testsuite.set("tests", str(len(suite_results)))
                testsuite.set("failures", str(len([r for r in suite_results if r.status == "FAIL"])))
                testsuite.set("errors", str(len([r for r in suite_results if r.status == "ERROR"])))
                testsuite.set("time", str(sum(r.duration for r in suite_results)))
                
                # 为每个测试用例创建testcase元素
                for result in suite_results:
                    testcase = ET.SubElement(testsuite, "testcase")
                    testcase.set("name", result.test_name)
                    testcase.set("classname", f"{suite_name}.{result.test_name}")
                    testcase.set("time", str(result.duration))
                    
                    if result.status == "FAIL":
                        failure = ET.SubElement(testcase, "failure")
                        failure.set("message", result.message)
                        failure.text = str(result.details) if result.details else result.message
                    
                    elif result.status == "ERROR":
                        error = ET.SubElement(testcase, "error")
                        error.set("message", result.message)
                        error.text = str(result.details) if result.details else result.message
            
            # 写入文件
            tree = ET.ElementTree(testsuites)
            tree.write(output_file, encoding="utf-8", xml_declaration=True)
            
            print(f"📄 JUnit XML报告已生成: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"⚠️ 生成JUnit XML报告失败: {e}")
            return ""
    
    def run_with_retry(self, max_retries: int = 3, retry_failed_only: bool = True) -> Dict[str, Any]:
        """
        带重试机制的测试执行
        
        Args:
            max_retries: 最大重试次数
            retry_failed_only: 是否只重试失败的测试
            
        Returns:
            包含重试统计的测试结果
        """
        print(f"🔄 启动重试机制测试 (最多重试 {max_retries} 次)")
        
        retry_stats = {
            "retry_attempts": 0,
            "tests_retried": [],
            "final_success_rate": 0
        }
        
        # 首次运行
        initial_results = self.run_all_tests(verbose=True)
        failed_tests = [r for r in self.results if r.status in ["FAIL", "ERROR"]]
        
        if not failed_tests or max_retries == 0:
            retry_stats["final_success_rate"] = initial_results["statistics"]["passed"] / max(initial_results["statistics"]["total"], 1) * 100
            return {**initial_results, "retry_stats": retry_stats}
        
        # 重试失败的测试
        for retry_count in range(1, max_retries + 1):
            print(f"\n🔄 第 {retry_count} 次重试 ({len(failed_tests)} 个失败测试)")
            retry_stats["retry_attempts"] = retry_count
            
            # 重新运行失败的测试
            retried_results = []
            for failed_test in failed_tests:
                # 找到对应的测试套件和测试函数
                for suite in self.test_suites:
                    for test_func in suite.tests:
                        if test_func.__name__ == failed_test.test_name:
                            retry_result = self._run_single_test(test_func, suite.name, verbose=True)
                            retried_results.append(retry_result)
                            retry_stats["tests_retried"].append({
                                "test_name": failed_test.test_name,
                                "retry_attempt": retry_count,
                                "status": retry_result.status
                            })
                            break
            
            # 更新失败测试列表
            failed_tests = [r for r in retried_results if r.status in ["FAIL", "ERROR"]]
            
            if not failed_tests:
                print(f"✅ 重试成功！第 {retry_count} 次重试后所有测试通过")
                break
        
        # 计算最终成功率
        final_results = self.run_all_tests(verbose=False)  # 最终完整运行
        retry_stats["final_success_rate"] = final_results["statistics"]["passed"] / max(final_results["statistics"]["total"], 1) * 100
        
        return {**final_results, "retry_stats": retry_stats}
    
    def generate_trend_report(self, historical_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成趋势报告（比较历史测试数据）
        
        Args:
            historical_data: 历史测试数据列表
            
        Returns:
            趋势分析报告
        """
        if not historical_data:
            return {"error": "No historical data provided"}
        
        current_stats = self.get_statistics()
        
        # 计算趋势
        trends = {
            "pass_rate_trend": [],
            "coverage_trend": [],
            "performance_trend": [],
            "test_count_trend": []
        }
        
        for i, historical in enumerate(historical_data):
            hist_stats = historical.get("statistics", {})
            
            # 通过率趋势
            pass_rate = hist_stats.get("passed", 0) / max(hist_stats.get("total", 1), 1) * 100
            trends["pass_rate_trend"].append({
                "date": historical.get("timestamp", f"run_{i}"),
                "pass_rate": pass_rate
            })
            
            # 覆盖率趋势
            coverage = historical.get("coverage", {}).get("total_coverage", 0)
            trends["coverage_trend"].append({
                "date": historical.get("timestamp", f"run_{i}"),
                "coverage": coverage
            })
            
            # 性能趋势
            duration = hist_stats.get("duration", 0)
            trends["performance_trend"].append({
                "date": historical.get("timestamp", f"run_{i}"),
                "duration": duration
            })
            
            # 测试数量趋势
            test_count = hist_stats.get("total", 0)
            trends["test_count_trend"].append({
                "date": historical.get("timestamp", f"run_{i}"),
                "test_count": test_count
            })
        
        # 计算变化率
        if len(historical_data) >= 2:
            latest = historical_data[-1]["statistics"]
            previous = historical_data[-2]["statistics"]
            
            trends["changes"] = {
                "pass_rate_change": (current_stats["passed"] / max(current_stats["total"], 1) * 100) - 
                                  (latest.get("passed", 0) / max(latest.get("total", 1), 1) * 100),
                "test_count_change": current_stats["total"] - latest.get("total", 0),
                "duration_change": current_stats["duration"] - latest.get("duration", 0)
            }
        
        return trends