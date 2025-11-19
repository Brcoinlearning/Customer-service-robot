"""集中定义各业务线的表单槽位规格，避免分散硬编码。

后续可在此文件扩展：
- required: 是否必填
- dependencies: 前置槽位（用于按顺序提示）
- enums: 枚举候选来源（enum_registry 中的 key）
- semantic_stage: 语义映射阶段标识（OptionBuilder 使用）
- llm: 是否允许 LLM 补全该槽位（低置信度时）
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class SlotSpec:
    name: str
    required: bool
    description: str
    dependencies: List[str] = field(default_factory=list)
    enums_key: Optional[str] = None          # 枚举候选在 enum_registry 中的标识
    semantic_stage: Optional[str] = None     # 语义映射阶段名称（OptionBuilder）
    allow_llm: bool = True                   # 是否允许 LLM 进行槽位补全


APPLE_COMPUTER_SLOTS: List[SlotSpec] = [
    SlotSpec("category", True, "产品大类", enums_key="category", allow_llm=False),
    SlotSpec("brand", True, "品牌", ["category"], enums_key="brand", allow_llm=False),
    SlotSpec("series", True, "产品系列", ["brand"], enums_key="series", semantic_stage="series_select"),
    SlotSpec("size", False, "尺寸规格", ["series"], enums_key="size"),
    SlotSpec("chip", True, "处理器芯片", ["series", "size"], enums_key="chip", semantic_stage="chip_select"),
    SlotSpec("storage", True, "存储容量", ["chip"], enums_key="storage", semantic_stage="storage_select"),
    SlotSpec("color", True, "颜色", ["series"], enums_key="color", semantic_stage="color_select"),
]

PHONE_SLOTS: List[SlotSpec] = [
    SlotSpec("category", True, "产品大类", enums_key="category", allow_llm=False),
    SlotSpec("brand", True, "品牌", ["category"], enums_key="brand", allow_llm=False),
    SlotSpec("series", True, "手机系列", ["brand"], enums_key="phone_model", semantic_stage="phone_model_select"),
    SlotSpec("storage", True, "存储容量", ["series"], enums_key="phone_storage", semantic_stage="phone_storage_select"),
    SlotSpec("color", True, "颜色", ["series"], enums_key="phone_color", semantic_stage="phone_color_select"),
]

DINING_SLOTS: List[SlotSpec] = [
    SlotSpec("category", True, "预订类型", enums_key="dining_category", allow_llm=False),
    SlotSpec("brand", True, "餐厅选择", ["category"], enums_key="dining_brand"),
    SlotSpec("series", True, "用餐时段", ["brand"], enums_key="dining_series"),
    SlotSpec("party_size", True, "用餐人数", ["series"], allow_llm=False),
    SlotSpec("private_room", False, "包间偏好", ["party_size"], allow_llm=False),
    SlotSpec("date", True, "预订日期", ["party_size"], allow_llm=True),
    SlotSpec("contact", True, "联系方式", ["date"], allow_llm=False),
]


_FORM_SPEC_MAP: Dict[str, List[SlotSpec]] = {
    "apple_computer": APPLE_COMPUTER_SLOTS,
    "apple_phone": PHONE_SLOTS,
    "dining": DINING_SLOTS,
}


def get_form_template(business_line: str) -> List[SlotSpec]:
    """返回指定业务线的槽位规格列表"""
    return _FORM_SPEC_MAP.get(business_line, [])


def as_definition_map(business_line: str) -> Dict[str, Dict[str, Any]]:
    """将 SlotSpec 列表转换为旧结构的 map（兼容现有 FormBasedDialogSystem 初始化逻辑）。

    返回示例：{"series": {"required": True, "dependencies": [..], "description": "..."}}
    """
    specs = get_form_template(business_line)
    out: Dict[str, Dict[str, Any]] = {}
    for spec in specs:
        out[spec.name] = {
            "required": spec.required,
            "dependencies": spec.dependencies,
            "description": spec.description,
            "enums_key": spec.enums_key,
            "semantic_stage": spec.semantic_stage,
            "allow_llm": spec.allow_llm,
        }
    return out
"""集中式槽位候选值规格
后续可替换为从知识库动态生成
"""
from typing import Dict, List

SLOT_CANDIDATES: Dict[str, Dict[str, List[str]]] = {
    "apple_computer": {
        "category": ["电脑", "手机", "平板"],
        "brand": ["苹果"],
        "series": ["MacBook Air", "MacBook Pro", "iMac", "Mac Mini", "Mac Studio"],
        "size": ["13寸", "14寸", "15寸", "16寸"],
        "chip": ["M3", "M3 Pro", "M3 Max"],
        "storage": ["512GB", "1TB", "2TB"],
        "color": ["深空灰", "银色", "午夜色", "星光色"],
    },
    "apple_phone": {
        "category": ["手机", "电脑", "平板"],
        "brand": ["苹果"],
        "model": ["iPhone 16 Pro 系列", "iPhone 16 系列", "iPhone 15 系列"],
        "storage": ["128GB", "256GB", "512GB", "1TB"],
        "color": ["黑色", "白色", "蓝色", "自然钛"],
    },
    "dining": {
        "category": ["餐饮"],
        "brand": ["海底捞", "西贝莜面村", "外婆家"],
        "party_size": ["2人", "4人", "6人", "8人"],
        "private_room": ["包间", "大厅"],
        "date": ["今天", "明天", "后天"],
        "contact": ["手机号"],
    }
}
