#!/usr/bin/env python3
"""
测试代码验证脚本
===============

验证新增测试代码的正确性：
1. 语法检查
2. 基本功能验证
3. 配置文件格式验证
4. 集成测试兼容性检查

使用方法:
    python tests/validate_test_code.py
"""

import sys
import os
import json
import subprocess
import importlib.util
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """验证结果"""
    test_name: str
    status: str  # "PASS", "FAIL", "WARNING"
    message: str
    details: str = ""

class TestCodeValidator:
    """测试代码验证器"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    def validate_syntax(self, file_path: str) -> ValidationResult:
        """验证Python文件语法"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 语法检查
            compile(content, file_path, 'exec')
            
            return ValidationResult(
                test_name=f"语法检查_{os.path.basename(file_path)}",
                status="PASS",
                message="语法检查通过"
            )
        except SyntaxError as e:
            return ValidationResult(
                test_name=f"语法检查_{os.path.basename(file_path)}",
                status="FAIL",
                message="语法错误",
                details=f"Line {e.lineno}: {e.text.strip() if e.text else ''} - {e.msg}"
            )
        except Exception as e:
            return ValidationResult(
                test_name=f"语法检查_{os.path.basename(file_path)}",
                status="WARNING",
                message="检查异常",
                details=str(e)
            )
    
    def validate_json_format(self, file_path: str) -> ValidationResult:
        """验证JSON文件格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            
            return ValidationResult(
                test_name=f"JSON格式_{os.path.basename(file_path)}",
                status="PASS",
                message="JSON格式正确"
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                test_name=f"JSON格式_{os.path.basename(file_path)}",
                status="FAIL",
                message="JSON格式错误",
                details=f"Line {e.lineno}: {e.msg}"
            )
        except Exception as e:
            return ValidationResult(
                test_name=f"JSON格式_{os.path.basename(file_path)}",
                status="WARNING",
                message="检查异常",
                details=str(e)
            )
    
    def validate_cli_interface(self, script_path: str) -> ValidationResult:
        """验证CLI接口功能"""
        try:
            result = subprocess.run(
                [sys.executable, script_path, '--help'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and 'usage:' in result.stdout:
                return ValidationResult(
                    test_name=f"CLI接口_{os.path.basename(script_path)}",
                    status="PASS",
                    message="CLI接口正常"
                )
            else:
                return ValidationResult(
                    test_name=f"CLI接口_{os.path.basename(script_path)}",
                    status="FAIL",
                    message="CLI接口异常",
                    details=f"stdout: {result.stdout[:200]}..., stderr: {result.stderr[:200]}..."
                )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                test_name=f"CLI接口_{os.path.basename(script_path)}",
                status="FAIL",
                message="CLI接口超时"
            )
        except Exception as e:
            return ValidationResult(
                test_name=f"CLI接口_{os.path.basename(script_path)}",
                status="WARNING",
                message="CLI检查异常",
                details=str(e)
            )
    
    def validate_existing_integration(self) -> ValidationResult:
        """验证与现有系统的集成性"""
        try:
            # 验证现有测试驱动是否正常
            result = subprocess.run(
                [sys.executable, 'tests/run_coverage.py', '--help'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return ValidationResult(
                    test_name="现有系统集成",
                    status="PASS",
                    message="与现有系统集成正常"
                )
            else:
                return ValidationResult(
                    test_name="现有系统集成",
                    status="FAIL",
                    message="现有系统运行异常",
                    details=result.stderr
                )
        except Exception as e:
            return ValidationResult(
                test_name="现有系统集成",
                status="WARNING",
                message="集成检查异常",
                details=str(e)
            )
    
    def validate_test_stubs(self) -> ValidationResult:
        """验证测试桩功能"""
        try:
            sys.path.insert(0, os.path.join(self.project_root, 'tests'))
            sys.path.insert(0, os.path.join(self.project_root, 'src'))
            
            # 测试Mock LLM Client
            from stubs.mock_llm_client import MockLLMClient
            client = MockLLMClient()
            result = client.detect_intent('测试', {'test': '测试'})
            
            # 测试Mock Config Loader
            from stubs.mock_config_loaders import MockBusinessConfigLoader
            loader = MockBusinessConfigLoader()
            config = loader.get_business_config('test')
            
            return ValidationResult(
                test_name="测试桩功能",
                status="PASS",
                message="测试桩功能正常",
                details=f"LLM结果: {result}, 配置类型: {type(config).__name__}"
            )
        except Exception as e:
            return ValidationResult(
                test_name="测试桩功能",
                status="FAIL",
                message="测试桩功能异常",
                details=str(e)
            )
    
    def run_full_validation(self):
        """运行完整验证"""
        print("🔍 开始测试代码验证...")
        print("=" * 60)
        
        # 验证新增的Python文件语法
        python_files = [
            'tests/test_performance.py',
            'tests/test_security.py', 
            'tests/test_ci_integration.py'
        ]
        
        for file_path in python_files:
            full_path = os.path.join(self.project_root, file_path)
            if os.path.exists(full_path):
                result = self.validate_syntax(full_path)
                self.results.append(result)
                print(f"  {result.status} - {result.test_name}: {result.message}")
                if result.details:
                    print(f"       详情: {result.details}")
        
        # 验证JSON配置文件
        json_files = [
            'tests/test_data/ci_config.json',
            'tests/test_data/test_cases.json'
        ]
        
        for file_path in json_files:
            full_path = os.path.join(self.project_root, file_path)
            if os.path.exists(full_path):
                result = self.validate_json_format(full_path)
                self.results.append(result)
                print(f"  {result.status} - {result.test_name}: {result.message}")
                if result.details:
                    print(f"       详情: {result.details}")
        
        # 验证CLI接口
        cli_scripts = [
            'tests/test_performance.py',
            'tests/test_security.py',
            'tests/test_ci_integration.py',
            'tests/run_coverage.py'
        ]
        
        for script_path in cli_scripts:
            full_path = os.path.join(self.project_root, script_path)
            if os.path.exists(full_path):
                result = self.validate_cli_interface(full_path)
                self.results.append(result)
                print(f"  {result.status} - {result.test_name}: {result.message}")
        
        # 验证现有系统集成
        result = self.validate_existing_integration()
        self.results.append(result)
        print(f"  {result.status} - {result.test_name}: {result.message}")
        
        # 验证测试桩
        result = self.validate_test_stubs()
        self.results.append(result)
        print(f"  {result.status} - {result.test_name}: {result.message}")
        if result.details:
            print(f"       详情: {result.details}")
    
    def generate_summary(self):
        """生成验证摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        warnings = sum(1 for r in self.results if r.status == "WARNING")
        
        print("\n" + "=" * 60)
        print("📊 验证结果摘要")
        print("=" * 60)
        print(f"总验证项: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️ 警告: {warnings}")
        print(f"📈 通过率: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ 失败项目:")
            for result in self.results:
                if result.status == "FAIL":
                    print(f"   - {result.test_name}: {result.message}")
        
        if warnings > 0:
            print("\n⚠️ 警告项目:")
            for result in self.results:
                if result.status == "WARNING":
                    print(f"   - {result.test_name}: {result.message}")
        
        print(f"\n🎯 验证结论: {'✅ 测试代码质量良好' if failed == 0 else '❌ 存在需要修复的问题'}")

def main():
    """验证主入口"""
    validator = TestCodeValidator()
    validator.run_full_validation()
    validator.generate_summary()
    
    # 根据验证结果设置退出码
    failed_count = sum(1 for r in validator.results if r.status == "FAIL")
    sys.exit(1 if failed_count > 0 else 0)

if __name__ == "__main__":
    main()