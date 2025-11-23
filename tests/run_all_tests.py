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

#!/usr/bin/env python3
import sys
import os

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from drivers.test_driver import TestDriver
# 导入需要被“监听”的核心类
from core.form_based_system import FormBasedDialogSystem

# --- 1. 注入自动日志拦截器 ---
original_process_input = FormBasedDialogSystem.process_input

def logged_process_input(self, user_input, *args, **kwargs):
    """
    这是一个装饰器函数，用于拦截机器人的输入输出，
    并将其打印出来，以便 TestDriver 捕获到日志文件中。
    """
    # 打印用户输入
    print(f"\n👤 User: {user_input}")
    
    # 执行原始逻辑
    result = original_process_input(self, user_input, *args, **kwargs)
    
    # 打印机器人回复
    response_text = result.get('response', '').replace('\n', '\n   ') # 缩进以便阅读
    print(f"🤖 Robot: {response_text}")
    
    return result

# 应用 Monkey Patch
FormBasedDialogSystem.process_input = logged_process_input
# ---------------------------

# 导入测试套件
from test_suites.test_core_system import get_core_system_tests
from test_suites.test_llm_integration import get_llm_integration_tests
from test_suites.test_config_loader import get_config_loader_tests
from test_suites.test_intent_recommendation import get_intent_recommendation_tests
from test_suites.test_business_scenarios import get_business_scenario_tests
from test_suites.test_exception_handling import get_exception_handling_tests

def main():
    # 初始化驱动，指定只生成 text 格式
    driver = TestDriver(output_dir='test_reports', formats=['text'])
    
    # 注册所有套件
    driver.register_test_suite(get_core_system_tests())
    driver.register_test_suite(get_config_loader_tests())
    driver.register_test_suite(get_intent_recommendation_tests())
    driver.register_test_suite(get_llm_integration_tests())
    driver.register_test_suite(get_business_scenario_tests())
    driver.register_test_suite(get_exception_handling_tests())
    
    # 运行
    result = driver.run_all_tests()
    
    # 退出码
    if result['stats']['failed'] > 0 or result['stats']['errors'] > 0:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())