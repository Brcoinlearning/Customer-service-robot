"""
配置加载器测试桩
================

目的：
1. 模拟业务配置加载异常（文件损坏、字段缺失等）
2. 模拟YAML流程定义解析错误
3. 支持测试配置相关的错误处理机制

设计：
- MockBusinessConfigLoader：模拟业务配置加载异常
- MockYAMLFlowLoader：模拟DSL解析异常
- 支持多种失败场景配置
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

# 模拟业务配置结构
@dataclass
class MockBusinessConfig:
    name: str
    slot_specs: List[Dict] = None
    enums: Dict[str, List[Dict]] = None
    filters: Dict[str, Dict] = None
    templates: Dict[str, List[str]] = None
    intent_recommendations: Dict[str, List[Dict]] = None
    command_keywords: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.slot_specs is None:
            self.slot_specs = []
        if self.enums is None:
            self.enums = {}
        if self.filters is None:
            self.filters = {}
        if self.templates is None:
            self.templates = {}
        if self.intent_recommendations is None:
            self.intent_recommendations = {}
        if self.command_keywords is None:
            self.command_keywords = {}


class MockBusinessConfigLoader:
    """
    业务配置加载器测试桩
    
    模拟各种配置加载异常场景：
    - 配置文件不存在
    - 配置文件格式错误（JSON语法错误）
    - 必需字段缺失
    - 字段类型错误
    - 循环依赖
    """
    
    def __init__(self, fail_mode: str = None, custom_configs: Dict[str, MockBusinessConfig] = None):
        """
        初始化Mock配置加载器
        
        Args:
            fail_mode: 失败模式
                - None: 正常模式
                - "file_not_found": 配置文件不存在
                - "json_syntax_error": JSON语法错误
                - "missing_required_fields": 缺少必需字段
                - "invalid_field_types": 字段类型错误
                - "circular_dependency": 槽位循环依赖
                - "empty_enums": 枚举为空
                - "invalid_filters": 过滤器配置无效
            custom_configs: 自定义配置映射 {business_name: config}
        """
        self.fail_mode = fail_mode
        self.custom_configs = custom_configs or {}
        self.call_history = []
        
        # 默认正常配置
        self.default_config = MockBusinessConfig(
            name="test_business",
            slot_specs=[
                {
                    "name": "category",
                    "required": True,
                    "description": "产品大类",
                    "enums_key": "category",
                    "dependencies": [],
                    "allow_llm": False
                },
                {
                    "name": "series", 
                    "required": True,
                    "description": "产品系列",
                    "enums_key": "series",
                    "dependencies": ["category"],
                    "allow_llm": True
                }
            ],
            enums={
                "category": [
                    {"label": "电脑", "aliases": ["电脑", "笔记本", "mac"]},
                    {"label": "手机", "aliases": ["手机", "iphone", "苹果手机"]}
                ],
                "series": [
                    {"label": "MacBook Air", "aliases": ["air", "macbook air"]},
                    {"label": "iPhone 16", "aliases": ["iphone 16", "16"]}
                ]
            },
            filters={
                "series_by_category": {
                    "电脑": ["MacBook Air", "MacBook Pro"],
                    "手机": ["iPhone 16", "iPhone 15"]
                }
            },
            templates={
                "form_welcome": ["欢迎使用测试业务"],
                "category_prompt": ["请选择产品类别"]
            },
            intent_recommendations={
                "series": [
                    {"keywords": ["专业", "性能"], "recommend": "MacBook Pro", "confidence": 0.75}
                ]
            },
            command_keywords={
                "confirm": ["确认", "确定", "好的"],
                "cancel": ["取消", "退出", "不要"]
            }
        )
    
    def get_business_config(self, business_name: str) -> MockBusinessConfig:
        """
        获取业务配置，支持各种异常场景
        """
        self.call_history.append({"method": "get_business_config", "business_name": business_name})
        
        # 检查自定义配置
        if business_name in self.custom_configs:
            return self.custom_configs[business_name]
        
        # 模拟各种失败场景
        if self.fail_mode == "file_not_found":
            raise FileNotFoundError(f"Business config file not found: {business_name}.json")
        
        elif self.fail_mode == "json_syntax_error":
            raise json.JSONDecodeError("Expecting ',' delimiter", "invalid json", 10)
        
        elif self.fail_mode == "missing_required_fields":
            # 返回缺少必需字段的配置
            config = MockBusinessConfig(name=business_name)
            # slot_specs为空，缺少必需配置
            return config
        
        elif self.fail_mode == "invalid_field_types":
            # 返回字段类型错误的配置
            config = self.default_config
            config.slot_specs = "invalid_type"  # 应该是列表，但设为字符串
            return config
        
        elif self.fail_mode == "circular_dependency":
            # 返回有循环依赖的配置
            config = MockBusinessConfig(
                name=business_name,
                slot_specs=[
                    {"name": "slot_a", "dependencies": ["slot_b"]},
                    {"name": "slot_b", "dependencies": ["slot_c"]},
                    {"name": "slot_c", "dependencies": ["slot_a"]}  # 循环依赖
                ]
            )
            return config
        
        elif self.fail_mode == "empty_enums":
            # 返回枚举为空的配置
            config = self.default_config
            config.enums = {"category": []}  # 空枚举
            return config
        
        elif self.fail_mode == "invalid_filters":
            # 返回无效过滤器配置
            config = self.default_config
            config.filters = {
                "series_by_category": {
                    "电脑": ["NonExistentSeries"]  # 引用不存在的系列
                }
            }
            return config
        
        # 正常模式，返回默认配置
        return self.default_config
    
    def get_slot_specs(self, business_name: str) -> List[Dict]:
        """获取槽位规格"""
        config = self.get_business_config(business_name)
        
        if self.fail_mode == "invalid_field_types" and isinstance(config.slot_specs, str):
            raise TypeError(f"Expected list for slot_specs, got {type(config.slot_specs)}")
        
        return config.slot_specs
    
    def get_enums(self, business_name: str) -> Dict[str, List[Dict]]:
        """获取枚举定义"""
        config = self.get_business_config(business_name)
        return config.enums
    
    def get_filters(self, business_name: str) -> Dict[str, Dict]:
        """获取过滤器配置"""
        config = self.get_business_config(business_name)
        return config.filters
    
    def get_templates(self, business_name: str) -> Dict[str, List[str]]:
        """获取模板配置"""
        config = self.get_business_config(business_name)
        return config.templates
    
    def get_intent_recommendations(self, business_name: str) -> Dict[str, List[Dict]]:
        """获取意图推荐配置"""
        config = self.get_business_config(business_name)
        return config.intent_recommendations
    
    def get_command_keywords(self, business_name: str) -> Dict[str, List[str]]:
        """获取命令关键词配置"""
        config = self.get_business_config(business_name)
        return config.command_keywords
    
    def set_fail_mode(self, fail_mode: str):
        """设置失败模式"""
        self.fail_mode = fail_mode
    
    def add_custom_config(self, business_name: str, config: MockBusinessConfig):
        """添加自定义配置"""
        self.custom_configs[business_name] = config
    
    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self.call_history
    
    def reset_history(self):
        """重置调用历史"""
        self.call_history = []


class MockYAMLFlowLoader:
    """
    YAML流程加载器测试桩
    
    模拟DSL解析各种异常场景：
    - YAML语法错误
    - 缺少必需字段
    - 槽位定义错误
    - 依赖关系无效
    - 事件定义错误
    """
    
    def __init__(self, fail_mode: str = None, custom_flows: Dict[str, Dict] = None):
        """
        初始化Mock YAML流程加载器
        
        Args:
            fail_mode: 失败模式
                - None: 正常模式
                - "yaml_syntax_error": YAML语法错误
                - "missing_flow_field": 缺少flow字段
                - "invalid_slot_definition": 无效槽位定义
                - "invalid_dependencies": 无效依赖关系
                - "missing_process_order": 缺少process_order
                - "invalid_events": 无效事件定义
            custom_flows: 自定义流程配置
        """
        self.fail_mode = fail_mode
        self.custom_flows = custom_flows or {}
        self.call_history = []
        
        # 默认正常流程配置
        self.default_flow = {
            "flow": {
                "name": "test_flow",
                "version": "1.0",
                "business_line": "test_business",
                "process_order": ["category", "series"],
                "slots": {
                    "category": {
                        "label": "产品大类",
                        "required": True,
                        "enums_key": "category",
                        "dependencies": [],
                        "allow_llm": False
                    },
                    "series": {
                        "label": "产品系列", 
                        "required": True,
                        "enums_key": "series",
                        "dependencies": ["category"],
                        "allow_llm": True
                    }
                },
                "events": {
                    "on_start": [
                        {"say": "欢迎使用测试流程"}
                    ],
                    "on_complete": [
                        {"say": "流程完成"}
                    ]
                }
            }
        }
    
    def load(self, yaml_file: str) -> Dict[str, Any]:
        """
        加载YAML流程定义，支持各种异常场景
        """
        self.call_history.append({"method": "load", "yaml_file": yaml_file})
        
        # 检查自定义流程
        if yaml_file in self.custom_flows:
            return self.custom_flows[yaml_file]
        
        # 模拟各种失败场景
        if self.fail_mode == "file_not_found":
            raise FileNotFoundError(f"YAML file not found: {yaml_file}")
        
        elif self.fail_mode == "yaml_syntax_error":
            # 模拟YAML语法错误
            import yaml
            raise yaml.YAMLError("Invalid YAML syntax at line 5")
        
        elif self.fail_mode == "missing_flow_field":
            # 返回缺少flow字段的配置
            return {"invalid": "config"}
        
        elif self.fail_mode == "invalid_slot_definition":
            # 返回无效槽位定义
            flow = self.default_flow.copy()
            flow["flow"]["slots"]["invalid_slot"] = {
                "label": "无效槽位",
                # 缺少required字段
                "enums_key": "invalid_enum"
            }
            return flow
        
        elif self.fail_mode == "invalid_dependencies":
            # 返回无效依赖关系
            flow = self.default_flow.copy()
            flow["flow"]["slots"]["series"]["dependencies"] = ["non_existent_slot"]
            return flow
        
        elif self.fail_mode == "missing_process_order":
            # 返回缺少process_order的配置
            flow = self.default_flow.copy()
            del flow["flow"]["process_order"]
            return flow
        
        elif self.fail_mode == "invalid_events":
            # 返回无效事件定义
            flow = self.default_flow.copy()
            flow["flow"]["events"]["on_start"] = "invalid_event_type"  # 应该是列表
            return flow
        
        # 正常模式
        return self.default_flow
    
    def validate(self, flow_config: Dict[str, Any]) -> bool:
        """
        验证流程配置
        """
        self.call_history.append({"method": "validate", "flow_config": "...truncated..."})
        
        if self.fail_mode in ["invalid_slot_definition", "invalid_dependencies", "missing_process_order", "invalid_events"]:
            return False
        
        # 基本验证逻辑
        if "flow" not in flow_config:
            return False
        
        flow = flow_config["flow"]
        required_fields = ["name", "business_line", "process_order", "slots"]
        
        for field in required_fields:
            if field not in flow:
                return False
        
        return True
    
    def set_fail_mode(self, fail_mode: str):
        """设置失败模式"""
        self.fail_mode = fail_mode
    
    def add_custom_flow(self, yaml_file: str, flow_config: Dict[str, Any]):
        """添加自定义流程配置"""
        self.custom_flows[yaml_file] = flow_config
    
    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self.call_history
    
    def reset_history(self):
        """重置调用历史"""
        self.call_history = []


# 便捷工厂函数
def create_mock_config_loader(scenario: str = "normal") -> MockBusinessConfigLoader:
    """
    创建预配置的Mock配置加载器
    
    Args:
        scenario: 测试场景名称
            - "normal": 正常工作模式
            - "file_error": 文件相关错误
            - "format_error": 格式相关错误  
            - "content_error": 内容相关错误
    
    Returns:
        配置好的MockBusinessConfigLoader实例
    """
    scenarios = {
        "normal": MockBusinessConfigLoader(),
        "file_error": MockBusinessConfigLoader(fail_mode="file_not_found"),
        "format_error": MockBusinessConfigLoader(fail_mode="json_syntax_error"),
        "content_error": MockBusinessConfigLoader(fail_mode="missing_required_fields")
    }
    
    return scenarios.get(scenario, MockBusinessConfigLoader())


def create_mock_yaml_loader(scenario: str = "normal") -> MockYAMLFlowLoader:
    """
    创建预配置的Mock YAML加载器
    
    Args:
        scenario: 测试场景名称
            - "normal": 正常工作模式
            - "syntax_error": YAML语法错误
            - "validation_error": 验证错误
    
    Returns:
        配置好的MockYAMLFlowLoader实例
    """
    scenarios = {
        "normal": MockYAMLFlowLoader(),
        "syntax_error": MockYAMLFlowLoader(fail_mode="yaml_syntax_error"),
        "validation_error": MockYAMLFlowLoader(fail_mode="invalid_slot_definition")
    }
    
    return scenarios.get(scenario, MockYAMLFlowLoader())