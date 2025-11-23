"""
核心系统测试套件
================

测试表单对话系统的核心功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from drivers.test_driver import TestSuite
from core.form_based_system import FormBasedDialogSystem, SlotStatus
from semantics.option_mapping import SemanticMapper
from stubs.mock_llm_client import MockLLMClient


def test_form_initialization():
    """测试表单初始化"""
    form = FormBasedDialogSystem('apple_store')
    assert form.current_form is not None
    assert len(form.current_form) > 0
    assert form.order_confirmed == False
    return True


def test_slot_filling_direct_match():
    """测试槽位填充 - 直接匹配"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('电脑', llm, mapper)
    category = form.current_form.get('category')
    assert category is not None
    assert category.status == SlotStatus.FILLED
    assert category.value.value == '电脑'
    return True


def test_semantic_filtering():
    """测试语义过滤"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 先填充category和series
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook Pro', llm, mapper)
    
    # series应该被正确填充
    series = form.current_form.get('series')
    assert series.status == SlotStatus.FILLED
    assert series.value.value == 'MacBook Pro'
    return True


def test_multi_slot_extraction():
    """测试多槽位抽取"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook Pro', llm, mapper)
    form.process_input('M3 Pro 16寸 1TB 银色', llm, mapper)
    
    # 检查多个槽位是否被填充
    assert form.current_form['chip'].status == SlotStatus.FILLED
    assert form.current_form['size'].status == SlotStatus.FILLED
    assert form.current_form['storage'].status == SlotStatus.FILLED
    assert form.current_form['color'].status == SlotStatus.FILLED
    return True


def test_form_completion_check():
    """测试表单完整性检查"""
    form = FormBasedDialogSystem('apple_store')
    
    # 初始状态不完整
    assert form._check_form_completeness() == False
    
    # 填充所有必填槽位后应该完整
    from core.form_based_system import SlotValue
    for slot_name, slot in form.current_form.items():
        if slot.definition.required:
            slot.status = SlotStatus.FILLED
            slot.value = SlotValue('test_value', 0.9, 'test', 'test')
    
    assert form._check_form_completeness() == True
    return True


def get_core_system_tests() -> TestSuite:
    """获取核心系统测试套件"""
    return TestSuite(
        name="core_system",
        description="核心表单对话系统功能测试",
        tests=[
            test_form_initialization,
            test_slot_filling_direct_match,
            test_semantic_filtering,
            test_multi_slot_extraction,
            test_form_completion_check,
        ]
    )
