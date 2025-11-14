import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# 同时将 src 目录加入路径，便于通过 core/parser 等顶层包名导入
sys.path.insert(0, os.path.join(project_root, 'src'))


from src.core.enhanced_context import EnhancedConversationContext
from src.knowledge.product_knowledge import ProductKnowledge
from src.parser.dsl_parser import DSLParser
from src.interpreter.interpreter import DSLInterpreter

def test_enhanced_context():
    """测试增强版上下文管理器"""
    print("🧪 测试增强版上下文管理器...")

    # 创建上下文管理器
    context = EnhancedConversationContext()

    # 测试基础功能
    context.set_stage("category_selection")
    context.add_to_chain("category", "手机")
    context.add_to_chain("brand", "苹果")
    context.add_to_chain("series", "iPhone 15")

    # 验证选择链
    chain = context.get_current_chain()
    print(f"📝 选择链: {[item['value'] for item in chain]}")
    assert len(chain) == 3, "选择链长度应该为3"

    # 验证当前选择
    assert context.get_context()["current_category"] == "手机"
    assert context.get_context()["current_brand"] == "苹果"
    assert context.get_context()["current_series"] == "iPhone 15"

    # 测试回退功能
    context.rollback_chain(1)
    assert context.get_context()["current_series"] is None
    print("✅ 回退功能测试通过")

    # 测试偏好记录
    context.record_preference("budget", "5000-8000")
    context.record_preference("usage", "摄影")
    preferences = context.get_context()["user_preferences"]
    assert preferences["budget"] == "5000-8000"
    print("✅ 偏好记录测试通过")

    print("🎉 增强上下文管理器测试全部通过！")

def test_product_knowledge():
    """测试产品知识库"""
    print("\n🧪 测试产品知识库...")

    knowledge = ProductKnowledge()

    # 测试品类获取
    categories = knowledge.get_category_options()
    print(f"📁 可用品类: {[cat['name'] for cat in categories]}")
    assert len(categories) > 0, "应该至少有一个品类"

    # 测试品牌获取
    brands = knowledge.get_brands_in_category("手机")
    print(f"🏷️ 手机品牌: {brands}")
    assert "苹果" in brands, "手机品类应该包含苹果"

    # 测试系列获取
    series = knowledge.get_series_in_brand("手机", "苹果")
    print(f"📦 苹果手机系列: {series}")
    assert any("iPhone 15" in s for s in series), "苹果手机应该包含iPhone 15"

    # 测试搜索功能
    results = knowledge.search_products("iPhone")
    print(f"🔍 搜索 'iPhone' 结果: {len(results)} 个")
    assert len(results) > 0, "搜索应该返回结果"

    print("🎉 产品知识库测试全部通过！")

def test_dsl_memory_rules():
    """测试DSL记忆规则"""
    print("\n🧪 测试DSL记忆规则解析...")

    # 加载DSL脚本
    dsl_content = """
INTENT product_query: "产品咨询"

RULE first_product_inquiry
WHEN INTENT_IS product_query AND CONTEXT_HAS "query_count" = 0
THEN
    RESPOND "首次产品咨询"
    INCREMENT "query_count"

RULE category_selected
WHEN INTENT_IS product_query AND CONTEXT_HAS "current_category"
THEN
    RESPOND "选择了${current_category}"
    ADD_TO_CHAIN "category" "${current_category}"
"""

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)

    # 验证解析结果
    assert "product_query" in parsed_dsl["intents"]
    assert len(parsed_dsl["rules"]) == 2

    print("📄 解析的规则:")
    for rule in parsed_dsl["rules"]:
        print(f"  - {rule['name']}: {len(rule['conditions'])}条件, {len(rule['actions'])}动作")

    print("🎉 DSL记忆规则解析测试通过！")

def test_memory_integration():
    """测试记忆功能集成"""
    print("\n🧪 测试记忆功能集成...")

    # 创建完整的工作流
    context = EnhancedConversationContext()
    knowledge = ProductKnowledge()

    # 模拟用户对话流程
    print("👤 用户: 我想买手机")
    context.set_stage("category_selection")
    context.add_to_chain("category", "手机")
    context.increment_query_count()

    print("🤖 系统: 已记录品类选择 -> 手机")

    print("👤 用户: 苹果的")
    context.add_to_chain("brand", "苹果")
    context.record_preference("brand", "苹果")

    print("🤖 系统: 已记录品牌偏好 -> 苹果")

    print("👤 用户: iPhone 15")
    context.add_to_chain("series", "iPhone 15")

    # 验证最终状态
    summary = context.get_conversation_summary()
    print(f"📊 对话摘要: {summary}")

    assert summary["product_chain_length"] == 3
    assert summary["current_selection"]["category"] == "手机"
    assert summary["current_selection"]["brand"] == "苹果"
    assert summary["current_selection"]["series"] == "iPhone 15"

    print("🎉 记忆功能集成测试通过！")

def test_scenario_simulation():
    """测试完整场景模拟"""
    print("\n🎭 测试完整产品咨询场景...")

    context = EnhancedConversationContext()
    knowledge = ProductKnowledge()

    # 场景1: 完整的手机购买咨询（在苹果产品线内更换型号）
    scenarios = [
        {"user": "你好", "action": "greeting"},
        {"user": "我想买手机", "action": "set_category", "value": "手机"},
        {"user": "苹果的", "action": "set_brand", "value": "苹果"},
        {"user": "iPhone 15怎么样", "action": "set_series", "value": "iPhone 15"},
        {"user": "换个16 Pro看看", "action": "change_brand", "value": "iPhone 16 Pro 系列"},
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- 步骤 {i} ---")
        print(f"👤 用户: {scenario['user']}")

        if scenario["action"] == "greeting":
            context.set_stage("welcome")
            print("🤖 系统: 欢迎！")

        elif scenario["action"] == "set_category":
            context.add_to_chain("category", scenario["value"])
            brands = knowledge.get_brands_in_category(scenario["value"])
            print(f"🤖 系统: 已选择{scenario['value']}，可选品牌: {', '.join(brands)}")

        elif scenario["action"] == "set_brand":
            context.add_to_chain("brand", scenario["value"])
            series = knowledge.get_series_in_brand(context.get_context()["current_category"], scenario["value"])
            print(f"🤖 系统: 已选择{scenario['value']}，可选系列: {', '.join(series)}")

        elif scenario["action"] == "set_series":
            context.add_to_chain("series", scenario["value"])
            print(f"🤖 系统: 已选择{scenario['value']}，正在加载详细信息...")

        elif scenario["action"] == "change_brand":
            # 回退到品牌选择（这里用来模拟用户更换为另一款 iPhone 型号）
            context.rollback_chain(1)  # 回退系列选择
            context.add_to_chain("brand", scenario["value"])
            series = knowledge.get_series_in_brand(context.get_context()["current_category"], scenario["value"])
            print(f"🤖 系统: 已切换到{scenario['value']}，可选系列: {', '.join(series)}")

    # 最终验证
    final_chain = context.get_current_chain()
    chain_values = [item["value"] for item in final_chain]
    print(f"\n📋 最终选择链: {' → '.join(chain_values)}")

    assert "手机" in chain_values
    assert any("iPhone 16 Pro" in v for v in chain_values)  # 最后选择的型号
    assert not any("iPhone 15" in v for v in chain_values)  # 旧型号应被回退掉

    print("🎉 完整场景模拟测试通过！")



def test_first_vs_repeat_product_query_prompts():
    """测试首次 vs 重复产品咨询时的 DSL 行为分支"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)

    # 场景一：首次产品咨询（query_count = 0）
    context_first = {
        "current_stage": "welcome",
        "current_category": None,
        "user_input": "帮我推荐一下产品",
        "query_count": 0,
    }
    responses_first = interpreter.execute("product_query", context_first)
    assert any("首次" in r for r in responses_first)
    # 提示文案中应同时提到电脑和手机，且可以额外提到 iPad 等苹果产品
    assert any("电脑" in r and "手机" in r for r in responses_first)

    # 场景二：重复产品咨询（query_count > 0）
    # 注意：真实对话中，首次兜底后 current_stage 会被设置为 "category_select"
    context_repeat = {
        "current_stage": "category_select",
        "current_category": None,
        "user_input": "我还想再看看别的",
        "query_count": 1,
    }
    responses_repeat = interpreter.execute("product_query", context_repeat)
    assert any("还没确定" in r for r in responses_repeat)



def test_cart_operation_reset_with_reset_keyword():
    """当 LLM 将“重置”识别为 cart_operation 时，也能完整重置上下文"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)

    # 模拟已经在手机品牌选择阶段的场景
    context_manager = EnhancedConversationContext()
    context_manager.add_to_chain("category", "手机")
    context_manager.set_stage("brand_select")

    ctx = context_manager.get_context()
    ctx["_manager"] = context_manager
    ctx["user_input"] = "重置"

    responses = interpreter.execute("cart_operation", ctx)

    # 执行后应回到初始 welcome 阶段，产品选择链清空
    new_ctx = context_manager.get_context()
    assert new_ctx["current_stage"] == "welcome"
    assert new_ctx["current_category"] is None
    assert new_ctx["product_chain"] == []
    assert any("重新开始" in r for r in responses)



def test_fallback_brand_select_from_dsl():
    """当在品牌选择阶段输入无法匹配的内容时，应触发 DSL 中的 fallback 规则"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)

    # 模拟已经进入手机品牌选择阶段，但用户输入了一句无法匹配任何品牌的内容
    context_manager = EnhancedConversationContext()
    context_manager.update_context("current_category", "手机")
    context_manager.set_stage("brand_select")

    ctx = context_manager.get_context()
    ctx["_manager"] = context_manager
    ctx["user_input"] = "随便说点什么，故意不包含品牌关键词"

    responses = interpreter.execute("product_query", ctx)

    # 应该触发 fallback_brand_select_* 规则，而不是 Python 内置字典
    # 这里期望出现“手机”的品牌提示文案
    assert any("手机" in r and "品牌" in r for r in responses)



def test_suggest_brands_uses_product_knowledge():
    """SUGGEST_BRANDS 应基于 ProductKnowledge 动态给出品牌列表"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)
    knowledge = ProductKnowledge()

    # 模拟已进入“手机”品牌选择阶段，用户询问“有哪些品牌”
    context_manager = EnhancedConversationContext()
    context_manager.update_context("current_category", "手机")
    context_manager.set_stage("brand_select")

    ctx = context_manager.get_context()
    ctx["_manager"] = context_manager
    ctx["user_input"] = "有哪些品牌？"
    ctx["knowledge"] = knowledge

    responses = interpreter.execute("product_query", ctx)

    brands = knowledge.get_brands_in_category("手机")
    # 期望响应中既提到“品牌”，又至少包含一个知识库中的品牌名
    assert any("品牌" in r and any(b in r for b in brands) for r in responses)


def test_suggest_series_uses_product_knowledge():
    """SUGGEST_SERIES 应基于 ProductKnowledge 动态给出系列/型号列表"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)
    knowledge = ProductKnowledge()

    # 模拟已进入“电脑-苹果”系列选择阶段，用户询问“有哪些系列”
    context_manager = EnhancedConversationContext()
    context_manager.update_context("current_category", "电脑")
    context_manager.update_context("current_brand", "苹果")
    context_manager.set_stage("series_select")

    ctx = context_manager.get_context()
    ctx["_manager"] = context_manager
    ctx["user_input"] = "有哪些系列？"
    ctx["knowledge"] = knowledge

    responses = interpreter.execute("product_query", ctx)



def test_suggest_series_for_ipad_and_imac_uses_product_knowledge():
    """SUGGEST_SERIES 在 iPad / iMac 场景下应基于 ProductKnowledge 输出系列列表"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)
    knowledge = ProductKnowledge()

    # 场景1：平板-苹果（iPad）系列列表
    context_manager_ipad = EnhancedConversationContext()
    context_manager_ipad.update_context("current_category", "平板")
    context_manager_ipad.update_context("current_brand", "苹果")
    context_manager_ipad.set_stage("series_select")

    ctx_ipad = context_manager_ipad.get_context()
    ctx_ipad["_manager"] = context_manager_ipad
    ctx_ipad["user_input"] = "有哪些系列？"
    ctx_ipad["knowledge"] = knowledge

    responses_ipad = interpreter.execute("product_query", ctx_ipad)
    series_ipad = knowledge.get_series_in_brand("平板", "苹果")
    assert any("iPad" in s for s in series_ipad)
    assert any(any(s in r for s in series_ipad) for r in responses_ipad)

    # 场景2：电脑-苹果-台式机（iMac / Mac mini / Mac Studio）系列列表
    context_manager_desktop = EnhancedConversationContext()
    context_manager_desktop.update_context("current_category", "电脑")
    context_manager_desktop.update_context("current_subtype", "台式机")
    context_manager_desktop.update_context("current_brand", "苹果")
    context_manager_desktop.set_stage("series_select")

    ctx_desktop = context_manager_desktop.get_context()
    ctx_desktop["_manager"] = context_manager_desktop
    ctx_desktop["user_input"] = "有哪些系列？"
    ctx_desktop["knowledge"] = knowledge

    responses_desktop = interpreter.execute("product_query", ctx_desktop)
    series_desktop = knowledge.get_series_in_brand("电脑", "苹果")
    # 期望包含 iMac / Mac mini / Mac Studio 等桌面系列
    assert any("iMac" in s or "Mac mini" in s or "Mac Studio" in s for s in series_desktop)
    assert any(any(s in r for s in series_desktop) for r in responses_desktop)

    series_list = knowledge.get_series_in_brand("电脑", "苹果")


def test_usage_scenario_recommendation_study_laptop():
    """当用户在电脑品类下提到“适合学习”的需求时，应基于知识库给出推荐"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)
    knowledge = ProductKnowledge()

    # 模拟场景：用户已选择电脑品类，在系列选择阶段说“推荐一个适合学习的电脑”
    context_manager = EnhancedConversationContext()
    context_manager.update_context("current_category", "电脑")
    context_manager.set_stage("series_select")

    ctx = context_manager.get_context()
    ctx["_manager"] = context_manager
    ctx["user_input"] = "给我推荐一个适合学习的电脑"
    ctx["knowledge"] = knowledge

    responses = interpreter.execute("product_query", ctx)

    # 知识库中在“电脑 + 学习”场景下，应推荐苹果相关机型（如 MacBook）
    assert any("苹果" in r or "MacBook" in r for r in responses)
    # 同时应该出现“学习”这样的场景词，表明是用途推荐而不是普通流程文案
    assert any("学习" in r for r in responses)



def test_describe_series_config_uses_product_knowledge():
    """DESCRIBE_SERIES_CONFIG 应基于 ProductKnowledge 输出系列配置"""
    dsl_path = os.path.join(project_root, 'src', 'scripts', 'ecommerce.dsl')
    with open(dsl_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    parser = DSLParser()
    parsed_dsl = parser.parse(dsl_content)
    interpreter = DSLInterpreter(parsed_dsl)
    knowledge = ProductKnowledge()

    # 场景：电脑-苹果，处于系列选择阶段，用户选择 MacBook Air
    context_manager = EnhancedConversationContext()
    context_manager.update_context("current_category", "电脑")
    context_manager.update_context("current_brand", "苹果")
    context_manager.set_stage("series_select")

    ctx = context_manager.get_context()
    ctx["_manager"] = context_manager
    ctx["user_input"] = "air 13寸"
    ctx["knowledge"] = knowledge

    responses = interpreter.execute("product_query", ctx)

    # 期望由知识库驱动，出现 MacBook Air 以及配置描述
    assert any("MacBook Air" in r for r in responses)
    assert any("13.6寸" in r for r in responses)


if __name__ == "__main__":
    print("🚀 开始记忆功能测试套件...")

    try:
        test_enhanced_context()
        test_product_knowledge()
        test_dsl_memory_rules()
        test_memory_integration()
        test_scenario_simulation()

        print("\n🎊 所有记忆功能测试通过！系统准备就绪。")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()