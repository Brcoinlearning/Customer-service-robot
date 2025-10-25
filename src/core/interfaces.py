# src/core/interfaces.py
"""
DSL解释器核心接口定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any

class IDSLParser(ABC):
    """DSL解析器接口"""
    
    @abstractmethod
    def parse(self, dsl_content: str) -> Dict[str, Any]:
        """解析DSL脚本内容"""
        pass

class IInterpreter(ABC):
    """解释执行器接口"""
    
    @abstractmethod
    def execute(self, detected_intent: str, context: Dict[str, Any] = None) -> List[str]:
        """根据意图执行相应的规则"""
        pass

class ILLMClient(ABC):
    """LLM客户端接口"""
    
    @abstractmethod
    def detect_intent(self, user_input: str, available_intents: Dict[str, str]) -> str:
        """使用LLM检测用户输入的意图"""
        pass

class IContextManager(ABC):
    """对话上下文管理器接口"""
    
    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        """获取当前对话上下文"""
        pass
    
    @abstractmethod
    def update_context(self, key: str, value: Any):
        """更新对话上下文"""
        pass