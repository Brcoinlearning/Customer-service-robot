"""
测试驱动程序 (Test Driver)
负责执行测试套件、收集结果、生成结构化报告
"""

import sys
import os
import json
import time
import traceback
import io
import contextlib
import inspect  # 用于提取测试函数的文档字符串
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    test_category: str
    status: str  # "PASS", "FAIL", "ERROR"
    duration: float
    description: str = ""  # 新增：测试内容的语言概括（来自docstring）
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: str = ""
    output_log: str = ""   # 存储该测试用例的详细交互日志

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
    def __init__(self, output_dir: str = None, formats: List[str] = None):
        """
        Args:
            output_dir: 输出目录
            formats: 报告格式列表，默认为 ['text']
        """
        self.output_dir = Path(output_dir) if output_dir else Path("test_reports")
        self.output_dir.mkdir(exist_ok=True)
        self.formats = formats or ['text']
        
        self.test_suites: List[TestSuite] = []
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.stats = {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0}

    def register_test_suite(self, suite: TestSuite):
        self.test_suites.append(suite)

    def run_all_tests(self, verbose: bool = False) -> Dict[str, Any]:
        print(f"🚀 开始测试 (输出目录: {self.output_dir})")
        self.start_time = datetime.now()
        
        # 简要输出：只在终端显示进度
        for suite in self.test_suites:
            print(f"📦 套件: {suite.name} ({len(suite.tests)} 个用例)...", end="", flush=True)
            self._run_test_suite(suite)
            print(" 完成")
        
        self.end_time = datetime.now()
        self._calculate_stats()
        
        # 生成报告
        if 'text' in self.formats: self._save_text_report()
        # 保留扩展性，暂不生成 html/json
        
        # 终端输出最终简报
        self._print_terminal_summary()
        
        return {"stats": self.stats}

    def _run_test_suite(self, suite: TestSuite):
        if suite.setup:
            try: suite.setup()
            except Exception: pass
            
        for test_func in suite.tests:
            self._run_single_test(test_func, suite.name)
            
        if suite.teardown:
            try: suite.teardown()
            except Exception: pass

    def _run_single_test(self, test_func: Callable, suite_name: str):
        test_name = test_func.__name__
        start_time = time.time()
        
        # 1. 提取测试描述 (Docstring)
        # 获取函数注释的第一行作为测试内容的概括
        doc = inspect.getdoc(test_func)
        if doc:
            description = doc.strip().split('\n')[0]
        else:
            description = "无测试描述"

        result = TestResult(
            test_name=test_name,
            test_category=suite_name,
            status="UNKNOWN",
            duration=0.0,
            description=description
        )
        
        # 2. 捕获输出
        capture_buffer = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(capture_buffer):
                test_result = test_func()
            
            if test_result is None or test_result is True:
                result.status = "PASS"
            else:
                result.status = "FAIL"
                result.message = "断言返回 False"
        except AssertionError as e:
            result.status = "FAIL"
            result.message = f"断言失败: {str(e)}"
        except Exception as e:
            result.status = "ERROR"
            result.message = f"运行错误: {str(e)}"
            result.details['traceback'] = traceback.format_exc()
        finally:
            result.duration = time.time() - start_time
            result.output_log = capture_buffer.getvalue()
            self.results.append(result)

    def _calculate_stats(self):
        self.stats['total'] = len(self.results)
        for r in self.results:
            if r.status == 'PASS': self.stats['passed'] += 1
            elif r.status == 'FAIL': self.stats['failed'] += 1
            elif r.status == 'ERROR': self.stats['errors'] += 1

    def _save_text_report(self):
        """生成包含概览和详细日志的结构化报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.output_dir / f"test_report_{timestamp}.log"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            # --- Header ---
            f.write("="*80 + "\n")
            f.write(f"  智能客服系统测试报告\n")
            f.write(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  总计: {self.stats['total']} | 通过: {self.stats['passed']} | 失败: {self.stats['failed']} | 错误: {self.stats['errors']}\n")
            f.write("="*80 + "\n\n")

            # --- Part 1: 测试情况概览 (Test Overview) ---
            f.write("一、测试情况概览\n")
            f.write("-" * 80 + "\n")
            # 格式化字符串：ID, 状态, 测试名称, 描述与结果
            header = f"{'ID':<4} | {'状态':<6} | {'测试名称':<30} | {'测试内容与结果摘要'}\n"
            f.write(header)
            f.write("-" * 80 + "\n")

            for idx, res in enumerate(self.results, 1):
                status_icon = "PASS" if res.status == "PASS" else res.status
                
                # 生成结果摘要语言
                if res.status == "PASS":
                    summary = f"内容：{res.description}\n{' '*46} 结果：验证成功。系统功能符合预期。"
                else:
                    summary = f"内容：{res.description}\n{' '*46} 结果：验证失败。{res.message}"
                
                # 打印第一行
                line1 = f"{idx:<4} | {status_icon:<6} | {res.test_name:<30} | 内容：{res.description}\n"
                f.write(line1)
                # 打印第二行（结果摘要，缩进对齐）
                if res.status == "PASS":
                    line2 = f"{' '*46} | 结果：验证成功。功能运行正常。\n"
                else:
                    line2 = f"{' '*46} | 结果：⚠️ 失败。原因: {res.message}\n"
                f.write(line2)
                f.write("-" * 80 + "\n")
            
            f.write("\n\n")

            # --- Part 2: 详细测试日志 (Detailed Logs) ---
            f.write("二、详细测试交互日志\n")
            f.write("="*80 + "\n")
            
            for idx, res in enumerate(self.results, 1):
                icon = "✅" if res.status == "PASS" else "❌"
                f.write(f"Test Case #{idx}: {res.test_name}\n")
                f.write(f"测试内容: {res.description}\n")
                f.write(f"运行结果: {icon} {res.status} (耗时: {res.duration:.3f}s)\n")
                f.write("-" * 40 + "\n")
                
                if res.output_log.strip():
                    f.write(res.output_log.strip() + "\n")
                else:
                    f.write("(该测试无交互输出)\n")
                
                if res.status != "PASS" and res.details.get('traceback'):
                    f.write("\n[异常堆栈]:\n")
                    f.write(res.details['traceback'])
                
                f.write("\n" + "="*80 + "\n\n")

        print(f"\n📝 完整测试报告已生成: {log_file}")

    def _print_terminal_summary(self):
        """终端只输出简要统计"""
        print("\n" + "-" * 30)
        print(f"测试总结")
        print(f"通过率: {self.stats['passed']}/{self.stats['total']} ({(self.stats['passed']/self.stats['total']*100):.1f}%)")
        if self.stats['failed'] > 0 or self.stats['errors'] > 0:
            print(f"⚠️ 存在 {self.stats['failed']} 个失败, {self.stats['errors']} 个错误，请查看日志文件。")
        print("-" * 30)