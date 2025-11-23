#!/usr/bin/env python3
"""
自动化测试脚本 - 运行所有测试套件
=================================

功能：
1. 自动发现和执行所有测试用例
2. 生成详细的测试报告（HTML + JSON）
3. 计算测试覆盖率和通过率
4. 支持持续集成环境

使用方法：
    python tests/run_all_tests.py
    python tests/run_all_tests.py --verbose
    python tests/run_all_tests.py --output=custom_reports/
"""

import sys
import os

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from drivers.test_driver import TestDriver, TestSuite
from test_suites.test_core_system import get_core_system_tests
from test_suites.test_llm_integration import get_llm_integration_tests
from test_suites.test_config_loader import get_config_loader_tests
from test_suites.test_intent_recommendation import get_intent_recommendation_tests
from test_suites.test_business_scenarios import get_business_scenario_tests
from test_suites.test_exception_handling import (
    get_exception_handling_tests, 
    get_boundary_condition_tests, 
    get_robustness_tests
)


def main():
    """主测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='运行客服机器人系统测试套件')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细输出')
    parser.add_argument('--output', '-o', default='test_reports', help='测试报告输出目录')
    parser.add_argument('--suite', '-s', help='指定运行特定测试套件')
    parser.add_argument('--no-coverage', action='store_true', help='禁用代码覆盖率统计')
    parser.add_argument('--include-exceptions', action='store_true', help='包含异常处理测试')
    
    args = parser.parse_args()
    
    # 创建测试驱动
    driver = TestDriver(output_dir=args.output, enable_coverage=not args.no_coverage)
    
    # 注册基础测试套件
    all_suites = [
        get_core_system_tests(),
        get_config_loader_tests(),
        get_intent_recommendation_tests(),
        get_llm_integration_tests(),
        get_business_scenario_tests(),
    ]
    
    # 根据参数添加异常处理测试
    if args.include_exceptions:
        all_suites.extend([
            get_exception_handling_tests(),
            get_boundary_condition_tests(),
            get_robustness_tests(),
        ])
    
    # 如果指定了特定套件，只运行该套件
    if args.suite:
        all_suites = [s for s in all_suites if s.name == args.suite]
        if not all_suites:
            print(f"❌ 未找到测试套件: {args.suite}")
            print(f"可用的测试套件:")
            for suite in all_suites:
                print(f"  - {suite.name}")
            return 1
    
    # 注册套件
    for suite in all_suites:
        driver.register_test_suite(suite)
    
    # 运行测试
    report = driver.run_all_tests(verbose=args.verbose)
    
    # 返回退出码（失败或错误时返回1）
    if report['summary']['statistics']['failed'] > 0 or report['summary']['statistics']['errors'] > 0:
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
