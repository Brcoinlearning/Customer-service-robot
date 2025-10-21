# tests/test_parser.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from parser.dsl_parser import DSLParser

def test_parser():
    """测试DSL解析器"""
    test_dsl = """
INTENT greeting: "问候"
INTENT help: "帮助"

RULE test_rule
WHEN INTENT_IS greeting
THEN
    RESPOND "Hello"
    RESPOND "How can I help you?"
"""
    
    parser = DSLParser()
    result = parser.parse(test_dsl)
    
    print("解析结果:")
    print(f"意图: {result['intents']}")
    print(f"规则数量: {len(result['rules'])}")
    
    for rule in result['rules']:
        print(f"规则 '{rule['name']}':")
        print(f"  条件: {rule['conditions']}")
        print(f"  动作: {rule['actions']}")

if __name__ == "__main__":
    test_parser()