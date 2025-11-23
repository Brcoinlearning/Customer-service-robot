"""
业务场景测试套件
================

测试完整的业务场景流程
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from drivers.test_driver import TestSuite
from core.form_based_system import FormBasedDialogSystem, SlotStatus
from semantics.option_mapping import SemanticMapper
from stubs.mock_llm_client import MockLLMClient


def test_apple_store_complete_flow():
    """测试苹果商店完整购物流程"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 模拟完整对话流程
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook Pro', llm, mapper)
    
    # 关键步骤：输入 M3 Pro
    # 这是一个容易出错的点，需要验证是否正确识别为 Pro 版本而非基础版
    form.process_input('M3 Pro', llm, mapper)
    
    form.process_input('16寸', llm, mapper)
    form.process_input('1TB', llm, mapper)
    form.process_input('银色', llm, mapper)
    
    # 检查所有必填槽位是否填充
    assert form.current_form['category'].status == SlotStatus.FILLED
    assert form.current_form['series'].status == SlotStatus.FILLED
    assert form.current_form['chip'].status == SlotStatus.FILLED
    assert form.current_form['size'].status == SlotStatus.FILLED
    assert form.current_form['storage'].status == SlotStatus.FILLED
    assert form.current_form['color'].status == SlotStatus.FILLED
    
    # [关键修正] 验证数据准确性
    # 确保 'M3 Pro' 输入没有被错误匹配为 'M3' (基础款)
    chip_value = form.current_form['chip'].value.value
    # 使用 'in' 判断以兼容 "M3 Pro" 或 "M3 进阶款 (Pro)" 等不同配置Label
    assert "Pro" in chip_value, f"芯片识别错误，期望包含'Pro'，实际得到: '{chip_value}'"
    
    # 检查表单完整性
    assert form._check_form_completeness() == True
    
    return True


def test_dining_complete_flow():
    """测试餐饮预订完整流程"""
    form = FormBasedDialogSystem('dining')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 模拟完整预订流程
    form.process_input('餐饮预订', llm, mapper)
    form.process_input('海底捞', llm, mapper)
    form.process_input('晚餐时段', llm, mapper)
    form.process_input('4人', llm, mapper)
    form.process_input('明天', llm, mapper)
    
    # 检查槽位填充
    assert form.current_form['category'].status == SlotStatus.FILLED
    assert form.current_form['brand'].status == SlotStatus.FILLED
    assert form.current_form['series'].status == SlotStatus.FILLED
    assert form.current_form['party_size'].status == SlotStatus.FILLED
    assert form.current_form['date'].status == SlotStatus.FILLED
    
    return True


def test_one_shot_input():
    """测试一句话包含多个信息"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 一句话包含多个槽位信息
    form.process_input('我要16寸MacBook Pro M3 Pro银色1TB', llm, mapper)
    
    # 应该能识别出多个槽位
    filled_slots = [
        name for name, slot in form.current_form.items()
        if slot.status == SlotStatus.FILLED
    ]
    
    assert len(filled_slots) >= 4  # 至少识别出4个槽位
    
    # [修正] 验证关键信息准确性
    if 'chip' in filled_slots:
        val = form.current_form['chip'].value.value
        assert "Pro" in val or "Max" in val, f"One-shot输入芯片识别可能有误: {val}"
        
    return True


def test_natural_language_flow():
    """测试自然语言对话流程"""
    form = FormBasedDialogSystem('dining')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 使用自然语言描述
    form.process_input('我想订餐', llm, mapper)
    form.process_input('想吃火锅', llm, mapper)
    form.process_input('晚上6点左右', llm, mapper)
    form.process_input('我们有4个人', llm, mapper)
    form.process_input('明天去', llm, mapper)
    
    # 检查关键槽位是否被正确识别
    brand = form.current_form.get('brand')
    if brand and brand.status == SlotStatus.FILLED:
        assert brand.value.value == '海底捞'
    
    return True


def test_partial_information_handling():
    """测试部分信息处理"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 只提供部分信息
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook', llm, mapper)
    
    # 系统应该能处理不完整的输入
    assert form.current_form['category'].status == SlotStatus.FILLED
    
    # 继续补充信息
    form.process_input('Pro版本', llm, mapper)
    
    return True


def test_error_recovery():
    """测试错误恢复"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 正常输入
    form.process_input('电脑', llm, mapper)
    
    # 无效输入（应该不会崩溃）
    form.process_input('xxxxx', llm, mapper)
    form.process_input('', llm, mapper)
    form.process_input('   ', llm, mapper)
    
    # 继续正常输入
    form.process_input('MacBook Pro', llm, mapper)
    
    # 系统应该仍然正常工作
    assert form.current_form['category'].status == SlotStatus.FILLED
    assert form.current_form['series'].status == SlotStatus.FILLED
    
    return True


def test_mixed_scenarios():
    """测试混合场景"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    # 混合使用精确匹配和意图推荐
    form.process_input('电脑', llm, mapper)  # 精确匹配
    form.process_input('MacBook Pro', llm, mapper)  # 精确匹配
    
    # [修正] 意图推荐芯片(chip)前，必须先满足其依赖项尺寸(size)
    form.process_input('16寸', llm, mapper)  # 精确匹配 - 提前到这里
    
    form.process_input('做视频剪辑', llm, mapper)  # 意图推荐 -> 推荐 M3 Pro + 1TB
    
    form.process_input('银色', llm, mapper)  # 精确匹配
    
    # 检查是否正确处理了混合输入
    chip = form.current_form.get('chip')
    storage = form.current_form.get('storage')
    
    # 意图推荐的槽位
    # [修正] 兼容新的配置Label
    assert "Pro" in chip.value.value or chip.value.value == 'M3 Pro'
    assert "1TB" in storage.value.value
    
    # 精确匹配的槽位
    assert form.current_form['size'].value.value == '16寸'
    assert form.current_form['color'].value.value == '银色'
    
    return True


def get_business_scenario_tests() -> TestSuite:
    """获取业务场景测试套件"""
    return TestSuite(
        name="business_scenarios",
        description="完整业务场景流程测试",
        tests=[
            test_apple_store_complete_flow,
            test_dining_complete_flow,
            test_one_shot_input,
            test_natural_language_flow,
            test_partial_information_handling,
            test_error_recovery,
            test_mixed_scenarios,
        ]
    )