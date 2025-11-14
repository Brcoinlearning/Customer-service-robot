# src/core/interfaces.py
"""
DSL解释器核心接口定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

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
    def detect_intent(self, user_input: str, available_intents: Dict[str, str], context: Optional[Dict[str, Any]] = None) -> str:
        """使用LLM检测用户输入的意图，允许可选的上下文信息参与提示词构造"""
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

class IKnowledgeProvider(ABC):
    """知识提供者接口，用于不同业务域的数据与模板输出"""

    @abstractmethod
    def get_brands_in_category(self, category: str) -> List[str]:
        pass

    @abstractmethod
    def get_series_in_brand(self, category: str, brand: str) -> List[str]:
        pass

    @abstractmethod
    def get_series_configs(self, category: str, brand: str, series_name: str) -> List[str]:
        pass

    @abstractmethod
    def get_template(self, key: str) -> List[str]:
        pass

    @abstractmethod
    def canonicalize(self, kind: str, term: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_recommendations_by_scenario(self, category: str, scenario: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def infer_category_for_brand(self, brand: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_default_brand_for_category(self, category: str) -> Optional[str]:
        pass

    @abstractmethod
    def filter_series_by_subtype(self, category: str, subtype: Optional[str], series_list: List[str]) -> List[str]:
        pass