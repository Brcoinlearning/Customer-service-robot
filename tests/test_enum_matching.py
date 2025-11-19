import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.form_based_system import FormBasedDialogSystem, SlotStatus
from semantics.option_mapping import SemanticMapper

# 测试: 纯数字选择 + 唯一匹配

def test_numeric_selection_series():
    form = FormBasedDialogSystem('apple_computer')
    mapper = SemanticMapper()
    # 触发系列提示
    form.process_input('我要买电脑', None, mapper)
    assert form.last_prompted_slot == 'series'
    r = form.process_input('2', None, None)
    assert form.current_form['series'].value.value == 'MacBook Pro'
    assert form.current_form['series'].status == SlotStatus.FILLED


def test_unique_match_storage():
    form = FormBasedDialogSystem('apple_computer')
    mapper = SemanticMapper()
    # 前置: 类别 + 芯片，进入系列提示
    form.process_input('我要买电脑 M3', None, mapper)
    assert form.last_prompted_slot == 'series'
    # 数字选择系列
    form.process_input('2', None, mapper)
    # 进入存储提示
    assert form.last_prompted_slot == 'storage'
    # 唯一匹配: 1T -> 1TB
    r = form.process_input('我想要1T', None, mapper)
    assert form.current_form['storage'].value.value == '1TB'

def test_ambiguous_storage():
    form = FormBasedDialogSystem('apple_computer')
    mapper = SemanticMapper()
    form.process_input('我要买电脑 M3', None, mapper)
    assert form.last_prompted_slot == 'series'
    form.process_input('2', None, mapper)  # MacBook Pro
    assert form.last_prompted_slot == 'storage'
    # 输入 512 触发两个命中 (512GB 与 512GB 特价版)
    resp = form.process_input('我想要512', None, mapper)
    assert '多个可能匹配' in resp['response'] or '歧义' in resp['response']
    # 未填充存储
    assert form.current_form['storage'].status == SlotStatus.EMPTY


def test_unique_match_color_alias():
    form = FormBasedDialogSystem('apple_computer')
    mapper = SemanticMapper()
    # 类别 + 芯片
    form.process_input('我要买电脑 M3', None, mapper)
    assert form.last_prompted_slot == 'series'
    # 选择系列
    form.process_input('2', None, mapper)
    assert form.last_prompted_slot == 'storage'
    # 填存储
    form.process_input('我想要1T', None, mapper)
    assert form.last_prompted_slot == 'color'
    # 颜色唯一匹配别名 暗蓝 -> 午夜色
    r = form.process_input('我喜欢暗蓝', None, mapper)
    assert form.current_form['color'].value.value == '午夜色'

if __name__ == '__main__':
    test_numeric_selection_series()
    test_unique_match_storage()
    test_unique_match_color_alias()
    test_ambiguous_storage()
    print('enum matching tests passed')
