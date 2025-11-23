"""
配置加载器测试套件
==================

测试业务配置加载和管理功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from drivers.test_driver import TestSuite
from knowledge.business_config_loader import business_config_loader


def test_config_loader_initialization():
    """测试配置加载器初始化"""
    assert business_config_loader is not None
    businesses = business_config_loader.list_businesses()
    assert len(businesses) > 0
    assert 'apple_store' in businesses
    assert 'dining' in businesses
    return True


def test_get_business_config():
    """测试获取业务配置"""
    config = business_config_loader.get_business_config('apple_store')
    assert config is not None
    assert config.name == 'apple_store'
    assert config.display_name == '苹果专卖店'
    return True


def test_get_slot_specs():
    """测试获取槽位规格"""
    specs = business_config_loader.get_slot_specs('apple_store')
    assert len(specs) > 0
    
    # 检查是否包含必要的槽位
    slot_names = [spec.name for spec in specs]
    assert 'category' in slot_names
    assert 'series' in slot_names
    assert 'chip' in slot_names
    return True


def test_get_enums():
    """测试获取枚举定义"""
    enums = business_config_loader.get_enums('apple_store')
    assert 'category' in enums
    assert 'chip' in enums
    assert 'storage' in enums
    
    # 检查枚举值结构
    chip_enums = enums['chip']
    assert len(chip_enums) > 0
    assert 'label' in chip_enums[0]
    assert 'aliases' in chip_enums[0]
    return True


def test_get_intent_recommendations():
    """测试获取意图推荐配置"""
    intents = business_config_loader.get_intent_recommendations('apple_store')
    assert 'chip' in intents
    assert 'storage' in intents
    assert 'size' in intents
    
    # 检查意图配置结构
    chip_intents = intents['chip']
    assert len(chip_intents) > 0
    assert 'intent' in chip_intents[0]
    assert 'keywords' in chip_intents[0]
    assert 'recommend' in chip_intents[0]
    return True


def test_get_filters():
    """测试获取过滤器配置"""
    config = business_config_loader.get_business_config('apple_store')
    assert config.filters is not None
    assert 'series_by_category' in config.filters
    
    # 检查过滤器内容
    series_by_cat = config.filters['series_by_category']
    assert '电脑' in series_by_cat
    assert '手机' in series_by_cat
    return True


def test_dining_config():
    """测试餐饮业务配置"""
    config = business_config_loader.get_business_config('dining')
    assert config is not None
    assert config.name == 'dining'
    
    specs = business_config_loader.get_slot_specs('dining')
    assert len(specs) > 0
    
    slot_names = [spec.name for spec in specs]
    assert 'brand' in slot_names
    assert 'party_size' in slot_names
    assert 'date' in slot_names
    return True


def get_config_loader_tests() -> TestSuite:
    """获取配置加载器测试套件"""
    return TestSuite(
        name="config_loader",
        description="业务配置加载器功能测试",
        tests=[
            test_config_loader_initialization,
            test_get_business_config,
            test_get_slot_specs,
            test_get_enums,
            test_get_intent_recommendations,
            test_get_filters,
            test_dining_config,
        ]
    )
