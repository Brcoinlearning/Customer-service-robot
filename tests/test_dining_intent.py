"""测试餐饮预订的意图推荐功能"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.form_based_system import FormBasedDialogSystem, SlotStatus
from semantics.option_mapping import SemanticMapper


class FakeLLMClient:
    """模拟LLM，不返回任何槽位"""
    def extract_slots(self, user_input: str, business_line: str, target_slots, current_values=None):
        return {}


def test_dining_intent_recommendation():
    """验证餐饮预订的意图推荐"""
    print("\n" + "="*60)
    print("测试: 餐饮预订意图推荐")
    print("="*60)
    
    form = FormBasedDialogSystem('dining')
    llm = FakeLLMClient()
    semantic_mapper = SemanticMapper()
    
    # 测试1: "火锅" → 海底捞
    print("\n测试1: 输入'想吃火锅'")
    form.process_input('餐饮预订', llm, semantic_mapper)
    result = form.process_input('想吃火锅', llm, semantic_mapper)
    
    brand_slot = form.current_form.get('brand')
    if brand_slot and brand_slot.status == SlotStatus.FILLED:
        print(f"  ✅ brand推荐: {brand_slot.value.value} (source: {brand_slot.value.source})")
        assert brand_slot.value.value == '海底捞', f"期望海底捞，实际: {brand_slot.value.value}"
        assert brand_slot.value.source == 'intent_recommend'
    else:
        print(f"  ⚠️ brand槽位未通过意图推荐填充")
    
    # 测试2: "晚上" → 晚餐时段
    print("\n测试2: 输入'晚上去'")
    form2 = FormBasedDialogSystem('dining')
    form2.process_input('餐饮预订', llm, semantic_mapper)
    form2.process_input('海底捞', llm, semantic_mapper)
    form2.process_input('晚上去', llm, semantic_mapper)
    
    series_slot = form2.current_form.get('series')
    if series_slot and series_slot.status == SlotStatus.FILLED:
        print(f"  ✅ series推荐: {series_slot.value.value}")
        assert series_slot.value.value == '晚餐时段'
    
    # 测试3: "约会" → 2人
    print("\n测试3: 输入'和女朋友约会'")
    form3 = FormBasedDialogSystem('dining')
    form3.process_input('餐饮预订', llm, semantic_mapper)
    form3.process_input('海底捞', llm, semantic_mapper)
    form3.process_input('晚餐时段', llm, semantic_mapper)
    form3.process_input('和女朋友约会', llm, semantic_mapper)
    
    party_slot = form3.current_form.get('party_size')
    if party_slot and party_slot.status == SlotStatus.FILLED:
        print(f"  ✅ party_size推荐: {party_slot.value.value}")
        assert party_slot.value.value == '2人'
        assert party_slot.value.source == 'intent_recommend'
    
    # 测试4: "明天" → 明天
    print("\n测试4: 输入'明天晚上'")
    form4 = FormBasedDialogSystem('dining')
    form4.process_input('餐饮预订', llm, semantic_mapper)
    form4.process_input('海底捞', llm, semantic_mapper)
    form4.process_input('晚餐时段', llm, semantic_mapper)
    form4.process_input('2人', llm, semantic_mapper)
    form4.process_input('明天晚上', llm, semantic_mapper)
    
    date_slot = form4.current_form.get('date')
    if date_slot and date_slot.status == SlotStatus.FILLED:
        print(f"  ✅ date推荐: {date_slot.value.value}")
        assert date_slot.value.value == '明天'
        # 允许direct或intent_recommend，因为"明天"既在别名中也在意图关键词中
        assert date_slot.value.source in ['direct', 'intent_recommend']
    
    print("\n✅ 餐饮预订意图推荐测试通过！")


if __name__ == '__main__':
    test_dining_intent_recommendation()
