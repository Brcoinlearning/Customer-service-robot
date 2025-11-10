from core.interfaces import IInterpreter
from typing import Dict, List, Any


class DSLInterpreter(IInterpreter):
    """支持记忆上下文的 DSL 解释器"""

    def __init__(self, parsed_dsl: Dict[str, Any]):
        self.intents = parsed_dsl["intents"]
        self.rules = parsed_dsl["rules"]

    def execute(self, detected_intent: str, context: Dict[str, Any] = None) -> List[str]:
        """根据意图和上下文执行规则"""

        responses: List[str] = []
        context = context or {}
        user_input = context.get("user_input", "").strip()

        # 智能处理数字选项：基于上下文修正意图
        if user_input in ['1', '2', '3', '4', '5']:
            current_stage = context.get('current_stage', '')
            print(f"检测到数字选项 '{user_input}'，当前阶段: {current_stage}")
            
            # 只在购物车相关阶段，才将数字选项修正为cart_operation
            # 在产品选择阶段，保持为product_query
            if current_stage in ['cart_added', 'viewing_cart', 'checkout']:
                if detected_intent == "product_query":
                    print("购物车阶段：修正意图: product_query → cart_operation")
                    detected_intent = "cart_operation"
            else:
                # 在产品选择阶段，确保数字选项保持为product_query
                if detected_intent != "product_query":
                    print(f"产品选择阶段：确保数字选项意图为product_query")
                    detected_intent = "product_query"

        # 原有的确认词处理
        if detected_intent == "product_query" and user_input in ['是', '是的', '好的', '可以', '行']:
            print("检测到确认词，将意图从product_query改为confirmation")
            detected_intent = "confirmation"

        # 规则匹配
        for rule in self.rules:
            if self._match_rule(rule, detected_intent, context):
                print(f"匹配规则: {rule['name']}")
                rule_responses = self._execute_actions(rule["actions"], context)
                responses.extend(rule_responses)
                break

        if not responses:
            responses.append("抱歉，我没有理解您的问题。请您重新描述。")

        return responses
    
    def _match_rule(self, rule: Dict, detected_intent: str, context: Dict[str, Any]) -> bool:
        """检查规则是否匹配，支持意图和上下文条件"""
        
        """print(f"正在匹配规则: {rule['name']}")"""
        """print(f"当前上下文: {context}")"""

        for condition in rule["conditions"]:
            ctype = condition["type"]
            print(f"检查条件: {ctype} - {condition}")

            if ctype == "intent":
                if condition.get("intent_name") != detected_intent:
                    """print(f"意图不匹配: 期望{condition.get('intent_name')}, 实际{detected_intent}")"""
                    return False

            elif ctype == "user_mention":
                user_text = context.get("user_input", "")
                keyword = condition.get("keyword", "")
                if keyword and keyword not in user_text:
                    """print(f"关键词不匹配: 期望包含'{keyword}', 实际'{user_text}'")"""
                    return False

            elif ctype == "user_mention_any":
                user_text = context.get("user_input", "").lower()
                keywords = condition.get("keywords", [])
                matched = any(keyword.lower() in user_text for keyword in keywords)
                if not matched:
                    """print(f"任意关键词不匹配: 期望包含{keywords}之一, 实际'{user_text}'")"""
                    return False


            elif ctype == "context_not_set":
                var_name = condition.get("var_name")
                if var_name in context and context.get(var_name) is not None:
                    return False

            elif ctype == "context_eq":
                var_name = condition.get("var_name")
                expected = condition.get("value")
                if context.get(var_name) != expected:
                    return False

            elif ctype == "stage_is":
                stage = context.get("current_stage") or context.get("current_stage")
                expected = condition.get("stage")
                if stage != expected:
                    return False

        return True

    def _execute_actions(self, actions: List[Dict], context: Dict[str, Any]) -> List[str]:
        """执行动作序列，并操作上下文管理器"""

        responses: List[str] = []
        context_manager = context.get("_manager")

        for action in actions:
            atype = action["type"]

            if atype == "respond":
                message = action.get("message", "")
                message = self._replace_variables(message, context)
                responses.append(message)

            elif atype == "set_variable" and context_manager:
                context_manager.update_context(action["var_name"], action["value"])

            elif atype == "set_stage" and context_manager:
                context_manager.set_stage(action["stage"])

            elif atype == "add_to_chain" and context_manager:
                context_manager.add_to_chain(action["item_type"], action["item_value"])

            elif atype == "increment" and context_manager:
                var_name = action["var_name"]
                current_value = context_manager.get_context().get(var_name, 0)
                context_manager.update_context(var_name, current_value + 1)

            elif atype == "record_preference" and context_manager:
                context_manager.record_preference(action["key"], action["value"])

            elif atype == "reset_shopping_context" and context_manager:
                context_manager._reset_context()
                context_manager.set_stage("welcome")

            # 新增：完整重置购物上下文
            elif atype == "reset_shopping_context" and context_manager:
                if hasattr(context_manager, 'reset_shopping_context'):
                    context_manager.reset_shopping_context()
                else:
                    # 后备方案：手动重置关键变量
                    reset_vars = ["current_category", "current_brand", "current_series", "product_chain"]
                    for var in reset_vars:
                        context_manager.update_context(var, None)
                    context_manager.set_stage("welcome")
                    print("⚠️ 使用后备方案重置上下文")

        return responses
    
   
    def _replace_variables(self, message: str, context: Dict[str, Any]) -> str:
        """替换消息中的变量占位符"""

        replacements = {
            "current_category": str(context.get("current_category", "")),
            "current_brand": str(context.get("current_brand", "")),
            "current_series": str(context.get("current_series", "")),
            "query_count": str(context.get("query_count", 0)),
        }

        for var_name, value in replacements.items():
            placeholder = f"${{{var_name}}}"
            message = message.replace(placeholder, value)

        # product_chain 展示
        if "product_chain" in context:
            chain_text = " → ".join(item["value"] for item in context["product_chain"])
            message = message.replace("${product_chain}", chain_text)
        else:
            message = message.replace("${product_chain}", "")

        return message