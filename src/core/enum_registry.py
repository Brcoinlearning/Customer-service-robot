"""统一的槽位枚举与别名注册表
提供:
- ENUM_SLOT_OPTIONS: {slot_name: [ {label:str, aliases:list[str]} ] }
- get_slot_options(slot_name) -> list[dict]
- map_numeric(slot_name, number) -> str|None
- unique_match(slot_name, user_input) -> str|None  (仅当唯一匹配时返回)
实现原则:
1. 只对常用槽位提供少量别名, 保持轻量
2. 数字选择仅在纯数字输入时生效
3. 唯一匹配: 输入中出现某候选的任一别名/主标签, 且总命中数 == 1
4. 不做模糊距离, 仅做子串包含 (小写归一)
"""
from typing import List, Dict, Optional

ENUM_SLOT_OPTIONS: Dict[str, List[Dict[str, List[str]]]] = {
    # 产品大类
    "category": [
        {"label": "电脑", "aliases": ["电脑", "笔记本", "mac", "macbook"]},
        {"label": "手机", "aliases": ["手机", "iphone", "苹果手机"]},
        {"label": "平板", "aliases": ["平板", "ipad", "苹果平板"]},
    ],
    # 餐饮预订类型
    "dining_category": [
        {"label": "餐饮预订", "aliases": ["餐饮预订", "预订", "订餐", "用餐", "餐饮"]},
    ],
    # 品牌
    "brand": [
        {"label": "苹果", "aliases": ["苹果", "apple", "苹果公司"]},
    ],
    # 电脑系列
    "series": [
        {"label": "MacBook Air", "aliases": ["air", "macbook air"]},
        {"label": "MacBook Pro", "aliases": ["pro", "macbook pro"]},
        {"label": "iMac", "aliases": ["imac"]},
    ],
    # 芯片
    "chip": [
        {"label": "M3", "aliases": ["m3"]},
        {"label": "M3 Pro", "aliases": ["m3 pro", "pro 芯片", "m3pro"]},
        {"label": "M3 Max", "aliases": ["m3 max", "max 芯片", "m3max"]},
    ],
    # 尺寸（用于电脑）
    "size": [
        {"label": "13寸", "aliases": ["13寸", "13英寸", "13"]},
        {"label": "14寸", "aliases": ["14寸", "14英寸", "14"]},
        {"label": "15寸", "aliases": ["15寸", "15英寸", "15"]},
        {"label": "16寸", "aliases": ["16寸", "16英寸", "16"]},
    ],
    # 存储
    "storage": [
        {"label": "512GB", "aliases": ["512", "512g", "512gb"]},
        {"label": "512GB 特价版", "aliases": ["512", "512 特价", "特价512"]},
        {"label": "1TB", "aliases": ["1t", "1tb", "一t", "一tb"]},
        {"label": "2TB", "aliases": ["2t", "2tb", "两t", "两tb"]},
    ],
    # 颜色
    "color": [
        {"label": "深空灰", "aliases": ["深空灰", "灰色", "灰", "深灰"]},
        {"label": "银色", "aliases": ["银色", "银", "银白", "白银"]},
        {"label": "午夜色", "aliases": ["午夜", "深蓝", "暗蓝", "午夜色"]},
        {"label": "星光色", "aliases": ["星光", "星光色", "金色", "香槟"]},
    ],
    # 手机型号 (示例)
    "phone_model": [
        {"label": "iPhone 16 Pro 系列", "aliases": ["16 pro", "pro max", "旗舰"]},
        {"label": "iPhone 16 系列", "aliases": ["16", "标准16", "普通16"]},
        {"label": "iPhone 15 系列", "aliases": ["15", "上一代"]},
    ],
    # 手机存储
    "phone_storage": [
        {"label": "256GB", "aliases": ["256", "256g"]},
        {"label": "512GB", "aliases": ["512", "512g", "512gb"]},
        {"label": "1TB", "aliases": ["1t", "1tb"]},
    ],
    # 手机颜色示例
    "phone_color": [
        {"label": "黑色", "aliases": ["黑", "黑色"]},
        {"label": "白色", "aliases": ["白", "白色"]},
        {"label": "蓝色", "aliases": ["蓝", "蓝色"]},
        {"label": "自然钛色", "aliases": ["钛", "自然钛", "钛色"]},
    ],
    # 餐饮人数示例 (party_size)
    "party_size": [
        {"label": "2人", "aliases": ["2人", "两人", "2"]},
        {"label": "4人", "aliases": ["4人", "四人", "4"]},
        {"label": "6人", "aliases": ["6人", "六人", "6"]},
        {"label": "8人", "aliases": ["8人", "八人", "8"]},
    ],
    # 餐厅品牌
    "dining_brand": [
        {"label": "海底捞", "aliases": ["海底捞", "火锅"]},
        {"label": "西贝莜面村", "aliases": ["西贝", "莜面村", "西北菜"]},
        {"label": "外婆家", "aliases": ["外婆家", "江浙菜"]},
    ],
    # 餐饮日期
    "date": [
        {"label": "今天", "aliases": ["今天", "当日", "1"]},
        {"label": "明天", "aliases": ["明天", "明日", "2"]},
        {"label": "后天", "aliases": ["后天", "3"]},
    ],
    # 餐饮时段/套餐类型
    "dining_series": [
        {"label": "午餐时段", "aliases": ["午餐", "中午", "1"]},
        {"label": "晚餐时段", "aliases": ["晚餐", "晚上", "2"]}, 
        {"label": "特色套餐", "aliases": ["套餐", "特色", "3"]},
    ],
}


def get_slot_options(slot_name: str) -> List[Dict[str, List[str]]]:
    return ENUM_SLOT_OPTIONS.get(slot_name, [])


def map_numeric(slot_name: str, number: int) -> Optional[str]:
    options = get_slot_options(slot_name)
    if not options:
        return None
    # 针对 storage 槽位的数字映射与展示顺序保持一致：
    # 展示: 1. 512GB 2. 1TB 3. 2TB
    # 但枚举中包含一个制造歧义的 "512GB 特价版" 选项用于匹配测试。
    # 因此数字选择需要过滤掉该特价版以保持测试与提示一致。
    if slot_name == "storage":
        filtered = [o for o in options if o["label"] in {"512GB", "1TB", "2TB"}]
        if number < 1 or number > len(filtered):
            return None
        return filtered[number - 1]["label"]
    if number < 1 or number > len(options):
        return None
    return options[number - 1]["label"]


def unique_match(slot_name: str, user_input: str) -> Optional[str]:
    """尝试对指定槽位执行唯一匹配。
    命中条件: 输入包含某个候选的主标签或别名 (子串判断, 小写归一), 且命中集合大小==1
    返回: 唯一匹配的 canonical label 或 None
    """
    options = get_slot_options(slot_name)
    if not options:
        return None
    text = user_input.lower()
    hits = []
    for opt in options:
        if opt["label"].lower() in text:
            hits.append(opt["label"])
            continue
        for alias in opt["aliases"]:
            if alias.lower() in text:
                hits.append(opt["label"])
                break
    # 去重
    hits = list(dict.fromkeys(hits))
    if len(hits) == 1:
        return hits[0]
    return None

def collect_matches(slot_name: str, user_input: str) -> List[str]:
    """返回所有命中的候选主标签 (去重)。"""
    options = get_slot_options(slot_name)
    if not options:
        return []
    text = user_input.lower()
    hits = []
    for opt in options:
        if opt["label"].lower() in text:
            hits.append(opt["label"])
            continue
        for alias in opt["aliases"]:
            if alias.lower() in text:
                hits.append(opt["label"])
                break
    return list(dict.fromkeys(hits))

__all__ = [
    "ENUM_SLOT_OPTIONS",
    "get_slot_options",
    "map_numeric",
    "unique_match",
    "collect_matches",
]
