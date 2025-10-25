"""
对话上下文管理
"""

from typing import Dict, Any
from .interfaces import IContextManager

class ConversationContext(IContextManager):
    """对话上下文管理器"""
    
    def __init__(self):
        self._context: Dict[str, Any] = {
            "user_id": None,
            "conversation_history": [],
            "current_intent": None,
            "variables": {}
        }
    
    def get_context(self) -> Dict[str, Any]:
        """获取当前对话上下文"""
        return self._context.copy()
    
    def update_context(self, key: str, value: Any):
        """更新对话上下文"""
        if key in self._context:
            self._context[key] = value
        else:
            self._context["variables"][key] = value
    
    def add_message(self, role: str, content: str):
        """添加对话消息到历史"""
        self._context["conversation_history"].append({
            "role": role,
            "content": content
        })
        # 保持历史记录不超过最大长度
        if len(self._context["conversation_history"]) > 10:
            self._context["conversation_history"].pop(0)