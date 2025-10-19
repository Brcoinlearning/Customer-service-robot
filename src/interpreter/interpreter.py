# src/interpreter/interpreter.py
from typing import Dict, List, Any

class DSLInterpreter:
    def __init__(self, parsed_dsl: Dict[str, Any]):
        self.intents = parsed_dsl['intents']
        self.rules = parsed_dsl['rules']
    
    def execute(self, detected_intent: str) -> List[str]:
        """根据检测到的意图执行相应的规则"""
        responses = []
        
        for rule in self.rules:
            if self._match_rule(rule, detected_intent):
                print(f"匹配规则: {rule['name']}")
                responses.extend(self._execute_actions(rule['actions']))
                break  # 只执行第一个匹配的规则
        
        # 如果没有规则匹配，使用默认规则
        if not responses:
            print("未匹配任何规则，使用默认响应")
            responses.append("抱歉，我没有理解您的问题。请您重新描述。")
        
        return responses
    
    def _match_rule(self, rule: Dict, detected_intent: str) -> bool:
        """检查规则是否匹配"""
        for condition in rule['conditions']:
            if condition['type'] == 'intent':
                if condition['intent_name'] == detected_intent:
                    return True
        return False
    
    def _execute_actions(self, actions: List[Dict]) -> List[str]:
        """执行动作序列"""
        responses = []
        for action in actions:
            if action['type'] == 'respond':
                responses.append(action['message'])
        return responses