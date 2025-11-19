from core.interfaces import ILLMClient
import json
import requests
import os
from typing import List, Dict, Any, Optional
import time
from core.slot_specs import SLOT_CANDIDATES

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

        prompt = f"""你是一个智能客服意图分类器。请根据用户输入和对话上下文，判断最匹配的意图。

    可用意图：
    {intent_descriptions}

    当前对话上下文（帮助你理解用户输入的含义）：
    {context_summary}

    用户输入: "{user_input}"

    分类规则：
    1. 问候语（你好、您好、早上好等）→ greeting
    2. 咨询业务相关信息（商品、服务、价格、细节等）→ product_query  
    3. 查询订单状态（订单、物流、进度等）→ order_status
    4. 表达不满或投诉（问题、故障、投诉等）→ complaint
    5. 购物车操作（加入、结算、下单等）→ cart_operation
    6. 明确的确认/否定词（是、好的、不要等）→ confirmation
    7. 数字选项（1、2、3等），根据上下文判断意图
    8. 只返回意图名称，不要解释

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
        """调用星火API - 用于意图检测"""
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
            "max_tokens": 10  # 意图检测只需要短回复
        }

        response = requests.post(url=self.url, json=body, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            raise Exception(f"API调用错误: {response.status_code}, {response.text}")

    def _call_extraction_api(self, messages: List[Dict]) -> str:
        """调用星火API - 用于槽位抽取"""
        headers = {
            'Authorization': self.api_key,
            'content-type': "application/json"
        }
        body = {
            "model": "lite",  # 保持使用 lite 模型，但优化提示词
            "user": "user_id",
            "messages": messages,
            "stream": False,
            "temperature": 0.1,
            "max_tokens": 1024  # 增加输出空间
        }

        response = requests.post(url=self.url, json=body, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            # 显示完整回复用于调试
            if len(content) > 200:
                print(f"🤖 LLM原始回复（截取前200字）: {content[:200]}...")
                print(f"📏 完整回复长度: {len(content)} 字符")
            else:
                print(f"🤖 LLM原始回复: {content}")
            return content
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

        # 通用关键词映射（适用于多种业务场景）
        keyword_mapping = {
            'greeting': ['你好', '您好', 'hello', 'hi', '早上好', '下午好', '晚上好', '嗨'],
            'product_query': ['产品', '商品', '买', '购买', '价格', '多少钱', '有什么', '推荐', '想要', '咨询', '了解', '查看'],
            'order_status': ['订单', '物流', '发货', '到哪里', '状态', '跟踪', '配送', '快递', '进度'],
            'complaint': ['投诉', '抱怨', '不满意', '问题', '故障', '坏了', '质量', '差', '太慢', '不好'],
            'cart_operation': ['购物车', '加入', '结算', '下单', '购买', '付款', '车', '确认订单'],
            'confirmation': ['是', '是的', '好的', '可以', '行', '没问题', '确定', '加入', '要',
                            '不', '不要', '不用', '否', '不是', '不需要', '再看看', '继续']  # 通用确认/否定词
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

    # ---------------- 多槽位抽取（LLM层） -----------------
    def extract_slots(self, user_input: str, business_line: str, target_slots: List[str], current_values: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """增强的LLM多槽位抽取 - 更好地同时识别多个信息项"""
        if not user_input or not target_slots:
            return {}
        
        # 从新的业务配置加载器获取候选值
        try:
            from knowledge.business_config_loader import business_config_loader
            all_enums = business_config_loader.get_all_enums()
            business_config = business_config_loader.get_business_config(business_line)
            slot_specs = business_config.slot_specs if business_config else []
        except Exception as e:
            candidates = SLOT_CANDIDATES.get(business_line, {})
            all_enums = {}
            slot_specs = []
        
        # 构建所有槽位的完整信息（包括未请求的槽位，供LLM主动推断）
        all_slot_info = []
        for slot_spec in slot_specs:
            if slot_spec.enums_key:
                # 拼接业务前缀获取枚举选项
                enum_key_full = f"{business_line}.{slot_spec.enums_key}"
                enum_options = all_enums.get(enum_key_full, [])
                if enum_options:
                    options = [opt.get('label', '') for opt in enum_options if opt.get('label')]
                    all_slot_info.append(f"- {slot_spec.name} ({slot_spec.description}): 标准选项 {', '.join(options)}")
                else:
                    all_slot_info.append(f"- {slot_spec.name} ({slot_spec.description})")
            else:
                all_slot_info.append(f"- {slot_spec.name} ({slot_spec.description}): 自由文本")
        
        current_summary = "无" if not current_values else ", ".join(f"{k}={v}" for k, v in current_values.items() if v)
        
        # 优化的提示词，明确禁止返回槽位描述
        prompt = f"""分析输入，提取信息。值必须匹配标准选项。

业务: {business_line}
槽位:
{chr(10).join(all_slot_info)}

已知: {current_summary}
输入: "{user_input}"

要求：
1. 值必须精确匹配标准选项中的具体值（如"MacBook Pro"、"M3"）
2. 严禁返回槽位描述本身（如"处理器芯片"、"存储容量"等）
3. 无法识别时value设为空字符串""
4. 可推断相关槽位（如"MacBook"可推断category/brand）
5. 置信度：明确=0.9, 推断=0.75
6. reason仅1-2字

JSON（无代码块标记）:
{{"series":{{"value":"MacBook Pro","confidence":0.9,"reason":"明确"}},"chip":{{"value":"","confidence":0.5,"reason":"未提及"}}}}"""
        messages = [{"role": "user", "content": prompt}]
        try:
            raw = self._call_extraction_api(messages)
            text = raw.strip()
            
            # 清理文本格式
            if text.startswith("```"):
                # 去除代码块包装
                lines = text.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_json = not in_json
                        continue
                    if in_json or line.strip().startswith("{"):
                        json_lines.append(line)
                text = '\n'.join(json_lines)
            
            # 查找 JSON 主体
            if not text.strip().startswith("{"):
                brace = text.find("{")
                if brace >= 0:
                    text = text[brace:]
                else:
                    print(f"🤖 无法找到JSON格式，原始回复: {raw}")
                    return {}
            
            # 尝试解析JSON
            try:
                result_obj = json.loads(text.strip())
            except json.JSONDecodeError as e:
                print(f"🤖 JSON解析失败: {e}")
                print(f"🤖 尝试解析的文本: {text[:200]}")
                # 检查是否是因为截断导致的
                if len(raw) > 700:
                    print(f"⚠️ LLM输出可能被截断（长度: {len(raw)}），建议增加 max_tokens")
                return {}
            cleaned: Dict[str, Dict[str, Any]] = {}
            for slot, info in result_obj.items():
                if not isinstance(info, dict):
                    continue
                val = info.get("value")
                conf = info.get("confidence", 0)
                if isinstance(val, str) and isinstance(conf, (int, float)) and 0 <= conf <= 1:
                    if conf < 0.35:  # 低置信度忽略
                        continue
                    reason = info.get("reason") or "llm"
                    cleaned[slot] = {"value": val.strip(), "confidence": float(conf), "reason": reason}
            return cleaned
        except Exception:
            return {}