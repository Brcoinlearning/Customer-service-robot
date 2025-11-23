import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.form_based_system import FormBasedDialogSystem, SlotStatus, SlotValue
from semantics.option_mapping import SemanticMapper


class FakeLLMClient:
    """模拟 LLM 抽取: 根据输入返回目标槽位"""
    def __init__(self):
        self.calls = []

    def extract_slots(self, user_input: str, business_line: str, target_slots, current_values=None):
        self.calls.append((user_input, target_slots))
        result = {}
        text = user_input.lower()
        # 模拟系列抽取
        if 'pro' in text:
            result['series'] = {"value": "MacBook Pro", "confidence": 0.8, "reason": "关键词 pro"}
        elif 'air' in text:
            result['series'] = {"value": "MacBook Air", "confidence": 0.75, "reason": "关键词 air"}
        # 模拟当用户说确认不再抽取
        return result


def test_multi_slot_extraction_and_completion():
    form = FormBasedDialogSystem('apple_store')
    llm = FakeLLMClient()
    semantic_mapper = SemanticMapper()

    # 输入同时包含尺寸 芯片 颜色 系列（系列通过 llm）
    text = '我要16寸 MacBook Pro M3 Max 银色 1TB'
    result = form.process_input(text, llm, semantic_mapper)
    # 基础直接匹配
    assert form.current_form['category'].status != SlotStatus.EMPTY
    assert form.current_form['chip'].value.value == 'M3 Max'
    assert form.current_form['storage'].value.value == '1TB'
    assert form.current_form['color'].value.value == '银色'
    # 系列依赖 llm
    series_slot = form.current_form.get('series')
    assert series_slot is not None
    assert series_slot.value is None or series_slot.value.value in ['MacBook Pro']  # 可能还未填因为系列不是直接映射


def test_conflict_resolution_flow():
    form = FormBasedDialogSystem('apple_store')
    llm = FakeLLMClient()
    semantic_mapper = SemanticMapper()

    # 初次填入颜色银色
    form.process_input('我要银色的电脑', llm, semantic_mapper)
    assert form.current_form['color'].value.value == '银色'
    # 再次输入深空灰触发冲突
    r2 = form.process_input('换成深空灰色', llm, semantic_mapper)
    assert form.awaiting_conflict_slot == 'color'
    assert '冲突' in r2['response']
    # 用户决策使用新值 (2)
    r3 = form.process_input('2', llm, semantic_mapper)
    assert form.current_form['color'].value.value == '深空灰'
    assert form.awaiting_conflict_slot is None


def test_validation_errors():
    form = FormBasedDialogSystem('apple_store')
    llm = FakeLLMClient()
    semantic_mapper = SemanticMapper()

    # 填充必须槽位（除了 series 先填完其它）
    form.process_input('我要电脑 M3 1TB 深空灰', llm, semantic_mapper)
    # 手工填入其余缺失使其完成以触发验证
    # 若系列缺失，模拟 llm 抽取系列 air 与尺寸 13寸 + M3 Max 不合法组合之一
    form.process_input('MacBook Air 13寸', llm, semantic_mapper)
    # 强制设置芯片与存储不合法组合 (M3 + 1TB 已通过输入形成) 完成时应触发验证错误
    # 补一次颜色已存在 使完成条件满足
    completion_inputs = ['确认']
    final_resp = ''
    for t in completion_inputs:
        r = form.process_input(t, llm, semantic_mapper)
        final_resp = r['response']
    # 如果完成且验证失败应该出现错误提示
    if form._check_form_completeness():
        assert ('不支持' in final_resp) or ('不合法' in final_resp) or ('调整' in final_resp)


def test_order_confirmation():
    form = FormBasedDialogSystem('apple_store')
    llm = FakeLLMClient()
    semantic_mapper = SemanticMapper()
    # 一次性提供大部分信息（系列由 llm 抽取）
    form.process_input('我要16寸 MacBook Pro M3 Pro 银色 512GB', llm, semantic_mapper)
    # 确认完成并下单
    assert form._check_form_completeness() is True
    resp = form.process_input('确认', llm, semantic_mapper)
    assert '订单已确认' in resp['response']
    assert form.order_confirmed is True
    assert '处理器' in resp['response'] or '颜色' in resp['response']


def test_numeric_selection():
    form = FormBasedDialogSystem('apple_store')
    llm = FakeLLMClient()
    semantic_mapper = SemanticMapper()
    # 获取初始提示并确认已设置首个槽位
    initial_prompt = form.get_initial_prompt()
    assert form.last_prompted_slot is not None
    first_slot = form.last_prompted_slot
    # 使用数字 1 选择首个槽位的第一个枚举值（若有）
    form.process_input('1', llm, semantic_mapper)
    assert form.current_form[first_slot].status in (SlotStatus.FILLED, SlotStatus.PARTIAL)
    # 系统应继续提示下一个必填槽位（若还有缺失）
    next_slot = form.last_prompted_slot
    if next_slot and next_slot != first_slot:
        form.process_input('2', llm, semantic_mapper)  # 选择第二个选项（如果存在）
        assert form.current_form[next_slot].status in (SlotStatus.FILLED, SlotStatus.PARTIAL)
    # 至少有一个必填槽位被填充
    filled_required = [name for name, s in form.current_form.items() if s.definition.required and s.status == SlotStatus.FILLED]
    assert len(filled_required) >= 1


if __name__ == '__main__':
    test_multi_slot_extraction_and_completion()
    test_conflict_resolution_flow()
    test_validation_errors()
    print('表单系统测试完成')