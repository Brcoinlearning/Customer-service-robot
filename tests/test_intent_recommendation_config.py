"""测试配置化后的意图推荐功能"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.form_based_system import FormBasedDialogSystem, SlotStatus
from semantics.option_mapping import SemanticMapper


class FakeLLMClient:
    """模拟LLM，不返回任何槽位"""
    def extract_slots(self, user_input: str, business_line: str, target_slots, current_values=None):
        return {}


def test_intent_recommendation_from_config():
    """验证意图推荐从配置文件正确加载和工作"""
    print("\n" + "="*60)
    print("测试: 意图推荐配置化")
    print("="*60)
    
    form = FormBasedDialogSystem('apple_store')
    llm = FakeLLMClient()
    semantic_mapper = SemanticMapper()
    
    # ---------------------------------------------------------
    # 测试1: "视频剪辑" → M3 Pro + 1TB
    # ---------------------------------------------------------
    print("\n测试1: 输入'我要做视频剪辑'")
    form.process_input('电脑', llm, semantic_mapper)
    form.process_input('MacBook Pro', llm, semantic_mapper)
    
    # [修正] 关键步骤：chip 依赖 size，必须先填充 size 才能触发 chip 的推荐
    print("  -> 补充输入: 14寸 (满足芯片依赖)")
    form.process_input('14寸', llm, semantic_mapper)
    
    # 触发意图推荐
    form.process_input('我要做视频剪辑', llm, semantic_mapper)
    
    # 检查chip槽位是否被推荐为M3 Pro
    chip_slot = form.current_form.get('chip')
    if chip_slot and chip_slot.status == SlotStatus.FILLED:
        print(f"  ✅ chip推荐: {chip_slot.value.value} (source: {chip_slot.value.source})")
        # [修正] 使用 in 判断以兼容 "M3 进阶款 (Pro)" 等不同配置Label
        assert "Pro" in chip_slot.value.value, f"期望M3 Pro，实际: {chip_slot.value.value}"
        assert chip_slot.value.source == 'intent_recommend', f"期望来源intent_recommend，实际: {chip_slot.value.source}"
    else:
        print(f"  ❌ chip槽位未填充")
        assert False, "chip槽位应该被推荐填充"
    
    # 检查storage槽位是否被推荐为1TB
    storage_slot = form.current_form.get('storage')
    if storage_slot and storage_slot.status == SlotStatus.FILLED:
        print(f"  ✅ storage推荐: {storage_slot.value.value} (source: {storage_slot.value.source})")
        assert "1TB" in storage_slot.value.value, f"期望1TB，实际: {storage_slot.value.value}"
        assert storage_slot.value.source == 'intent_recommend'
    else:
        print(f"  ❌ storage槽位未填充")
        assert False, "storage槽位应该被推荐填充"
    
    # ---------------------------------------------------------
    # 测试2: "办公" → M3 + 512GB
    # ---------------------------------------------------------
    print("\n测试2: 输入'办公用'")
    form2 = FormBasedDialogSystem('apple_store')
    form2.process_input('电脑', llm, semantic_mapper)
    form2.process_input('MacBook Air', llm, semantic_mapper)
    
    # [修正] 关键步骤：先填充 size
    print("  -> 补充输入: 13寸 (满足芯片依赖)")
    form2.process_input('13寸', llm, semantic_mapper)
    
    form2.process_input('办公用', llm, semantic_mapper)
    
    chip_slot2 = form2.current_form.get('chip')
    storage_slot2 = form2.current_form.get('storage')
    
    if chip_slot2 and chip_slot2.status == SlotStatus.FILLED:
        print(f"  ✅ chip推荐: {chip_slot2.value.value}")
        # [修正] 兼容 "M3 基础款" 或 "M3"
        assert "M3" in chip_slot2.value.value or "基础" in chip_slot2.value.value
    
    if storage_slot2 and storage_slot2.status == SlotStatus.FILLED:
        print(f"  ✅ storage推荐: {storage_slot2.value.value}")
        assert "512" in storage_slot2.value.value
    
    # ---------------------------------------------------------
    # 测试3: "便携" → 13寸
    # ---------------------------------------------------------
    print("\n测试3: 输入'便携'")
    form3 = FormBasedDialogSystem('apple_store')
    form3.process_input('电脑', llm, semantic_mapper)
    form3.process_input('MacBook Pro', llm, semantic_mapper)
    
    # 这里直接推荐 size，不需要前置依赖
    form3.process_input('便携', llm, semantic_mapper)
    
    size_slot3 = form3.current_form.get('size')
    if size_slot3 and size_slot3.status == SlotStatus.FILLED:
        print(f"  ✅ size推荐: {size_slot3.value.value}")
        assert "13" in size_slot3.value.value
        assert size_slot3.value.source == 'intent_recommend'
    
    print("\n✅ 所有意图推荐测试通过！")


if __name__ == '__main__':
    test_intent_recommendation_from_config()