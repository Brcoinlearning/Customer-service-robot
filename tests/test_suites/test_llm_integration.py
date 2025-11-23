"""
LLM集成测试套件
===============

测试与大语言模型的集成功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from drivers.test_driver import TestSuite
from stubs.mock_llm_client import MockLLMClient


def test_mock_llm_initialization():
    """测试Mock LLM客户端初始化"""
    llm = MockLLMClient()
    assert llm is not None
    return True


def test_mock_llm_extract_slots():
    """测试Mock LLM槽位抽取"""
    llm = MockLLMClient()
    
    result = llm.extract_slots(
        "我要MacBook Pro M3 Pro",
        "apple_store",
        ["series", "chip"]
    )
    
    assert isinstance(result, dict)
    # Mock客户端会返回空字典或模拟数据
    return True


def test_mock_llm_robustness():
    """测试Mock LLM鲁棒性"""
    llm = MockLLMClient()
    
    # 测试空输入
    result = llm.extract_slots("", "apple_store", [])
    assert isinstance(result, dict)
    
    # 测试无效槽位
    result = llm.extract_slots("test", "apple_store", ["invalid_slot"])
    assert isinstance(result, dict)
    
    return True


def test_llm_response_format():
    """测试LLM响应格式"""
    llm = MockLLMClient()
    
    result = llm.extract_slots(
        "我要16寸银色的",
        "apple_store",
        ["size", "color"]
    )
    
    # 检查响应格式
    for slot_name, slot_info in result.items():
        if slot_info:  # 如果有返回值
            assert isinstance(slot_info, dict)
            assert 'value' in slot_info
            assert 'confidence' in slot_info
    
    return True


def test_llm_confidence_levels():
    """测试LLM置信度水平"""
    llm = MockLLMClient()
    
    result = llm.extract_slots(
        "我想要MacBook",
        "apple_store",
        ["series"]
    )
    
    # 如果有返回，检查置信度范围
    for slot_info in result.values():
        if slot_info and 'confidence' in slot_info:
            conf = slot_info['confidence']
            assert 0 <= conf <= 1.0
    
    return True


def get_llm_integration_tests() -> TestSuite:
    """获取LLM集成测试套件"""
    return TestSuite(
        name="llm_integration",
        description="大语言模型集成功能测试",
        tests=[
            test_mock_llm_initialization,
            test_mock_llm_extract_slots,
            test_mock_llm_robustness,
            test_llm_response_format,
            test_llm_confidence_levels,
        ]
    )
