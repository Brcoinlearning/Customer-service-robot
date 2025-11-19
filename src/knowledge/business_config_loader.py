"""
统一业务配置加载器
用于加载和管理各业务线的配置信息，包括槽位规格、枚举定义和模板
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from core.interfaces import SlotSpec


@dataclass
class BusinessConfig:
    """业务配置数据类"""
    name: str
    display_name: str
    description: str
    slot_specs: List[SlotSpec]
    enums: Dict[str, List[Dict[str, Any]]]
    templates: Dict[str, List[str]]
    filters: Dict[str, Dict[str, List[str]]] = None  # 动态过滤映射
    command_keywords: Dict[str, List[str]] = None  # 通用命令关键词
    intent_recommendations: Dict[str, List[Dict[str, Any]]] = None  # 意图推荐配置


class BusinessConfigLoader:
    """业务配置加载器"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(current_dir, 'business_configs')
        self.config_dir = config_dir
        self._configs: Dict[str, BusinessConfig] = {}
        self._enum_registry: Dict[str, List[Dict[str, Any]]] = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """加载所有业务配置"""
        if not os.path.exists(self.config_dir):
            print(f"配置目录不存在: {self.config_dir}")
            return
            
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                business_name = filename[:-5]  # 去掉.json后缀
                config_path = os.path.join(self.config_dir, filename)
                try:
                    self._load_business_config(business_name, config_path)
                except Exception as e:
                    print(f"加载配置失败 {filename}: {e}")
    
    def _load_business_config(self, business_name: str, config_path: str):
        """加载单个业务配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析业务信息
        business_info = data.get('business_info', {})
        
        # 解析槽位规格
        slot_specs = []
        for spec_data in data.get('slot_specs', []):
            slot_spec = SlotSpec(
                name=spec_data['name'],
                required=spec_data['required'],
                description=spec_data['description'],
                dependencies=spec_data.get('dependencies', []),
                enums_key=spec_data.get('enums_key'),
                semantic_stage=spec_data.get('semantic_stage'),
                allow_llm=spec_data.get('allow_llm', False)
            )
            slot_specs.append(slot_spec)
        
        # 解析枚举定义
        enums = data.get('enums', {})
        
        # 解析模板、过滤映射、命令关键词、意图推荐
        templates = data.get('templates', {})
        filters = data.get('filters', {})
        command_keywords = data.get('command_keywords', {})
        intent_recommendations = data.get('intent_recommendations', {})
        
        # 创建业务配置对象
        config = BusinessConfig(
            name=business_info.get('name', business_name),
            display_name=business_info.get('display_name', business_name),
            description=business_info.get('description', ''),
            slot_specs=slot_specs,
            enums=enums,
            templates=templates,
            filters=filters,
            command_keywords=command_keywords,
            intent_recommendations=intent_recommendations
        )
        
        self._configs[business_name] = config
        
        # 更新全局枚举注册表（使用业务前缀避免冲突）
        for enum_key, enum_values in enums.items():
            # 使用业务前缀的全局键
            global_key = f"{business_name}.{enum_key}"
            self._enum_registry[global_key] = enum_values
        
        print(f"成功加载业务配置: {business_name} ({config.display_name})")
    
    def get_business_config(self, business_name: str) -> Optional[BusinessConfig]:
        """获取指定业务的配置"""
        return self._configs.get(business_name)
    
    def get_slot_specs(self, business_name: str) -> List[SlotSpec]:
        """获取指定业务的槽位规格"""
        config = self._configs.get(business_name)
        if config:
            return config.slot_specs
        return []
    
    def inject_slot_specs(self, business_name: str, slot_specs: List[SlotSpec]):
        """
        为指定业务动态注入槽位规格（用于DSL）
        
        Args:
            business_name: 业务名称
            slot_specs: 槽位规格列表
        """
        config = self._configs.get(business_name)
        if config:
            config.slot_specs = slot_specs
        else:
            print(f"⚠️  业务配置不存在: {business_name}，无法注入槽位规格")
    
    def get_enums(self, business_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取指定业务的枚举定义"""
        config = self._configs.get(business_name)
        if config:
            return config.enums
        return {}
    
    def get_templates(self, business_name: str) -> Dict[str, List[str]]:
        """获取指定业务的模板"""
        config = self._configs.get(business_name)
        if config:
            return config.templates
        return {}
    
    def get_template(self, business_name: str, template_key: str) -> List[str]:
        """获取指定业务的单个模板（兼容ProductKnowledge.get_template接口）"""
        templates = self.get_templates(business_name)
        return templates.get(template_key, [])
    
    def get_all_enums(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有业务的枚举定义（向后兼容）"""
        return self._enum_registry.copy()
    
    def get_intent_recommendations(self, business_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取指定业务的意图推荐配置
        
        返回格式：
        {
            "chip": [
                {
                    "intent": "高性能场景",
                    "keywords": ["视频", "剪辑"],
                    "recommend": "M3 Pro",
                    "confidence": 0.75,
                    "reason": "检测到专业创作需求"
                }
            ]
        }
        """
        config = self._configs.get(business_name)
        if config and config.intent_recommendations:
            return config.intent_recommendations
        return {}
    
    def list_businesses(self) -> List[str]:
        """列出所有可用的业务"""
        return list(self._configs.keys())
    
    def get_business_display_names(self) -> Dict[str, str]:
        """获取业务的显示名称映射"""
        return {name: config.display_name for name, config in self._configs.items()}


# 全局业务配置加载器实例
business_config_loader = BusinessConfigLoader()


def get_business_config(business_name: str) -> Optional[BusinessConfig]:
    """获取业务配置的便捷函数"""
    return business_config_loader.get_business_config(business_name)


def get_slot_specs(business_name: str) -> List[SlotSpec]:
    """获取槽位规格的便捷函数"""
    return business_config_loader.get_slot_specs(business_name)


def get_enum_options(enum_key: str) -> List[Dict[str, Any]]:
    """获取枚举选项的便捷函数（向后兼容）"""
    all_enums = business_config_loader.get_all_enums()
    return all_enums.get(enum_key, [])


def get_templates(business_name: str) -> Dict[str, List[str]]:
    """获取模板的便捷函数"""
    return business_config_loader.get_templates(business_name)


# 向后兼容函数 (用于替换 enum_registry.py)

def get_slot_options(enum_key: str, business_name: str = None) -> List[Dict[str, Any]]:
    """获取槽位选项（向后兼容）"""
    # 如果指定了业务名，优先使用业务特定的枚举
    if business_name:
        business_enums = business_config_loader.get_enums(business_name)
        if enum_key in business_enums:
            return business_enums[enum_key]
    
    # 回退到全局枚举
    all_enums = business_config_loader.get_all_enums()
    return all_enums.get(enum_key, [])


def map_numeric(enum_key: str, number: int) -> Optional[str]:
    """数字映射（向后兼容）"""
    options = get_slot_options(enum_key)
    if not options:
        return None
    
    # 针对 storage 槽位的特殊处理
    if enum_key == "storage":
        filtered = [o for o in options if o["label"] in {"512GB", "1TB", "2TB"}]
        if number < 1 or number > len(filtered):
            return None
        return filtered[number - 1]["label"]
    
    if number < 1 or number > len(options):
        return None
    return options[number - 1]["label"]


def unique_match(enum_key: str, user_input: str) -> Optional[str]:
    """唯一匹配（向后兼容）"""
    options = get_slot_options(enum_key)
    if not options:
        return None
    
    text = user_input.lower()
    hits = []
    
    for opt in options:
        label = opt.get("label", "")
        aliases = opt.get("aliases", [])
        
        if label.lower() in text:
            hits.append(label)
            continue
        for alias in aliases:
            if alias.lower() in text:
                hits.append(label)
                break
    
    # 去重
    hits = list(dict.fromkeys(hits))
    if len(hits) == 1:
        return hits[0]
    return None


def collect_matches(enum_key: str, user_input: str) -> List[str]:
    """收集所有匹配项（向后兼容）"""
    options = get_slot_options(enum_key)
    if not options:
        return []
    
    text = user_input.lower()
    hits = []
    
    for opt in options:
        label = opt.get("label", "")
        aliases = opt.get("aliases", [])
        
        if label.lower() in text:
            hits.append(label)
            continue
        for alias in aliases:
            if alias.lower() in text:
                hits.append(label)
                break
    
    return list(dict.fromkeys(hits))