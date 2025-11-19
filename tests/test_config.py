"""
测试配置管理器 (Test Configuration Manager)

用于管理测试配置、加载测试数据、提供测试工具函数
"""

import json
import configparser
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class TestConfigManager:
    """测试配置管理器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录路径
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), "test_data")
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "test_config.ini"
        self.test_cases_file = self.config_dir / "test_cases.json"
        
        # 加载配置
        self.config = configparser.ConfigParser()
        if self.config_file.exists():
            self.config.read(self.config_file, encoding='utf-8')
        
        # 加载测试用例
        self.test_cases = {}
        if self.test_cases_file.exists():
            try:
                with open(self.test_cases_file, 'r', encoding='utf-8') as f:
                    self.test_cases = json.load(f)
            except json.JSONDecodeError as e:
                print(f"警告: 测试用例文件格式错误: {e}")
    
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            value = self.config.get(section, key)
            # 尝试转换类型
            if value.lower() in ['true', 'false']:
                return value.lower() == 'true'
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def get_test_cases(self, category: str) -> List[Dict[str, Any]]:
        """获取指定类别的测试用例"""
        return self.test_cases.get(category, [])
    
    def get_dsl_test_cases(self) -> List[Dict[str, Any]]:
        """获取DSL解析测试用例"""
        return self.get_test_cases("dsl_test_cases")
    
    def get_intent_detection_test_cases(self) -> List[Dict[str, Any]]:
        """获取意图识别测试用例"""
        return self.get_test_cases("intent_detection_test_cases")
    
    def get_scenario_test_cases(self) -> List[Dict[str, Any]]:
        """获取场景测试用例"""
        return self.get_test_cases("scenario_test_cases")
    
    def get_error_handling_test_cases(self) -> List[Dict[str, Any]]:
        """获取错误处理测试用例"""
        return self.get_test_cases("error_handling_test_cases")
    
    def get_performance_test_cases(self) -> List[Dict[str, Any]]:
        """获取性能测试用例"""
        return self.get_test_cases("performance_test_cases")
    
    # 便捷配置获取方法
    def is_mock_enabled(self) -> bool:
        """是否启用Mock"""
        return self.get_config("mock_settings", "enable_llm_mock", True)
    
    def get_output_dir(self) -> str:
        """获取输出目录"""
        return self.get_config("test_environment", "output_dir", "test_reports")
    
    def get_timeout(self) -> int:
        """获取测试超时时间"""
        return self.get_config("test_environment", "timeout", 30)
    
    def get_target_coverage(self) -> float:
        """获取目标覆盖率"""
        return self.get_config("coverage_settings", "target_coverage", 80.0)
    
    def should_generate_html_report(self) -> bool:
        """是否生成HTML报告"""
        return self.get_config("report_settings", "generate_html_report", True)
    
    def should_generate_json_report(self) -> bool:
        """是否生成JSON报告"""
        return self.get_config("report_settings", "generate_json_report", True)


# 全局配置管理器实例
_config_manager: Optional[TestConfigManager] = None

def get_config_manager() -> TestConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = TestConfigManager()
    return _config_manager


# 便捷函数
def load_test_cases(category: str) -> List[Dict[str, Any]]:
    """加载指定类别的测试用例"""
    return get_config_manager().get_test_cases(category)

def get_test_config(section: str, key: str, default: Any = None) -> Any:
    """获取测试配置值"""
    return get_config_manager().get_config(section, key, default)