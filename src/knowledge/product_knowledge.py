from typing import Dict, List, Any, Optional
import os
import json

class ProductKnowledge:
    """产品知识库 - 存储产品分类和关系"""
    
    def __init__(self):
        self.categories = self._initialize_categories()
        self.response_templates = self._initialize_response_templates()
        self.aliases = self._initialize_aliases()
        self._load_external_templates()
        self._load_external_aliases()
    
    def _initialize_categories(self) -> Dict[str, Any]:
        """初始化产品分类结构"""
        return {
            "手机": {
                "description": "智能手机系列",
                "icon": "📱",
                "brands": {
                    "苹果": {
                        "series": ["iPhone 16 Pro 系列", "iPhone 16 系列", "iPhone 15 系列"],
                        "scenarios": ["摄影", "办公", "游戏", "日常使用"],
                        "price_range": "中高端",
                        "series_configs": {
                            "iPhone 16 Pro 系列": [
                                "1. 256GB",
                                "2. 512GB",
                                "3. 1TB",
                            ],
                            "iPhone 16 系列": [
                                "1. 128GB",
                                "2. 256GB",
                                "3. 512GB",
                            ],
                            "iPhone 15 系列": [
                                "1. 128GB",
                                "2. 256GB",
                                "3. 512GB",
                            ],
                        },
                    },
                }
            },
            "电脑": {
                "description": "电脑设备系列",
                "icon": "💻",
                "brands": {
                    "苹果": {
                        "series": ["MacBook Air", "MacBook Pro", "iMac", "Mac mini", "Mac Studio"],
                        "scenarios": ["设计", "编程", "办公", "创意工作", "学习"],
                        "price_range": "高端",
                        "series_configs": {
                            "MacBook Air": [
                                "1. 13.6寸：适合日常学习和轻办公，机身更小巧",
                                "2. 15.3寸：屏幕更大，更适合多窗口办公和观影",
                            ],
                            "MacBook Pro": [
                                "1. 14寸：兼顾便携与性能，适合移动办公和创作",
                                "2. 16寸：屏幕更大、性能更强，适合重度创作和开发",
                            ],
                            "iMac": [
                                "1. 24寸一体机：屏幕素质高，外观一体化，适合家庭和创意办公",
                                "2. M 系列芯片：性能与能耗平衡，适合日常办公和轻度剪辑",
                            ],
                            "Mac mini": [
                                "💻 1. 基础版：适合日常办公、家庭娱乐（请输入1选择）",
                                "🔌 2. 增强版：支持多显示器、更多接口（请输入2选择）",
                            ],
                            "Mac Studio": [
                                "1. 高性能台式主机：适合专业创意、剪辑和开发场景",
                                "2. 更强散热与扩展性：支持多显示器与高负载工作流",
                            ],
                        },
                    },
                }
            },
            "平板": {
                "description": "iPad 平板电脑系列",
                "icon": "📘",
                "brands": {
                    "苹果": {
                        "series": ["iPad Pro", "iPad Air", "iPad", "iPad mini"],
                        "scenarios": ["学习", "娱乐", "看视频", "记笔记"],
                        "price_range": "中高端",
                        "series_configs": {
                            "iPad Pro": [
                                "1. 大尺寸高刷屏：适合专业绘画和影音创作",
                                "2. 搭配 Apple Pencil 和键盘，接近笔记本体验",
                            ],
                            "iPad Air": [
                                "1. 轻薄便携：适合学生随身携带学习、上课记笔记",
                                "2. 性能与重量平衡，日常娱乐和办公都够用",
                            ],
                            "iPad": [
                                "1. 入门款：适合日常追剧、网课和轻度办公",
                                "2. 价格相对亲民，性价比较高",
                            ],
                            "iPad mini": [
                                "1. 小尺寸机身：单手握持方便，适合阅读和移动使用",
                                "2. 便携性最好，适合作为随身电子书和记事本",
                            ],
                        },
                    },
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
    
    def _initialize_response_templates(self) -> Dict[str, Any]:
        """初始化通用响应模板，尽量将固定文案从 DSL 中迁移到知识库"""
        return {
            # 问候与引导
            "greeting_intro": [
                "您好！欢迎来到苹果产品顾问。",
                "您可以跟我说：想买 Mac（电脑）、iPhone（手机）或 iPad 等。",
            ],
            # 全局重置与切换
            "global_reset_prompt": [
                "好的，让我们重新开始！",
                "您想先了解 Mac（电脑）还是 iPhone（手机）？也可以说 iPad。",
            ],
            "switch_to_phone_done": [
                "好的，为您推荐 iPhone 手机！",
            ],
            "switch_to_computer_prompt": [
                "检测到您想改为了解电脑，已为您切换！",
                "目前我们有：笔记本电脑、台式机。",
                "您更偏向【笔记本】还是【台式机】？",
            ],
            # 品牌范围兜底
            "non_apple_brand_fallback": [
                "这位客官，目前我是苹果产品专卖顾问，只能帮您推荐 Apple 的产品哦～",
                "您可以告诉我更想了解 Mac、iPhone、iPad 还是 Apple Watch、AirPods 等哪一类？",
            ],
            # 大类确认与提示
            "phone_category_confirm": [
                "好的，为您推荐 iPhone 手机！",
            ],
            "ipad_category_confirm": [
                "好的，您想了解 iPad。",
            ],
            "computer_subtype_prompt": [
                "目前我们有：笔记本电脑、台式机。",
                "您更偏向【笔记本】还是【台式机】？",
            ],
            # 大类询问
            "ask_category_first": [
                "感谢您的首次咨询！为了更好地为您推荐产品，先帮您确定一个方向。",
                "您是想先了解 Mac（电脑）、iPhone（手机）还是 iPad？",
            ],
            "ask_category_repeat": [
                "我们还没确定您想看【电脑】还是【手机】～",
                "请告诉我：想了解【电脑】还是【手机】？也可以说 iPad。",
            ],
            # 子类引导
            "laptop_intro_prompt": [
                "了解～您想要的苹果笔记本有多种选择。",
                "您更倾向哪一类？比如：MacBook Air、MacBook Pro 等。",
            ],
            "desktop_intro_prompt": [
                "好的，这里主要是苹果的台式机产品。",
                "例如：iMac、Mac mini、Mac Studio 等。您更偏向哪一类？",
            ],
            # MacBook Pro with M3 尺寸
            "mbp_m3_size_options": [
                "好的！【MacBook Pro with M3 芯片】目前有：",
                "1. 14 寸：12,999 元",
                "2. 16 寸：16,999 元",
                "您更关注【14 寸】还是【16 寸】？可以说 1 或 2",
            ],
            # MacBook Air 存储
            "air_13_storage_options": [
                "📦 13.6寸 MacBook Air 可选配置：",
                "1. 8GB + 256GB SSD：8,999元",
                "2. 8GB + 512GB SSD：10,999元",
                "3. 16GB + 512GB SSD：12,999元",
                "您需要哪种存储配置？可以说 1、2、3",
            ],
            "air_15_storage_options": [
                "📦 15.3寸 MacBook Air 可选配置：",
                "1. 8GB + 256GB SSD：11,999元",
                "2. 8GB + 512GB SSD：13,999元",
                "3. 16GB + 1TB SSD：15,999元",
                "您需要哪种存储配置？可以说 1、2、3",
            ],
            # MacBook Pro 芯片
            "mbp_14_chip_options": [
                "🔧 14寸 MacBook Pro 芯片选项：",
                "1. M3芯片：12,999元",
                "2. M3 Pro芯片：16,999元",
                "3. M3 Max芯片：24,999元",
                "您需要哪种芯片配置？可以说 1、2、3",
            ],
            "mbp_16_chip_options": [
                "🔧 16寸 MacBook Pro 芯片选项：",
                "1. M3 Pro芯片：22,999元",
                "2. M3 Max芯片：29,999元",
                "您需要哪种芯片配置？可以说 1 或 2",
            ],
            # MacBook Pro 存储（按芯片）
            "mbp_storage_options_m3": [
                "✅ 已选择 M3 芯片",
                "📦 存储配置选项：",
                "1. 512GB SSD",
                "2. 1TB SSD",
                "3. 2TB SSD",
                "您需要哪种存储容量？",
            ],
            "mbp_storage_options_m3_pro": [
                "✅ 已选择 M3 Pro 芯片",
                "📦 存储配置选项：",
                "1. 1TB SSD",
                "2. 2TB SSD",
                "3. 4TB SSD",
                "您需要哪种存储容量？",
            ],
            "mbp_storage_options_m3_max": [
                "✅ 已选择 M3 Max 芯片",
                "📦 存储配置选项：",
                "1. 2TB SSD",
                "2. 4TB SSD",
                "3. 8TB SSD",
                "您需要哪种存储容量？",
            ],
            # iPhone 颜色
            "iphone_color_options": [
                "🎨 颜色可选：",
                "1. 黑色",
                "2. 白色",
                "3. 蓝色",
                "4. 自然钛",
                "您偏好哪种颜色？可以说 1、2、3、4",
            ],
            # 通用重启提示
            "restart_prompt_short": [
                "🔄 好的，让我们重新开始！",
                "您想了解什么苹果产品？可以说：Mac、iPhone、iPad 等",
            ],
            "cart_cleared_prompt": [
                "🗑️ 已清空购物车",
                "让我们重新开始选择产品吧！",
                "您想了解什么苹果产品？可以说：Mac、iPhone、iPad 等",
            ],
            "fallback_category_select_prompt": [
                "请告诉我您想先了解 Mac（电脑）还是 iPhone（手机）？也可以说 iPad。",
            ],
            "fallback_subtype_select_prompt": [
                "您更偏向【笔记本】还是【台式机】？",
            ],
            "fallback_brand_select_with_subtype_prompt": [
                "请选择${current_subtype}的品牌",
            ],
            "fallback_brand_select_with_category_prompt": [
                "请选择${current_category}的品牌",
            ],
            "fallback_brand_select_generic_prompt": [
                "请选择产品的品牌",
            ],
            "fallback_series_select_prompt": [
                "请选择您感兴趣的产品系列",
            ],
            "fallback_config_select_prompt": [
                "⚠️ 请输入有效的选项编号（如：1 或 2）",
                "📝 您可以直接输入数字来选择配置",
            ],
            "fallback_phone_model_select_prompt": [
                "请选择您感兴趣的 iPhone 型号，可以说 1、2、3。",
            ],
            "fallback_phone_storage_select_prompt": [
                "请选择需要的存储容量，例如 256GB。",
            ],
            "fallback_phone_color_select_prompt": [
                "请选择喜欢的机身颜色，例如黑色、白色。",
            ],
            "fallback_default_prompt": [
                "抱歉，我没有理解。您可以重新描述需求，或说'重新开始'来重置对话。",
            ],
            # 新增的错误处理模板
            "invalid_config_choice": [
                "❌ 无效的选项，请输入 1 或 2",
                "💡 提示：直接输入数字即可选择配置",
            ],
            "config_selection_guide": [
                "🔍 请从上面的配置中选择一个：",
                "⌨️ 输入对应的数字编号即可（如：1、2）",
            ],
        }

    def _load_external_templates(self):
        try:
            base = os.path.dirname(__file__)
            path = os.path.join(base, 'data', 'product_templates.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.response_templates.update(data)
        except Exception:
            pass

    def get_template(self, key: str) -> List[str]:
        """获取响应模板，返回字符串列表"""
        value = self.response_templates.get(key)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [str(value)]

    def _initialize_aliases(self) -> Dict[str, Dict[str, str]]:
        return {
            "brand": {
                "apple": "苹果",
                "iphone": "苹果",
            },
            "series": {
                "air": "MacBook Air",
                "macbook air": "MacBook Air",
                # 精确笔记本系列别名，避免与 iPhone 16 Pro 冲突
                "macbook pro": "MacBook Pro",
                "macbook pro": "MacBook Pro",
                "imac": "iMac",
                "mini": "Mac mini",
                "mac mini": "Mac mini",
                "studio": "Mac Studio",
                "mac studio": "Mac Studio",
                # iPhone 系列别名
                "16 pro": "iPhone 16 Pro 系列",
                "16pro": "iPhone 16 Pro 系列",
                "iphone 16 pro": "iPhone 16 Pro 系列",
                "16": "iPhone 16 系列",
                "iphone 16": "iPhone 16 系列",
                "15": "iPhone 15 系列",
                "iphone 15": "iPhone 15 系列",
            },
            "category": {
                "电脑": "电脑",
                "手机": "手机",
                "平板": "平板",
                "mac": "电脑",
                "iphone": "手机",
                "ipad": "平板",
            },
            "subtype": {
                "笔记本": "笔记本",
                "台式机": "台式机",
            },
        }

    def _load_external_aliases(self):
        try:
            base = os.path.dirname(__file__)
            path = os.path.join(base, 'data', 'product_aliases.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict):
                            self.aliases.setdefault(k, {}).update(v)
        except Exception:
            pass

    def canonicalize(self, kind: str, term: str) -> Optional[str]:
        if not term:
            return None
        t = term.strip().lower()
        m = self.aliases.get(kind, {})
        return m.get(t)
    
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

    def get_series_configs(self, category: str, brand: str, series_name: str) -> List[str]:
        """获取指定系列的配置选项（如不同尺寸/芯片组合）"""
        brand_info = self.get_brand_info(category, brand)
        if not brand_info:
            return []
        config_map = brand_info.get("series_configs", {})
        return config_map.get(series_name, [])

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

    def infer_category_for_brand(self, brand: str) -> Optional[str]:
        for category, category_info in self.categories.items():
            if brand in category_info.get("brands", {}).keys():
                return category
        return None

    def get_default_brand_for_category(self, category: str) -> Optional[str]:
        info = self.categories.get(category)
        if not info:
            return None
        brands = list(info.get("brands", {}).keys())
        return brands[0] if brands else None

    def filter_series_by_subtype(self, category: str, subtype: Optional[str], series_list: List[str]) -> List[str]:
        if category == "电脑" and subtype:
            if subtype == "笔记本":
                return [s for s in series_list if s in {"MacBook Air", "MacBook Pro"}]
            if subtype == "台式机":
                return [s for s in series_list if s in {"iMac", "Mac mini", "Mac Studio"}]
        return series_list