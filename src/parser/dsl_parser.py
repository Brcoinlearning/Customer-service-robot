from core.interfaces import IDSLParser
import re
from typing import Dict, List, Any

class DSLParser(IDSLParser):  # 改为实现IDSLParser接口
    def __init__(self):
        self.intents = {}
        self.rules = []
    
    def parse(self, dsl_content: str) -> Dict[str, Any]:
        """解析DSL脚本内容 - 实现IDSLParser接口"""
        lines = dsl_content.split('\n')
        current_rule = None
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
                
            # 解析INTENT定义
            if line.startswith('INTENT'):
                self._parse_intent(line, line_num)
            
            # 解析RULE定义
            elif line.startswith('RULE'):
                if current_rule:
                    self.rules.append(current_rule)
                current_rule = self._start_new_rule(line, line_num)
            
            # 解析WHEN条件
            elif line.startswith('WHEN') and current_rule:
                self._parse_when_condition(line, current_rule, line_num)

            # 解析追加的 AND 条件（WHEN 之后，THEN 之前）
            elif line.startswith('AND') and current_rule and not current_rule.get('in_then_section'):
                self._parse_when_condition(line, current_rule, line_num)
            
            # 解析THEN动作
            elif line.startswith('THEN') and current_rule:
                current_rule['in_then_section'] = True
            
            # 解析动作（在THEN部分）
            elif current_rule and current_rule.get('in_then_section'):
                self._parse_action(line, current_rule, line_num)
        
        # 添加最后一个规则
        if current_rule:
            self.rules.append(current_rule)
        
        return {
            'intents': self.intents,
            'rules': self.rules
        }
    
    def _parse_intent(self, line: str, line_num: int):
        """解析INTENT定义"""
        match = re.match(r'INTENT\s+(\w+)\s*:\s*"([^"]+)"', line)
        if match:
            intent_name, description = match.groups()
            self.intents[intent_name] = description
        else:
            raise SyntaxError(f"Line {line_num}: Invalid INTENT format: {line}")
    
    def _start_new_rule(self, line: str, line_num: int) -> Dict[str, Any]:
        """开始解析新的RULE"""
        match = re.match(r'RULE\s+(\w+)', line)
        if match:
            return {
                'name': match.group(1),
                'conditions': [],
                'actions': [],
                'in_then_section': False
            }
        else:
            raise SyntaxError(f"Line {line_num}: Invalid RULE format: {line}")
    
    def _parse_when_condition(self, line: str, current_rule: Dict, line_num: int):
        """解析WHEN条件"""
        # 支持复合条件: WHEN INTENT_IS xxx AND ...
        
        # 处理 INTENT_IS
        if 'INTENT_IS' in line:
            match = re.search(r'INTENT_IS\s+(\w+)', line)
            if match:
                current_rule['conditions'].append({
                    'type': 'intent',
                    'intent_name': match.group(1)
                })

        # 解析 USER_MENTION - 支持多个关键词
        user_mention_match = re.search(r'USER_MENTION\s+"([^"]+)"', line)
        if user_mention_match:
            keywords = user_mention_match.group(1).split('|')
            for keyword in keywords:
                current_rule['conditions'].append({
                    'type': 'user_mention',
                    'keyword': keyword.strip()
                })

        # 解析 USER_MENTION_ANY - 任意一个关键词匹配即可
        user_mention_any_match = re.search(r'USER_MENTION_ANY\s+"([^"]+)"', line)
        if user_mention_any_match:
            keywords = user_mention_any_match.group(1).split('|')
            current_rule['conditions'].append({
                'type': 'user_mention_any',
                'keywords': [k.strip() for k in keywords]
            })

        # 解析 CONTEXT_NOT_SET var
        context_not_set_match = re.search(r'CONTEXT_NOT_SET\s+(\w+)', line)
        if context_not_set_match:
            current_rule['conditions'].append({
                'type': 'context_not_set',
                'var_name': context_not_set_match.group(1)
            })

        # 解析 CONTEXT_HAS "var_name" [= number]
        # 形式一：CONTEXT_HAS "query_count" = 0  （变量存在且值等于给定数字）
        context_has_eq_match = re.search(r'CONTEXT_HAS\s+"([^"]+)"\s*=\s*(\d+)', line)
        if context_has_eq_match:
            var_name, value_str = context_has_eq_match.groups()
            current_rule['conditions'].append({
                'type': 'context_has',
                'var_name': var_name,
                'value': int(value_str)
            })
        else:
            # 形式二：CONTEXT_HAS "current_category"  （变量存在且不为 None）
            context_has_match = re.search(r'CONTEXT_HAS\s+"([^"]+)"', line)
            if context_has_match:
                current_rule['conditions'].append({
                    'type': 'context_has',
                    'var_name': context_has_match.group(1)
                })

        # 解析 CONTEXT_EQ var = "value"
        context_eq_match = re.search(r'CONTEXT_EQ\s+(\w+)\s*=\s*"([^"]+)"', line)
        if context_eq_match:
            current_rule['conditions'].append({
                'type': 'context_eq',
                'var_name': context_eq_match.group(1),
                'value': context_eq_match.group(2)
            })

        # 解析 CONTEXT_STAGE_IS "stage"
        stage_match = re.search(r'CONTEXT_STAGE_IS\s+"([^"]+)"', line)
        if stage_match:
            current_rule['conditions'].append({
                'type': 'stage_is',
                'stage': stage_match.group(1)
            })

    def _parse_action(self, line: str, current_rule: Dict, line_num: int):
        """解析动作"""
        if line.startswith('RESPOND'):
            match = re.match(r'RESPOND\s+"([^"]+)"', line)
            if match:
                current_rule['actions'].append({
                    'type': 'respond',
                    'message': match.group(1)
                })
            else:
                raise SyntaxError(f"Line {line_num}: Invalid RESPOND action: {line}")
        elif line.startswith('RESET_SHOPPING_CONTEXT'):
            current_rule['actions'].append({
                'type': 'reset_shopping_context'
            })
        elif line.startswith('SET_STAGE'):
            match = re.match(r'SET_STAGE\s+"([^"]+)"', line)
            if match:
                current_rule['actions'].append({
                    'type': 'set_stage',
                    'stage': match.group(1)
                })
            else:
                raise SyntaxError(f"Line {line_num}: Invalid SET_STAGE action: {line}")
        elif line.startswith('SET_VAR'):
            # SET_VAR key = "value"
            match = re.match(r'SET_VAR\s+(\w+)\s*=\s*"([^"]+)"', line)
            if match:
                current_rule['actions'].append({
                    'type': 'set_variable',
                    'var_name': match.group(1),
                    'value': match.group(2)
                })
            else:
                raise SyntaxError(f"Line {line_num}: Invalid SET_VAR action: {line}")
        elif line.startswith('ADD_TO_CHAIN'):
            # ADD_TO_CHAIN type = "category" value = "电脑"
            match = re.match(r'ADD_TO_CHAIN\s+type\s*=\s*"([^"]+)"\s+value\s*=\s*"([^"]+)"', line)
            if match:
                current_rule['actions'].append({
                    'type': 'add_to_chain',
                    'item_type': match.group(1),
                    'item_value': match.group(2)
                })
            else:
                # 支持简写语法：ADD_TO_CHAIN "category" "电脑"
                short_match = re.match(r'ADD_TO_CHAIN\s+"([^"]+)"\s+"([^"]+)"', line)
                if short_match:
                    current_rule['actions'].append({
                        'type': 'add_to_chain',
                        'item_type': short_match.group(1),
                        'item_value': short_match.group(2)
                    })
                else:
                    raise SyntaxError(f"Line {line_num}: Invalid ADD_TO_CHAIN action: {line}")  
        elif line.startswith('INCREMENT'):
            match = re.match(r'INCREMENT\s+"([^"]+)"', line)
            if match:
                current_rule['actions'].append({
                    'type': 'increment',
                    'var_name': match.group(1)
                })
            else:
                raise SyntaxError(f"Line {line_num}: Invalid INCREMENT action: {line}")
