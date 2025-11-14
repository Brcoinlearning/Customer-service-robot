from typing import Dict, List, Any, Optional
import os
import json

from core.interfaces import IKnowledgeProvider

class DiningKnowledgeProvider(IKnowledgeProvider):
    def __init__(self):
        self.categories = self._initialize_categories()
        self.response_templates = self._initialize_response_templates()
        self.aliases = self._initialize_aliases()
        self._load_external_templates()
        self._load_external_aliases()

    def _initialize_categories(self) -> Dict[str, Any]:
        return {
            "餐饮": {
                "description": "餐厅预订与菜品选择",
                "icon": "🍽️",
                "brands": {
                    "海底捞": {
                        "series": ["午餐套餐", "晚餐套餐", "家庭套餐"],
                        "series_configs": {
                            "午餐套餐": ["1. 11:30", "2. 12:00", "3. 12:30"],
                            "晚餐套餐": ["1. 18:00", "2. 18:30", "3. 19:00"],
                            "家庭套餐": ["1. 17:00", "2. 17:30", "3. 18:00"],
                        },
                    },
                    "西贝莜面村": {
                        "series": ["午市精选", "晚市精选"],
                        "series_configs": {
                            "午市精选": ["1. 11:30", "2. 12:00", "3. 12:30"],
                            "晚市精选": ["1. 18:00", "2. 18:30", "3. 19:00"],
                        },
                    },
                    "外婆家": {
                        "series": ["商务简餐", "家庭聚餐"],
                        "series_configs": {
                            "商务简餐": ["1. 12:00", "2. 12:30"],
                            "家庭聚餐": ["1. 18:00", "2. 19:00"],
                        },
                    },
                },
            }
        }

    def _initialize_response_templates(self) -> Dict[str, Any]:
        return {
            "greeting_intro": [
                "您好！欢迎使用餐饮预订助手。",
                "您可以跟我说：订餐、预订、餐厅等。",
            ],
            "ask_category_first": [
                "为了更好地为您安排预订，请先确定一个方向。",
                "您是想预订哪类餐厅？可以直接说餐厅名称。",
            ],
            "category_confirm_dining": [
                "好的，已进入餐饮预订。",
            ],
            "brand_select_prompt": [
                "您更倾向哪家餐厅？",
            ],
            "series_select_prompt": [
                "请选择该餐厅的用餐套餐或时段。",
            ],
            "config_select_prompt": [
                "请选择具体的时间档。",
            ],
            "restart_prompt_short": [
                "好的，我们重新开始预订流程。",
                "请告诉我您想预订的餐厅或菜系。",
            ],
        }

    def _load_external_templates(self):
        try:
            base = os.path.dirname(__file__)
            path = os.path.join(base, 'data', 'dining_templates.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.response_templates.update(data)
        except Exception:
            pass

    def _initialize_aliases(self) -> Dict[str, Dict[str, str]]:
        return {
            "category": {
                "餐饮": "餐饮",
                "订餐": "餐饮",
                "预订": "餐饮",
                "餐厅": "餐饮",
            },
            "brand": {
                "haidilao": "海底捞",
                "海底捞": "海底捞",
                "xibei": "西贝莜面村",
                "西贝": "西贝莜面村",
                "外婆家": "外婆家",
            },
            "series": {
                "午餐套餐": "午餐套餐",
                "晚餐套餐": "晚餐套餐",
                "家庭套餐": "家庭套餐",
                "午市精选": "午市精选",
                "晚市精选": "晚市精选",
                "商务简餐": "商务简餐",
                "家庭聚餐": "家庭聚餐",
            },
        }

    def _load_external_aliases(self):
        try:
            base = os.path.dirname(__file__)
            path = os.path.join(base, 'data', 'dining_aliases.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict):
                            self.aliases.setdefault(k, {}).update(v)
        except Exception:
            pass

    def get_brands_in_category(self, category: str) -> List[str]:
        if category in self.categories:
            return list(self.categories[category]["brands"].keys())
        return []

    def get_series_in_brand(self, category: str, brand: str) -> List[str]:
        if category in self.categories and brand in self.categories[category]["brands"]:
            return self.categories[category]["brands"][brand]["series"]
        return []

    def get_series_configs(self, category: str, brand: str, series_name: str) -> List[str]:
        if category in self.categories and brand in self.categories[category]["brands"]:
            m = self.categories[category]["brands"][brand].get("series_configs", {})
            return m.get(series_name, [])
        return []

    def get_template(self, key: str) -> List[str]:
        v = self.response_templates.get(key)
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [str(v)]

    def canonicalize(self, kind: str, term: str) -> Optional[str]:
        if not term:
            return None
        t = term.strip().lower()
        m = self.aliases.get(kind, {})
        return m.get(t)

    def get_recommendations_by_scenario(self, category: str, scenario: str) -> List[Dict[str, Any]]:
        return []

    def infer_category_for_brand(self, brand: str) -> Optional[str]:
        for category, info in self.categories.items():
            if brand in info.get("brands", {}).keys():
                return category
        return None

    def get_default_brand_for_category(self, category: str) -> Optional[str]:
        info = self.categories.get(category)
        if not info:
            return None
        brands = list(info.get("brands", {}).keys())
        return brands[0] if brands else None

    def filter_series_by_subtype(self, category: str, subtype: Optional[str], series_list: List[str]) -> List[str]:
        return series_list