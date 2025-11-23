"""
意图推荐测试套件
================

测试智能意图识别和推荐功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from drivers.test_driver import TestSuite
from core.form_based_system import FormBasedDialogSystem, SlotStatus
from semantics.option_mapping import SemanticMapper
from stubs.mock_llm_client import MockLLMClient


def test_intent_chip_video_editing():
    """测试意图推荐 - 视频剪辑场景推荐M3 Pro"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook Pro', llm, mapper)
    form.process_input('我要做视频剪辑', llm, mapper)
    
    chip = form.current_form.get('chip')
    assert chip.status == SlotStatus.FILLED
    assert chip.value.value == 'M3 Pro'
    assert chip.value.source == 'intent_recommend'
    return True


def test_intent_chip_office():
    """测试意图推荐 - 办公场景推荐M3"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook Air', llm, mapper)
    form.process_input('办公用', llm, mapper)
    
    chip = form.current_form.get('chip')
    storage = form.current_form.get('storage')
    
    assert chip.status == SlotStatus.FILLED
    assert chip.value.value == 'M3'
    assert storage.status == SlotStatus.FILLED
    assert storage.value.value == '512GB'
    return True


def test_intent_size_portable():
    """测试意图推荐 - 便携需求推荐13寸"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook Pro', llm, mapper)
    form.process_input('便携', llm, mapper)
    
    size = form.current_form.get('size')
    assert size.status == SlotStatus.FILLED
    assert size.value.value == '13寸'
    assert size.value.source == 'intent_recommend'
    return True


def test_intent_dining_hotpot():
    """测试意图推荐 - 火锅需求推荐海底捞"""
    form = FormBasedDialogSystem('dining')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('餐饮预订', llm, mapper)
    form.process_input('想吃火锅', llm, mapper)
    
    brand = form.current_form.get('brand')
    assert brand.status == SlotStatus.FILLED
    assert brand.value.value == '海底捞'
    assert brand.value.source == 'intent_recommend'
    return True


def test_intent_dining_evening():
    """测试意图推荐 - 晚上用餐推荐晚餐时段"""
    form = FormBasedDialogSystem('dining')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('餐饮预订', llm, mapper)
    form.process_input('海底捞', llm, mapper)
    form.process_input('晚上去', llm, mapper)
    
    series = form.current_form.get('series')
    assert series.status == SlotStatus.FILLED
    assert series.value.value == '晚餐时段'
    return True


def test_intent_dining_couple():
    """测试意图推荐 - 约会场景推荐2人"""
    form = FormBasedDialogSystem('dining')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('餐饮预订', llm, mapper)
    form.process_input('海底捞', llm, mapper)
    form.process_input('晚餐时段', llm, mapper)
    form.process_input('和女朋友约会', llm, mapper)
    
    party_size = form.current_form.get('party_size')
    assert party_size.status == SlotStatus.FILLED
    assert party_size.value.value == '2人'
    return True


def test_intent_multi_slot():
    """测试意图推荐 - 一句话触发多个槽位推荐"""
    form = FormBasedDialogSystem('apple_store')
    llm = MockLLMClient()
    mapper = SemanticMapper()
    
    form.process_input('电脑', llm, mapper)
    form.process_input('MacBook Pro', llm, mapper)
    form.process_input('做视频剪辑用，需要便携', llm, mapper)
    
    # 应该同时推荐chip和size
    chip = form.current_form.get('chip')
    size = form.current_form.get('size')
    storage = form.current_form.get('storage')
    
    assert chip.value.value == 'M3 Pro'
    assert size.value.value == '13寸'
    assert storage.value.value == '1TB'
    return True


def get_intent_recommendation_tests() -> TestSuite:
    """获取意图推荐测试套件"""
    return TestSuite(
        name="intent_recommendation",
        description="智能意图识别和推荐功能测试",
        tests=[
            test_intent_chip_video_editing,
            test_intent_chip_office,
            test_intent_size_portable,
            test_intent_dining_hotpot,
            test_intent_dining_evening,
            test_intent_dining_couple,
            test_intent_multi_slot,
        ]
    )
