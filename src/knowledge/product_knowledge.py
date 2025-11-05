from typing import Dict, List, Any, Optional

class ProductKnowledge:
    """产品知识库 - 存储产品分类和关系"""
    
    def __init__(self):
        self.categories = self._initialize_categories()
    
    def _initialize_categories(self) -> Dict[str, Any]:
        """初始化产品分类结构"""
        return {
            "手机": {
                "description": "智能手机系列",
                "icon": "📱",
                "brands": {
                    "苹果": {
                        "series": ["iPhone 15", "iPhone 14", "iPhone SE"],
                        "scenarios": ["摄影", "办公", "游戏", "日常使用"],
                        "price_range": "中高端"
                    },
                    "华为": {
                        "series": ["Mate系列", "P系列", "Nova系列"],
                        "scenarios": ["商务", "摄影", "长续航"],
                        "price_range": "中高端"
                    },
                    "小米": {
                        "series": ["数字系列", "Mix系列", "Civi系列"],
                        "scenarios": ["性价比", "游戏", "智能家居"],
                        "price_range": "中端"
                    },
                    "OPPO": {
                        "series": ["Find系列", "Reno系列", "A系列"],
                        "scenarios": ["摄影", "时尚", "快充"],
                        "price_range": "中端"
                    }
                }
            },
            "电脑": {
                "description": "电脑设备系列",
                "icon": "💻",
                "brands": {
                    "苹果": {
                        "series": ["MacBook Air", "MacBook Pro"],
                        "scenarios": ["设计", "编程", "办公", "创意工作"],
                        "price_range": "高端"
                    },
                    "联想": {
                        "series": ["ThinkPad", "YOGA", "拯救者"],
                        "scenarios": ["商务办公", "游戏", "学习"],
                        "price_range": "中高端"
                    },
                    "戴尔": {
                        "series": ["XPS", "Inspiron", "Alienware"],
                        "scenarios": ["设计", "游戏", "办公"],
                        "price_range": "中高端"
                    },
                    "华硕": {
                        "series": ["ROG", "ZenBook", "VivoBook"],
                        "scenarios": ["游戏", "办公", "学生"],
                        "price_range": "中端"
                    }
                }
            },
            "智能设备": {
                "description": "智能穿戴和家居设备",
                "icon": "🎧",
                "brands": {
                    "苹果": {
                        "series": ["Apple Watch", "AirPods", "HomePod"],
                        "scenarios": ["健康监测", "音乐", "智能家居"],
                        "price_range": "高端"
                    },
                    "华为": {
                        "series": ["Watch GT", "FreeBuds", "Sound X"],
                        "scenarios": ["运动健康", "音频", "智能生活"],
                        "price_range": "中高端"
                    },
                    "小米": {
                        "series": ["手环", "耳机", "智能家居"],
                        "scenarios": ["性价比", "运动", "智能控制"],
                        "price_range": "入门到中端"
                    }
                }
            },
            "影音娱乐": {
                "description": "影音娱乐设备",
                "icon": "📺",
                "brands": {
                    "索尼": {
                        "series": ["电视机", "耳机", "播放器"],
                        "scenarios": ["家庭影院", "音乐", "游戏"],
                        "price_range": "高端"
                    },
                    "三星": {
                        "series": ["电视机", "显示器", "音响"],
                        "scenarios": ["家庭娱乐", "办公", "游戏"],
                        "price_range": "中高端"
                    }
                }
            }
        }
    
    def get_category_options(self) -> List[Dict[str, str]]:
        """获取所有品类选项（带图标）"""
        return [
            {"name": name, "icon": info["icon"], "description": info["description"]}
            for name, info in self.categories.items()
        ]
    
    def get_brands_in_category(self, category: str) -> List[str]:
        """获取指定品类下的所有品牌"""
        if category in self.categories:
            return list(self.categories[category]["brands"].keys())
        return []
    
    def get_series_in_brand(self, category: str, brand: str) -> List[str]:
        """获取指定品牌下的所有系列"""
        if (category in self.categories and 
            brand in self.categories[category]["brands"]):
            return self.categories[category]["brands"][brand]["series"]
        return []
    
    def get_category_info(self, category: str) -> Optional[Dict[str, Any]]:
        """获取品类详细信息"""
        return self.categories.get(category)
    
    def get_brand_info(self, category: str, brand: str) -> Optional[Dict[str, Any]]:
        """获取品牌详细信息"""
        if category in self.categories:
            return self.categories[category]["brands"].get(brand)
        return None
    
    def get_recommendations_by_scenario(self, category: str, scenario: str) -> List[Dict[str, Any]]:
        """根据使用场景推荐品牌"""
        recommendations = []
        if category in self.categories:
            for brand, info in self.categories[category]["brands"].items():
                if scenario in info["scenarios"]:
                    recommendations.append({
                        "brand": brand,
                        "series": info["series"],
                        "price_range": info["price_range"],
                        "reason": f"适合{scenario}场景"
                    })
        
        return recommendations
    
    def get_all_scenarios(self) -> List[str]:
        """获取所有使用场景"""
        scenarios = set()
        for category_info in self.categories.values():
            for brand_info in category_info["brands"].values():
                scenarios.update(brand_info["scenarios"])
        return sorted(list(scenarios))
    
    def search_products(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索产品（简单关键词匹配）"""
        results = []
        keyword_lower = keyword.lower()
        
        for category, category_info in self.categories.items():
            # 搜索品类
            if keyword_lower in category.lower():
                results.append({
                    "type": "category",
                    "name": category,
                    "icon": category_info["icon"],
                    "description": category_info["description"]
                })
            
            # 搜索品牌
            for brand, brand_info in category_info["brands"].items():
                if keyword_lower in brand.lower():
                    results.append({
                        "type": "brand",
                        "name": brand,
                        "category": category,
                        "series": brand_info["series"],
                        "scenarios": brand_info["scenarios"]
                    })
                
                # 搜索系列
                for series in brand_info["series"]:
                    if keyword_lower in series.lower():
                        results.append({
                            "type": "series",
                            "name": series,
                            "brand": brand,
                            "category": category,
                            "scenarios": brand_info["scenarios"]
                        })
        
        return results