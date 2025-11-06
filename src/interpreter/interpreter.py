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

        # 没有条件时不匹配，避免误触发
        if not rule.get("conditions"):
            return False

        for condition in rule["conditions"]:
            ctype = condition["type"]

            if ctype == "intent":
                if condition.get("intent_name") != detected_intent:
                    return False

            elif ctype == "user_mention":
                user_text = context.get("user_input", "")
                keyword = condition.get("keyword", "")
                if keyword and keyword not in user_text:
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