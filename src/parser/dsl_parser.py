# src/parser/dsl_parser.py
import re
from typing import Dict, List, Any

class DSLParser:
    def __init__(self):
        self.intents = {}
        self.rules = []
    
    def parse(self, dsl_content: str) -> Dict[str, Any]:
        """解析DSL脚本内容"""
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
        if 'INTENT_IS' in line:
            match = re.search(r'INTENT_IS\s+(\w+)', line)
            if match:
                current_rule['conditions'].append({
                    'type': 'intent',
                    'intent_name': match.group(1)
                })
            else:
                raise SyntaxError(f"Line {line_num}: Invalid INTENT_IS condition: {line}")
    
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