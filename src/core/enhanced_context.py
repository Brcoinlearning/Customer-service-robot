from typing import Dict, List, Any, Optional
from .interfaces import IContextManager
import time

class EnhancedConversationContext(IContextManager):
    """增强版对话上下文管理器"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or f"user_{int(time.time())}"
        self._reset_context()
    
    def _reset_context(self):
        """重置上下文"""
        self._context = {
            # 用户标识
            "user_id": self.user_id,
            "start_time": time.time(),
            
            # 对话状态
            "current_stage": "welcome",
            "state_history": ["welcome"],
            
            # 产品选择链
            "product_chain": [],
            "current_category": None,
            "current_subtype": None,
            "current_brand": None,
            "current_series": None,
            
            # 用户偏好
            "user_preferences": {},
            "budget_range": None,
            "usage_scenario": None,
            
            # 对话记忆
            "conversation_history": [],
            "mentioned_products": [],
            "query_count": 0
        }
    
    def get_context(self) -> Dict[str, Any]:
        return self._context.copy()
    
    def update_context(self, key: str, value: Any):
        """更新上下文"""
        if key in self._context:
            self._context[key] = value
        else:
            self._context.setdefault("session_variables", {})[key] = value
    
    def add_to_chain(self, item_type: str, item_value: str):
        """添加到产品选择链"""
        chain_item = {
            "type": item_type,
            "value": item_value,
            "timestamp": time.time()
        }
        hierarchy = {
            "category": 0,
            "subtype": 1,
            "brand": 2,
            "series": 3
        }

        level = hierarchy.get(item_type, 99)
        filtered_chain = []
        for item in self._context["product_chain"]:
            if hierarchy.get(item["type"], 99) < level:
                filtered_chain.append(item)

        self._context["product_chain"] = filtered_chain
        self._context["product_chain"].append(chain_item)
        self._recalculate_current_choices()
    
    def get_current_chain(self) -> List[Dict]:
        """获取当前选择链"""
        return self._context["product_chain"].copy()
    
    def get_last_choice(self) -> Optional[Dict]:
        """获取最后的选择"""
        if self._context["product_chain"]:
            return self._context["product_chain"][-1]
        return None
    
    def rollback_chain(self, steps: int = 1):
        """回退选择链"""
        if steps >= len(self._context["product_chain"]):
            self._context["product_chain"] = []
            self._context["current_category"] = None
            self._context["current_subtype"] = None
            self._context["current_brand"] = None
            self._context["current_series"] = None
        else:
            # 回退指定步数
            self._context["product_chain"] = self._context["product_chain"][:-steps]
            # 重新计算当前选择
            self._recalculate_current_choices()
    
    def _recalculate_current_choices(self):
        """根据选择链重新计算当前选择"""
        self._context["current_category"] = None
        self._context["current_subtype"] = None
        self._context["current_brand"] = None
        self._context["current_series"] = None
        
        for item in self._context["product_chain"]:
            if item["type"] == "category":
                self._context["current_category"] = item["value"]
            elif item["type"] == "subtype":
                self._context["current_subtype"] = item["value"]
            elif item["type"] == "brand":
                self._context["current_brand"] = item["value"]
            elif item["type"] == "series":
                self._context["current_series"] = item["value"]
    
    def set_stage(self, stage: str):
        """设置对话阶段"""
        self._context["current_stage"] = stage
        self._context["state_history"].append(stage)
    
    def get_stage(self) -> str:
        """获取当前阶段"""
        return self._context["current_stage"]
    
    def add_message(self, role: str, content: str):
        """添加对话消息"""
        self._context["conversation_history"].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        # 保持最近20条记录
        if len(self._context["conversation_history"]) > 20:
            self._context["conversation_history"].pop(0)
    
    def record_preference(self, key: str, value: Any):
        """记录用户偏好"""
        self._context["user_preferences"][key] = value
    
    def increment_query_count(self):
        """增加查询计数"""
        self._context["query_count"] += 1
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要"""
        return {
            "user_id": self.user_id,
            "duration": time.time() - self._context["start_time"],
            "message_count": len(self._context["conversation_history"]),
            "current_stage": self._context["current_stage"],
            "product_chain_length": len(self._context["product_chain"]),
            "query_count": self._context["query_count"],
            "current_selection": {
                "category": self._context["current_category"],
                "subtype": self._context["current_subtype"],
                "brand": self._context["current_brand"],
                "series": self._context["current_series"]
            }
        }

    def reset_shopping_context(self):
        """完整重置购物上下文，回到初始状态"""
        # 保留基本的用户信息和对话历史
        user_id = self._context["user_id"]
        start_time = self._context["start_time"]
        conversation_history = self._context["conversation_history"]
        query_count = self._context["query_count"]
        
        # 完整重置购物上下文
        self._context = {
            # 用户标识
            "user_id": user_id,
            "start_time": start_time,
            
            # 对话状态 - 重置为welcome
            "current_stage": "welcome",
            "state_history": ["welcome"],
            
            # 产品选择链 - 完全清空
            "product_chain": [],
            "current_category": None,
            "current_subtype": None,
            "current_brand": None,
            "current_series": None,
            
            # 用户偏好 - 重置
            "user_preferences": {},
            "budget_range": None,
            "usage_scenario": None,
            
            # 对话记忆 - 保留历史但清空提及产品
            "conversation_history": conversation_history,
            "mentioned_products": [],
            "query_count": query_count
        }
        print("✅ 购物上下文已重置")