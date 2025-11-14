from core.interfaces import ILLMClient
import json
import requests
from typing import List, Dict, Any, Optional
import time

class SparkLLMClient(ILLMClient):  # 已正确实现接口
    def __init__(self, api_key: str, api_url: str = None, model: str = None):
        self.api_key = api_key
        self.url = api_url if api_url else "https://spark-api-open.xf-yun.com/v1/chat/completions"
        self.model = model if model else "lite"

    def detect_intent(self, user_input: str, available_intents: Dict[str, str], context: Optional[Dict[str, Any]] = None) -> str:
        """使用LLM检测用户输入的意图 - 实现ILLMClient接口

        上下文信息（当前阶段、已选产品链、最近几条对话）将被用作提示词的一部分，
        以帮助 LLM 更好地理解“继续”“好的”等模糊表达在当前场景下的含义。
        """

        # 首先进行简单关键词匹配，处理明确的确认/否定词
        simple_words = ['是', '是的', '好的', '可以', '行', '不', '不要', '不用', '否', '不是']
        stripped = user_input.strip()
        if stripped in simple_words:
            # 仅在订单/购物车相关阶段，才将简单确认/否定词直接映射为 confirmation
            stage = None
            if context and isinstance(context, dict):
                stage = context.get("current_stage")
            cart_related_stages = {"completed", "cart_added", "viewing_cart", "checkout"}
            if stage in cart_related_stages:
                print("检测到购物流程中的简单确认/否定词，直接返回confirmation意图")
                return "confirmation"

        # 注意：这里不再处理数字选项，交给解释器根据上下文处理
        # 因为数字选项的意图取决于当前对话阶段

        # 构造上下文摘要，帮助 LLM 更好地理解当前所处步骤
        context_summary = ""
        if context:
            context_summary = self._build_context_summary(context)

        # 原有的LLM识别逻辑...
        intent_list = list(available_intents.keys())
        intent_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in available_intents.items()])

        prompt = f"""你是一个客服意图分类器。请分析用户输入并返回最匹配的意图名称。

    可用意图：
    {intent_descriptions}

    当前对话上下文（仅用于帮助你理解用户输入的含义）：
    {context_summary}

    用户输入: "{user_input}"

    重要规则：
    1. 如果用户提到购买、产品、电脑、手机、价格、配置等，返回 product_query
    2. 如果用户说"你好"、"您好"等问候语，返回 greeting
    3. 如果用户询问订单、物流、发货状态，返回 order_status
    4. 如果用户表达不满、投诉、问题，返回 complaint
    5. 如果用户提到购物车、加入、结算、下单等，返回 cart_operation
    6. 如果用户说简单的确认词（是、是的、好的、可以、行、没问题、确定、加入、要）或否定词（不、不要、不用、否、不是），返回 confirmation
    7. 对于数字选项（1、2、3等），如果在产品选择上下文中返回 product_query
    8. 只返回意图名称，不要其他内容

    意图名称:"""

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
            "model": "lite",
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

    def _build_context_summary(self, context: Dict) -> str:
        """将对话上下文整理为简短的文本摘要，供 LLM 参考"""
        try:
            stage = context.get("current_stage", "未知阶段")
            category = context.get("current_category") or "未选择"
            subtype = context.get("current_subtype") or "未选择"
            brand = context.get("current_brand") or "未选择"
            series = context.get("current_series") or "未选择"

            # 产品选择链展示
            chain = context.get("product_chain") or []
            if chain:
                chain_text = " -> ".join(item.get("value", "") for item in chain)
            else:
                chain_text = "暂无"

            # 最近几条对话
            history = context.get("conversation_history") or []
            recent = history[-3:]
            history_lines = []
            for msg in recent:
                role = msg.get("role")
                role_cn = "用户" if role == "user" else "客服" if role == "assistant" else str(role)
                content = str(msg.get("content", ""))
                history_lines.append(f"- {role_cn}: {content}")

            history_block = "\n".join(history_lines) if history_lines else "(无最近对话记录)"

            summary = (
                f"当前对话阶段: {stage}\n"
                f"当前已选产品链: {chain_text}\n"
                f"当前选择: 品类={category} 子类={subtype} 品牌={brand} 系列={series}\n"
                f"最近几条对话:\n{history_block}"
            )
            return summary
        except Exception as e:
            # 为防止上下文结构异常导致 LLM 调用失败，出现异常时退回空摘要
            print(f"构造上下文摘要时出错: {e}")
            return "(上下文信息暂不可用)"

    def _fallback_intent_detection(self, user_input: str, available_intents: Dict[str, str]) -> str:
        """降级意图识别：当API调用失败时使用关键词匹配"""
        user_input_lower = user_input.lower()

        keyword_mapping = {
            'greeting': ['你好', '您好', 'hello', 'hi', '早上好', '下午好', '晚上好', '嗨'],
            'product_query': ['产品', '商品', '买', '购买', '价格', '多少钱', '有什么', '推荐', '型号', '电脑', '手机', '笔记本', '苹果', '联想', '戴尔'],
            'order_status': ['订单', '物流', '发货', '到哪里', '状态', '跟踪', '配送', '快递'],
            'complaint': ['投诉', '抱怨', '不满意', '问题', '故障', '坏了', '质量', '差'],
            'cart_operation': ['购物车', '加入', '结算', '下单', '购买', '付款', '车'],
            'confirmation': ['是', '是的', '好的', '可以', '行', '没问题', '确定', '加入', '要',
                            '不', '不要', '不用', '否', '不是', '不需要', '再看看']  # 增强确认词列表
        }

        print("使用关键词匹配进行意图识别...")
        for intent, keywords in keyword_mapping.items():
            # 检查意图是否在可用意图中（避免识别到DSL中不存在的意图）
            if intent in available_intents:
                for keyword in keywords:
                    if keyword in user_input_lower:
                        print(f"关键词匹配: '{keyword}' -> {intent}")
                        return intent

        print("未找到匹配关键词，返回 'unknown'")
        return "unknown"