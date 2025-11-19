"""槽位验证模块 - 用于对已填充的槽位组合进行业务约束校验
后续可扩展为从 DSL 或知识库动态加载守卫规则。
"""
from typing import Dict, List, Tuple

class SlotValidationError(Exception):
    pass

def validate_chip_storage(context: Dict) -> List[str]:
    """芯片与存储组合校验。
    标准 M3 不允许 1TB/2TB；手机非 Pro 系列不允许 1TB。
    返回错误消息列表（无错误则为空）。
    """
    errors: List[str] = []
    chip = context.get("selected_chip") or context.get("chip")
    storage = context.get("selected_storage") or context.get("storage")
    series = context.get("current_series") or context.get("series")
    category = context.get("current_category") or context.get("category")
    if chip and storage:
        if chip == "M3" and storage in {"1TB", "2TB"}:
            errors.append("标准 M3 芯片不支持 1TB 及以上存储，请选择 M3 Pro 或 M3 Max")
    if category == "手机" and series:
        if "Pro" not in series and storage == "1TB":
            errors.append("当前手机系列不支持 1TB（仅 Pro 系列支持），请调整存储或机型")
    return errors

def validate_size_chip(context: Dict) -> List[str]:
    """尺寸与芯片组合校验：例如 13寸不支持 M3 Max 等。"""
    errors: List[str] = []
    size = context.get("current_size") or context.get("size")
    chip = context.get("selected_chip") or context.get("chip")
    series = context.get("current_series") or context.get("series")
    if size and chip:
        if size == "13寸" and chip == "M3 Max":
            errors.append("13寸机型不提供 M3 Max 选项，请选择 M3 或 M3 Pro")
        if size == "14寸" and chip == "M3 Max" and series == "MacBook Air":
            errors.append("MacBook Air 不支持 M3 Max，请选择 Pro 系列或更改芯片")
    return errors

VALIDATORS = [
    validate_chip_storage,
    validate_size_chip,
]

def run_validators(context: Dict) -> List[str]:
    """运行所有验证器并收集错误消息。"""
    all_errors: List[str] = []
    for validator in VALIDATORS:
        try:
            all_errors.extend(validator(context))
        except Exception:
            # 单个验证器失败不影响其它验证
            continue
    return all_errors
