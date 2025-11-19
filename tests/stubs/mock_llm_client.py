"""
LLM客户端测试桩 (Mock LLM Client Stub)

目的：
1. 模拟SparkLLMClient的API调用，避免实际调用外部API
2. 返回预设的意图识别结果，使测试结果可控可复现
3. 支持测试各种场景，包括正常情况和异常情况

设计：
- 实现与SparkLLMClient相同的接口（ILLMClient）
- 使用规则映射和关键词匹配返回预设意图
- 支持自定义返回结果用于特定测试场景
- 记录所有调用历史便于测试验证
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.interfaces import ILLMClient
from typing import Dict, Any, Optional, List


class MockLLMClient(ILLMClient):
    """
    LLM客户端测试桩
    
    模拟SparkLLMClient的行为，但不实际调用外部API。
    使用预定义的规则和关键词映射返回意图。
    """
    
    def __init__(self, fail_mode: bool = False, custom_responses: Dict[str, str] = None):
        """
        初始化Mock LLM客户端
        
        Args:
            fail_mode: 是否模拟API失败（用于测试错误处理）
            custom_responses: 自定义响应映射 {用户输入: 意图名称}
        """
        self.fail_mode = fail_mode
        self.custom_responses = custom_responses or {}
        self.call_history = []  # 记录所有调用历史
        
        # 预定义的关键词映射规则
        self.keyword_mapping = {
            'greeting': ['你好', '您好', 'hello', 'hi', '早上好', '下午好', '晚上好', '嗨'],
            'product_query': [
                '产品', '商品', '买', '购买', '价格', '多少钱', '有什么', '推荐', '型号',
                '电脑', '手机', '笔记本', '苹果', '联想', '戴尔', 'mac', 'iphone',
                'air', 'pro', '配置', '存储', '颜色', '芯片', '尺寸',
                '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'  # 数字选项
            ],
            'order_status': ['订单', '物流', '发货', '到哪里', '状态', '跟踪', '配送', '快递'],
            'complaint': ['投诉', '抱怨', '不满意', '问题', '故障', '坏了', '质量', '差'],
            'cart_operation': [
                '购物车', '加入', '结算', '下单', '付款', '车', '重置', '清空',
                '还是买', '换个', '不要', '取消'
            ],
            'confirmation': [
                '是', '是的', '好的', '可以', '行', '没问题', '确定', '要',
                '不', '不要', '不用', '否', '不是', '不需要', '再看看'
            ],
            'dining_query': [
                '订餐', '预定', '预订', '订位', '包间', '餐厅', '吃饭', '就餐',
                '火锅', '川菜', '粤菜', '西餐', '日料', '海底捞', '星巴克'
            ],
            'help': ['帮助', 'help', '怎么用', '使用说明', '功能'],
        }
    
    def detect_intent(
        self, 
        user_input: str, 
        available_intents: Dict[str, str], 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        模拟意图识别
        
        Args:
            user_input: 用户输入文本
            available_intents: 可用意图字典 {意图名: 描述}
            context: 对话上下文（可选）
        
        Returns:
            识别到的意图名称，如果无法识别则返回'unknown'
        """
        # 记录调用历史
        self.call_history.append({
            'user_input': user_input,
            'available_intents': list(available_intents.keys()),
            'context': context
        })
        
        # 模拟API失败
        if self.fail_mode:
            raise Exception("Mock LLM API failure")
        
        # 检查自定义响应
        if user_input in self.custom_responses:
            return self.custom_responses[user_input]
        
        # 使用关键词匹配
        detected_intent = self._match_by_keywords(user_input, available_intents, context)
        
        return detected_intent
    
    def _match_by_keywords(
        self, 
        user_input: str, 
        available_intents: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        基于关键词匹配识别意图
        
        Args:
            user_input: 用户输入
            available_intents: 可用意图
            context: 上下文信息
        
        Returns:
            匹配的意图名称
        """
        user_input_lower = user_input.lower().strip()
        
        # 特殊处理：简单确认词在特定阶段返回confirmation
        simple_confirm_words = ['是', '是的', '好的', '可以', '行', '不', '不要', '不用', '否', '不是']
        if user_input_lower in simple_confirm_words and context:
            stage = context.get("current_stage", "")
            cart_related_stages = {"completed", "cart_added", "viewing_cart", "checkout"}
            if stage in cart_related_stages and "confirmation" in available_intents:
                return "confirmation"
        
        # 遍历关键词映射，按优先级匹配
        priority_order = [
            'greeting',           # 问候优先级最高
            'cart_operation',     # 购物车操作
            'confirmation',       # 确认/否定
            'dining_query',       # 餐饮查询
            'product_query',      # 产品查询
            'order_status',       # 订单状态
            'complaint',          # 投诉
            'help'               # 帮助
        ]
        
        for intent in priority_order:
            # 只匹配可用的意图
            if intent not in available_intents:
                continue
            
            keywords = self.keyword_mapping.get(intent, [])
            for keyword in keywords:
                if keyword in user_input_lower:
                    return intent
        
        # 未匹配到任何关键词，返回unknown
        return "unknown"
    
    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self.call_history
    
    def reset_history(self):
        """重置调用历史"""
        self.call_history = []
    
    def set_fail_mode(self, fail: bool):
        """设置失败模式"""
        self.fail_mode = fail
    
    def add_custom_response(self, user_input: str, intent: str):
        """添加自定义响应"""
        self.custom_responses[user_input] = intent
    
    def clear_custom_responses(self):
        """清空自定义响应"""
        self.custom_responses = {}


class ConfigurableMockLLMClient(MockLLMClient):
    """
    可配置的Mock LLM客户端
    
    支持更精细的测试场景配置，如：
    - 按次数返回不同结果
    - 模拟延迟
    - 模拟间歇性失败
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.response_sequence = []  # 按顺序返回的响应列表
        self.current_index = 0
        self.simulate_delay = False
        self.delay_seconds = 0
    
    def set_response_sequence(self, responses: List[str]):
        """
        设置响应序列，按调用顺序依次返回
        
        Args:
            responses: 意图名称列表
        """
        self.response_sequence = responses
        self.current_index = 0
    
    def detect_intent(
        self, 
        user_input: str, 
        available_intents: Dict[str, str], 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """覆盖父类方法，支持序列响应"""
        # 记录调用
        self.call_history.append({
            'user_input': user_input,
            'available_intents': list(available_intents.keys()),
            'context': context
        })
        
        # 模拟延迟
        if self.simulate_delay:
            import time
            time.sleep(self.delay_seconds)
        
        # 如果有响应序列，按序返回
        if self.response_sequence and self.current_index < len(self.response_sequence):
            intent = self.response_sequence[self.current_index]
            self.current_index += 1
            return intent
        
        # 否则使用默认行为
        return super().detect_intent(user_input, available_intents, context)


# 便捷工厂函数
def create_mock_llm_client(scenario: str = "normal") -> MockLLMClient:
    """
    创建预配置的Mock LLM客户端
    
    Args:
        scenario: 测试场景名称
            - "normal": 正常工作模式
            - "failure": 模拟API失败
            - "custom": 返回空客户端，需自行配置
    
    Returns:
        配置好的MockLLMClient实例
    """
    scenarios = {
        "normal": MockLLMClient(fail_mode=False),
        "failure": MockLLMClient(fail_mode=True),
        "custom": MockLLMClient()
    }
    
    return scenarios.get(scenario, MockLLMClient())