from core.interfaces import ILLMClient
import json
import requests
from typing import List, Dict
import time

class SparkLLMClient(ILLMClient):  # 已正确实现接口
    def __init__(self, api_key: str, api_url: str = None, model: str = None):
        self.api_key = api_key
        self.url = api_url if api_url else "https://spark-api-open.xf-yun.com/v1/chat/completions"
        self.model = model if model else "lite"
    
    def detect_intent(self, user_input: str, available_intents: Dict[str, str]) -> str:
        """使用LLM检测用户输入的意图 - 实现ILLMClient接口"""
        
        # 构建意图识别提示词 - 简化提示，强调只返回名称
        intent_list = list(available_intents.keys())
        intent_names = ", ".join(intent_list)
        
        prompt = f"""你是一个严格的意图分类器。请分析用户输入并只返回最匹配的意图名称。

可用意图名称: {intent_names}

用户输入: "{user_input}"

要求:
1. 只返回意图名称，不要任何其他文字
2. 如果不匹配任何意图，返回 "unknown"
3. 不要解释，不要示例，不要额外内容

直接返回意图名称:"""

        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            print("调用LLM API进行意图识别...")
            response = self._call_api(messages)
            detected_intent = response.strip()
            print(f"LLM返回原始内容: '{detected_intent}'")
            
            # 清理响应：移除可能的引号和其他字符
            detected_intent = self._clean_intent_response(detected_intent)
            print(f"清理后意图: '{detected_intent}'")
            
            # 验证返回的意图是否在预定义列表中
            if detected_intent in available_intents:
                return detected_intent
            else:
                print(f"意图 '{detected_intent}' 不在预定义列表中，返回 'unknown'")
                return "unknown"
                
        except Exception as e:
            print(f"LLM API调用失败: {e}")
            # 降级处理：使用关键词匹配
            return self._fallback_intent_detection(user_input, available_intents)
    
    def _clean_intent_response(self, intent_response: str) -> str:
        """清理LLM返回的意图响应"""
        # 移除可能的引号
        intent_response = intent_response.replace('"', '').replace("'", "")
        # 移除可能的"返回"等前缀
        if "返回" in intent_response:
            # 提取最后一个单词
            parts = intent_response.split()
            if parts:
                intent_response = parts[-1]
        # 移除可能的标点符号
        intent_response = intent_response.strip(' .。!！?？')
        return intent_response
    
    def _call_api(self, messages: List[Dict]) -> str:
        """调用星火API"""
        headers = {
            'Authorization': self.api_key,
            'content-type': "application/json"
        }
        body = {
            "model": self.model,  # 使用配置的model，而不是硬编码"lite"
            "user": "user_id",
            "messages": messages,
            "stream": False,
            "temperature": 0.1,
            "max_tokens": 10
        }
        
        response = requests.post(url=self.url, json=body, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            raise Exception(f"API调用错误: {response.status_code}, {response.text}")
    
    def _fallback_intent_detection(self, user_input: str, available_intents: Dict[str, str]) -> str:
        """降级意图识别：当API调用失败时使用关键词匹配"""
        user_input_lower = user_input.lower()
        
        keyword_mapping = {
            'greeting': ['你好', '您好', 'hello', 'hi', '早上好', '下午好', '晚上好', '嗨'],
            'product_query': ['产品', '商品', '买', '购买', '价格', '多少钱', '有什么', '推荐', '型号'],
            'order_status': ['订单', '物流', '发货', '到哪里', '状态', '跟踪', '配送', '快递'],
            'complaint': ['投诉', '抱怨', '不满意', '问题', '故障', '坏了', '质量', '差']
        }
        
        print("使用关键词匹配进行意图识别...")
        for intent, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    print(f"关键词匹配: '{keyword}' -> {intent}")
                    return intent
        
        print("未找到匹配关键词，返回 'unknown'")
        return "unknown"