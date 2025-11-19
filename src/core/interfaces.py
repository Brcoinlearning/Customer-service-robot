# src/core/interfaces.py
"""
表单系统核心接口定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SlotSpec:
    """槽位规格定义"""
    name: str
    required: bool
    description: str
    dependencies: List[str] = field(default_factory=list)
    enums_key: Optional[str] = None
    semantic_stage: Optional[str] = None
    allow_llm: bool = True


class ILLMClient(ABC):
    """LLM客户端接口"""

    @abstractmethod
    def detect_intent(self, user_input: str, available_intents: Dict[str, str], context: Optional[Dict[str, Any]] = None) -> str:
        """使用LLM检测用户输入的意图，允许可选的上下文信息参与提示词构造"""
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