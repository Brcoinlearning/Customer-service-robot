"""
多槽位信息采集对话系统（概念验证）
通过自然语言理解逐步收集配置偏好，避免生硬的“表单”术语。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from semantics.option_mapping import OptionBuilder  # 复用本地构造选项
from knowledge.business_config_loader import (
    business_config_loader, map_numeric, unique_match, 
    collect_matches, get_slot_options
)

class SlotStatus(Enum):
    EMPTY = "empty"           # 未填充
    PARTIAL = "partial"       # 部分信息（需要进一步确认）
    FILLED = "filled"         # 已完整填充
    CONFLICTED = "conflicted" # 信息冲突

class OrderStatus(Enum):
    COLLECTING = "collecting"   # 收集信息中
    READY_CONFIRM = "ready_confirm"  # 准备确认订单
    CONFIRMED = "confirmed"     # 已确认订单
    RESELECTING = "reselecting" # 重新选择某项
    AWAITING_CONTINUE = "awaiting_continue"  # 等待用户决定是否继续购物

@dataclass
class SlotDefinition:
    name: str
    required: bool
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他槽位
    validator: Optional[callable] = None
    description: str = ""
    enums_key: Optional[str] = None          # 枚举候选 key (enum_registry)
    semantic_stage: Optional[str] = None     # 语义映射阶段名称 (OptionBuilder)
    allow_llm: bool = True                   # 是否允许 LLM 补全

@dataclass
class SlotValue:
    value: Any
    confidence: float
    source: str  # "numeric", "semantic", "llm", "direct"
    reason: str = ""

@dataclass
class FormSlot:
    definition: SlotDefinition
    status: SlotStatus = SlotStatus.EMPTY
    value: Optional[SlotValue] = None
    candidates: List[SlotValue] = field(default_factory=list)

class FormBasedDialogSystem:
    """多槽位信息采集对话系统核心"""
    
    def __init__(self, business_line: str):
        self.business_line = business_line
        self.form_template = self._load_form_template(business_line)
        self.current_form = self._create_empty_form()
        self.pending_conflicts: List[Dict[str, SlotValue]] = []
        self.awaiting_conflict_slot: Optional[str] = None
        self.validation_errors: List[str] = []
        self.order_confirmed: bool = False
        self.order_summary: Dict[str, Any] = {}
        self.last_prompted_slot: Optional[str] = None  # 最近一次提示的槽位，用于数字选择
        self.initial_prompt_shown: bool = False  # 是否已显示初始提示
        self.order_status: OrderStatus = OrderStatus.COLLECTING
        self.reselect_slot: Optional[str] = None  # 当前重选的槽位
        
        # 业务过滤映射（来自配置文件）
        cfg = business_config_loader.get_business_config(business_line)
        self.business_filters = cfg.filters if cfg and getattr(cfg, 'filters', None) else {}
        
    def _load_form_template(self, business_line: str) -> Dict[str, SlotDefinition]:
        """从统一业务配置加载槽位定义"""
        slot_specs = business_config_loader.get_slot_specs(business_line)
        converted: Dict[str, SlotDefinition] = {}
        
        for spec in slot_specs:
            converted[spec.name] = SlotDefinition(
                name=spec.name,
                required=spec.required,
                dependencies=spec.dependencies,
                validator=None,
                description=spec.description,
                enums_key=spec.enums_key,
                semantic_stage=spec.semantic_stage,
                allow_llm=spec.allow_llm
            )
        return converted
    
    def get_initial_prompt(self) -> str:
        """获取初始提示，引导用户开始填写表单"""
        if not self.initial_prompt_shown:
            self.initial_prompt_shown = True
            
            # 自动填充单选项槽位
            self._auto_fill_single_option_slots()
            
            missing_required = [
                name for name, slot in self.current_form.items()
                if slot.definition.required and slot.status == SlotStatus.EMPTY
            ]
            if missing_required:
                first_slot = missing_required[0]
                self.last_prompted_slot = first_slot
                return self._generate_slot_prompt(first_slot)
        return ""
    
    def _create_empty_form(self) -> Dict[str, FormSlot]:
        """创建空表单"""
        return {name: FormSlot(definition=defn) for name, defn in self.form_template.items()}

    def get_context(self) -> Dict[str, Any]:
        """提供给语义构造器的上下文字典 (OptionBuilder 期望 _manager.get_context())."""
        ctx: Dict[str, Any] = {}
        for name, slot in self.current_form.items():
            if slot.value:
                ctx[f"current_{name}"] = slot.value.value
                if name == "chip":
                    ctx["selected_chip"] = slot.value.value
        return ctx
    
    def process_input(self, user_input: str, llm_client, semantic_mapper) -> Dict[str, Any]:
        """处理用户输入，尝试填充多个槽位"""
        extraction_result = {
            "slots_updated": [],
            "slots_filled": [],
            "conflicts": [],
            "response": "",
            "form_complete": False
        }

        # 处理继续购物/结束状态
        if self.order_status == OrderStatus.AWAITING_CONTINUE:
            normalized = user_input.strip().lower()
            if normalized in {"是", "继续", "继续购物", "再看看", "还要"}:
                # 重置表单，开始新一轮选购
                self._reset_form()
                next_slot = self._get_next_missing_slot()
                if next_slot:
                    self.last_prompted_slot = next_slot
                    extraction_result["response"] = "🎉 好的，我们重新开始选择～\n\n" + self._generate_slot_prompt(next_slot)
                else:
                    extraction_result["response"] = "系统错误：无法找到下一个槽位"
                return extraction_result
            elif normalized in {"再见", "不了", "结束", "退出", "exit", "quit", "bye"}:
                # 结束对话
                goodbye_template = business_config_loader.get_template(self.business_line, "form_goodbye")
                if goodbye_template:
                    extraction_result["response"] = "\n".join(goodbye_template)
                else:
                    extraction_result["response"] = "👋 感谢光临，期待下次为您服务！"
                extraction_result["should_exit"] = True  # 标记需要退出
                return extraction_result
            else:
                # 用户回复了其他内容，再次提示
                continue_template = business_config_loader.get_template(self.business_line, "form_continue_shopping_prompt")
                if continue_template:
                    extraction_result["response"] = "\n".join(continue_template)
                else:
                    extraction_result["response"] = "想继续看看其他产品吗？(输入'是'或'继续' / 输入'再见'结束)"
                return extraction_result

        # 优先处理纯数字输入（通用数字选择逻辑，不走LLM）
        stripped = user_input.strip()
        if stripped.isdigit():
            number = int(stripped)
            
            # 场景1：冲突解决（1/2/3）
            if self.awaiting_conflict_slot:
                if number in {1, 2, 3}:
                    self._resolve_conflict(self.awaiting_conflict_slot, str(number))
                    extraction_result["form_complete"] = self._check_form_completeness()
                    extraction_result["response"] = self._generate_response({"slots_updated": [], "slots_filled": [], "conflicts": [], "form_complete": extraction_result["form_complete"]})
                    return extraction_result
                else:
                    invalid_template = business_config_loader.get_template(self.business_line, "form_conflict_invalid_choice")
                    extraction_result["response"] = "\n".join(invalid_template) if invalid_template else "请输入 1 保留原值 | 2 使用新值 | 3 重新说明"
                    return extraction_result
            
            # 场景2：重选槽位选择（只在等待重选状态时处理）
            if self.reselect_slot == "waiting":
                required_slots = [name for name, slot in self.current_form.items() if slot.definition.required and slot.status == SlotStatus.FILLED]
                if 1 <= number <= len(required_slots):
                    selected_slot = required_slots[number - 1]
                    self.order_status = OrderStatus.RESELECTING
                    # 清空选中的槽位及其下游依赖
                    self._clear_slot_and_dependencies(selected_slot)
                    self.last_prompted_slot = selected_slot
                    self.reselect_slot = None  # 重置标志，避免循环
                    reselect_prefix = business_config_loader.get_template(self.business_line, "form_reselect_prompt_prefix")
                    if reselect_prefix:
                        prefix_text = "\n".join(reselect_prefix).replace("{slot_desc}", self.current_form[selected_slot].definition.description)
                    else:
                        prefix_text = f"好的，请重新选择{self.current_form[selected_slot].definition.description}："
                    extraction_result["response"] = prefix_text + "\n\n" + self._generate_slot_prompt(selected_slot)
                    return extraction_result
            
            # 场景3：确认菜单选择（1=确认/2=重选/3=重新开始）
            if self.order_status == OrderStatus.READY_CONFIRM:
                if number == 1:
                    # 触发确认逻辑（后面会处理）
                    pass  # 继续执行下面的确认逻辑
                elif number == 2:
                    extraction_result["response"] = self._generate_reselect_options()
                    return extraction_result
                elif number == 3:
                    self._reset_form()
                    next_slot = self._get_next_missing_slot()
                    if next_slot:
                        self.last_prompted_slot = next_slot
                        extraction_result["response"] = "好的！让我们重新开始选择～\n\n" + self._generate_slot_prompt(next_slot)
                    else:
                        extraction_result["response"] = "系统错误：无法找到下一个槽位"
                    return extraction_result
            
            # 场景4：当前槽位的选项序号映射（通用逻辑）
            target_slot = None
            
            # 优先使用 last_prompted_slot（最近提示的槽位）
            if self.last_prompted_slot and self.order_status != OrderStatus.READY_CONFIRM:
                target_slot = self.last_prompted_slot
            else:
                # 如果没有 last_prompted_slot，找第一个空的必填槽位
                for name, slot in self.current_form.items():
                    if slot.definition.required and slot.status == SlotStatus.EMPTY:
                        target_slot = name
                        break
            
            if target_slot:
                sd = self.form_template.get(target_slot)
                # 检查是否有 enums_key，如果没有说明是自由文本输入
                if sd and sd.enums_key:
                    enum_key = sd.enums_key
                    mapped = self._business_numeric_map(enum_key, number)
                    
                    if mapped:
                        sv = SlotValue(mapped, 0.9, "numeric", "序号选择")
                        update_result = self._update_slot(target_slot, sv)
                        if update_result["updated"]:
                            extraction_result["slots_updated"].append(target_slot)
                        if update_result["filled"]:
                            extraction_result["slots_filled"].append(target_slot)
                        
                        # 如果是重选模式，完成后检查表单完整性
                        if self.order_status == OrderStatus.RESELECTING:
                            self.reselect_slot = None
                            # 检查是否还有空槽位
                            if self._check_form_completeness():
                                # 表单完整，跳到确认状态
                                self.order_status = OrderStatus.READY_CONFIRM
                                self.last_prompted_slot = None
                                extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {mapped}\n\n" + self._generate_order_summary() + "\n\n" + self._generate_confirmation_options()
                            else:
                                # 表单不完整，继续收集
                                self.order_status = OrderStatus.COLLECTING
                                self.last_prompted_slot = None
                                extraction_result["form_complete"] = False
                                extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {mapped}\n\n" + self._generate_response(extraction_result)
                            return extraction_result
                        else:
                            # 清空last_prompted_slot，让_generate_response重新设置下一个
                            self.last_prompted_slot = None
                            extraction_result["form_complete"] = self._check_form_completeness()
                            extraction_result["response"] = self._generate_response(extraction_result)
                            return extraction_result
                    else:
                        # 数字无法映射到选项，给出错误提示（不继续走LLM）
                        invalid_template = business_config_loader.get_template(self.business_line, "form_invalid_option")
                        extraction_result["response"] = "\n".join(invalid_template) if invalid_template else "无该选项，请输入有效序号或重新描述。"
                        return extraction_result
                elif sd and not sd.enums_key:
                    # 自由文本输入槽位（如联系方式），纯数字也直接接受
                    sv = SlotValue(stripped, 1.0, "free_text", "自由输入")
                    update_result = self._update_slot(target_slot, sv)
                    if update_result["updated"]:
                        extraction_result["slots_updated"].append(target_slot)
                    if update_result["filled"]:
                        extraction_result["slots_filled"].append(target_slot)
                    
                    # 如果是重选模式，完成后检查表单完整性
                    if self.order_status == OrderStatus.RESELECTING:
                        self.reselect_slot = None
                        # 检查是否还有空槽位
                        if self._check_form_completeness():
                            # 表单完整，跳到确认状态
                            self.order_status = OrderStatus.READY_CONFIRM
                            self.last_prompted_slot = None
                            extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {stripped}\n\n" + self._generate_order_summary() + "\n\n" + self._generate_confirmation_options()
                        else:
                            # 表单不完整，继续收集
                            self.order_status = OrderStatus.COLLECTING
                            self.last_prompted_slot = None
                            extraction_result["form_complete"] = False
                            extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {stripped}\n\n" + self._generate_response(extraction_result)
                        return extraction_result
                    else:
                        # 清空last_prompted_slot，让_generate_response重新设置下一个
                        self.last_prompted_slot = None
                        extraction_result["form_complete"] = self._check_form_completeness()
                        extraction_result["response"] = self._generate_response(extraction_result)
                        return extraction_result
                # 如果没有 enums_key，说明是自由文本输入（如联系方式），不处理纯数字，继续往下走

        # 唯一匹配：仅针对最近提示槽位，且输入不是纯数字
        if self.last_prompted_slot and not stripped.isdigit() and not self.awaiting_conflict_slot:
            sd = self.form_template.get(self.last_prompted_slot)
            
            # 检查是否有 enums_key，如果没有说明是自由文本输入（如联系方式）
            if sd and sd.enums_key:
                enum_key = sd.enums_key
                hits = collect_matches(enum_key, stripped)
                if len(hits) == 1:
                    uniq = hits[0]
                    sv = SlotValue(uniq, 0.75, "single_match", "唯一匹配")
                    update_result = self._update_slot(self.last_prompted_slot, sv)
                    if update_result["updated"]:
                        extraction_result["slots_updated"].append(self.last_prompted_slot)
                    if update_result["filled"]:
                        extraction_result["slots_filled"].append(self.last_prompted_slot)
                    
                    # 如果是重选模式，完成后检查表单完整性
                    if self.order_status == OrderStatus.RESELECTING:
                        target_slot = self.last_prompted_slot
                        self.reselect_slot = None
                        # 检查是否还有空槽位
                        if self._check_form_completeness():
                            # 表单完整，跳到确认状态
                            self.order_status = OrderStatus.READY_CONFIRM
                            self.last_prompted_slot = None
                            extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {uniq}\n\n" + self._generate_order_summary() + "\n\n" + self._generate_confirmation_options()
                        else:
                            # 表单不完整，继续收集
                            self.order_status = OrderStatus.COLLECTING
                            self.last_prompted_slot = None
                            extraction_result["form_complete"] = False
                            extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {uniq}\n\n" + self._generate_response(extraction_result)
                        return extraction_result
                    else:
                        # 清空last_prompted_slot，让_generate_response重新设置下一个
                        self.last_prompted_slot = None
                        extraction_result["form_complete"] = self._check_form_completeness()
                        extraction_result["response"] = self._generate_response(extraction_result)
                        return extraction_result
                elif len(hits) > 1:
                    # 歧义提示
                    ambiguous_template = business_config_loader.get_template(self.business_line, "form_ambiguous_match")
                    if ambiguous_template:
                        msg = "\n".join(ambiguous_template).replace("{matches}", ", ".join(hits))
                    else:
                        msg = "⚠️ 检测到多个可能匹配: " + ", ".join(hits) + "\n请更具体描述或输入序号选择。"
                    extraction_result["response"] = msg
                    return extraction_result
            elif sd and not sd.enums_key:
                # 自由文本输入槽位（如联系方式），直接接受用户输入
                sv = SlotValue(stripped, 1.0, "free_text", "自由输入")
                update_result = self._update_slot(self.last_prompted_slot, sv)
                if update_result["updated"]:
                    extraction_result["slots_updated"].append(self.last_prompted_slot)
                if update_result["filled"]:
                    extraction_result["slots_filled"].append(self.last_prompted_slot)
                
                # 如果是重选模式，完成后检查表单完整性
                if self.order_status == OrderStatus.RESELECTING:
                    target_slot = self.last_prompted_slot
                    self.reselect_slot = None
                    # 检查是否还有空槽位
                    if self._check_form_completeness():
                        # 表单完整，跳到确认状态
                        self.order_status = OrderStatus.READY_CONFIRM
                        self.last_prompted_slot = None
                        extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {stripped}\n\n" + self._generate_order_summary() + "\n\n" + self._generate_confirmation_options()
                    else:
                        # 表单不完整，继续收集
                        self.order_status = OrderStatus.COLLECTING
                        self.last_prompted_slot = None
                        extraction_result["form_complete"] = False
                        extraction_result["response"] = f"✅ 已更新：{self.current_form[target_slot].definition.description} -> {stripped}\n\n" + self._generate_response(extraction_result)
                    return extraction_result
                else:
                    # 清空last_prompted_slot，让_generate_response重新设置下一个
                    self.last_prompted_slot = None
                    extraction_result["form_complete"] = self._check_form_completeness()
                    extraction_result["response"] = self._generate_response(extraction_result)
                    return extraction_result

        # 通用命令处理（从配置加载命令关键词）
        normalized = user_input.strip().lower()
        
        # 获取通用命令关键词（如果配置中没有，使用默认值）
        confirm_keywords = self._get_command_keywords("confirm", ["确认", "确认订单", "下单", "提交", "提交订单", "ok", "yes"])
        reselect_keywords = self._get_command_keywords("reselect", ["重选", "修改", "重新选择", "change", "edit"])
        restart_keywords = self._get_command_keywords("restart", ["继续购物", "重新开始", "再选一个", "restart", "reset"])
        
        # 处理重选命令
        if self.order_status == OrderStatus.READY_CONFIRM:
            if normalized in reselect_keywords:
                extraction_result["response"] = self._generate_reselect_options()
                return extraction_result
            elif normalized in restart_keywords:
                self._reset_form()
                next_slot = self._get_next_missing_slot()
                if next_slot:
                    self.last_prompted_slot = next_slot
                    extraction_result["response"] = "好的！让我们重新开始选择～\n\n" + self._generate_slot_prompt(next_slot)
                else:
                    extraction_result["response"] = "系统错误：无法找到下一个槽位"
                return extraction_result
        
        # 确认动作：当用户输入确认并且表单完整且无验证错误
        if normalized in confirm_keywords and self.order_status == OrderStatus.READY_CONFIRM:
            # 若还未完成或存在错误给出提示
            if not self._check_form_completeness():
                incomplete_template = business_config_loader.get_template(self.business_line, "form_info_incomplete")
                incomplete_msg = "\n".join(incomplete_template) if incomplete_template else "信息尚未完整，请继续补充："
                extraction_result["response"] = incomplete_msg + " " + ", ".join([
                    name for name, slot in self.current_form.items() if slot.definition.required and slot.status == SlotStatus.EMPTY
                ])
                return extraction_result
            # 再次运行验证器，确保最新组合合法
            from core.slot_validators import run_validators
            context_view = {n: s.value.value for n, s in self.current_form.items() if s.value}
            errors = run_validators(context_view)
            if errors:
                self.validation_errors = errors
                error_title_template = business_config_loader.get_template(self.business_line, "form_validation_error_title")
                error_footer_template = business_config_loader.get_template(self.business_line, "form_validation_error_footer")
                error_title = "\n".join(error_title_template) if error_title_template else "❓ 某些组合暂时不太合适："
                error_footer = "\n".join(error_footer_template) if error_footer_template else "可以调整相关项后再试一下～"
                extraction_result["response"] = error_title + "\n" + "\n".join(f"- {e}" for e in errors) + "\n" + error_footer
                return extraction_result
            # 生成订单摘要
            summary_lines = []
            for name, slot in self.current_form.items():
                if slot.status == SlotStatus.FILLED:
                    summary_lines.append(f"  • {slot.definition.description}: {slot.value.value}")
            self.order_confirmed = True
            self.order_status = OrderStatus.AWAITING_CONTINUE  # 设置为等待继续状态
            self.order_summary = {n: s.value.value for n, s in self.current_form.items() if s.value}
            
            # 使用知识库的人性化确认模板
            confirm_template = business_config_loader.get_template(self.business_line, "form_order_confirmed")
            thanks_template = business_config_loader.get_template(self.business_line, "form_order_thanks")
            
            response_parts = []
            if confirm_template:
                response_parts.extend(confirm_template)
            else:
                response_parts.append("✅ 订单已确认！")
            
            response_parts.append("")
            response_parts.extend(summary_lines)
            
            if thanks_template:
                response_parts.append("")
                response_parts.extend(thanks_template)
            
            response_text = "\n".join(response_parts)
            extraction_result["response"] = response_text
            return extraction_result
        
        # 1. 多槽位信息抽取
        extracted_info = self._extract_multiple_slots(user_input, llm_client, semantic_mapper)
        
        # 2. 更新表单（一旦检测到冲突，立即中断，不再处理其他槽位）
        for slot_name, slot_value in extracted_info.items():
            if slot_name in self.current_form:
                update_result = self._update_slot(slot_name, slot_value)
                if update_result["updated"]:
                    extraction_result["slots_updated"].append(slot_name)
                if update_result["filled"]:
                    extraction_result["slots_filled"].append(slot_name)
                if update_result["conflict"]:
                    conflict_record = {
                        "slot": slot_name,
                        "existing": self.current_form[slot_name].value,
                        "new": slot_value
                    }
                    extraction_result["conflicts"].append(conflict_record)
                    self.pending_conflicts.append(conflict_record)
                    self.awaiting_conflict_slot = slot_name
                    # 检测到冲突，立即中断，不再处理其他槽位
                    break
        
        # 3. 先检查表单完整性（供响应生成阶段使用）
        extraction_result["form_complete"] = self._check_form_completeness()
        # 4. 再生成响应（这样完成状态可触发验证器）
        extraction_result["response"] = self._generate_response(extraction_result)
        
        return extraction_result
    
    def _extract_multiple_slots(self, user_input: str, llm_client, semantic_mapper) -> Dict[str, SlotValue]:
        """从用户输入中抽取多个槽位信息
        
        三层提取策略：
        Layer 1 (精确匹配): 直接关键词/别名匹配，高置信度
        Layer 2 (智能推荐): 基于用户意图和上下文的语义理解推荐
        Layer 3 (兜底识别): LLM全局理解，处理复杂/模糊表达
        """
        extracted = {}
        
        # Layer 1: 直接关键词匹配（仅扫描缺失槽位，避免干扰已填充槽位）
        direct_matches = self._direct_keyword_extraction(user_input)
        extracted.update(direct_matches)
        
        # Layer 2: 智能推荐层 - 基于意图理解推荐选项
        # 这一层处理用户的隐含需求，如"做视频剪辑"→推荐高性能配置
        missing_slots = [name for name, slot in self.current_form.items() 
                        if slot.status == SlotStatus.EMPTY and name not in extracted]
        
        for slot_name in missing_slots:
            # 优先使用semantic_stage动态过滤（如芯片根据系列过滤）
            semantic_result = self._semantic_slot_extraction(user_input, slot_name, semantic_mapper)
            if semantic_result:
                extracted[slot_name] = semantic_result
                continue
            
            # 如果没有semantic_stage配置，尝试基于意图的智能推荐
            intent_result = self._intent_based_recommendation(user_input, slot_name)
            if intent_result:
                extracted[slot_name] = intent_result
        
        # Layer 3: LLM 全局抽取（处理复杂表达和多槽位识别）
        all_missing_slots = [name for name, slot in self.current_form.items() 
                            if slot.status == SlotStatus.EMPTY]
        llm_result = self._llm_slot_extraction(user_input, all_missing_slots, llm_client)
        for slot_name, slot_value in llm_result.items():
            if slot_name not in extracted:  # 优先级：精确匹配 > 智能推荐 > LLM兜底
                extracted[slot_name] = slot_value
                
        return extracted
    
    def _direct_keyword_extraction(self, user_input: str) -> Dict[str, SlotValue]:
        """
        直接关键词识别层 - 从业务配置动态加载别名进行匹配
        支持中文/英文/数字混合匹配，减少LLM调用
        使用上下文消歧策略：优先匹配当前缺失的槽位
        
        优化：仅扫描缺失槽位，避免干扰已填充的槽位
        """
        extracted = {}
        text_lower = user_input.lower().strip()
        
        # 从当前业务配置获取所有枚举定义
        enums = business_config_loader.get_enums(self.business_line)
        
        # 仅收集缺失槽位的候选结果
        candidates = {}  # {slot_name: [(label, confidence, reason, match_length)]}
        
        # 遍历表单槽位定义，仅检查缺失的槽位
        for slot_name, slot_def in self.form_template.items():
            # 【优化】跳过已填充的槽位
            if self.current_form[slot_name].status != SlotStatus.EMPTY:
                continue
            
            # 获取该槽位对应的枚举key
            enum_key = slot_def.enums_key if slot_def.enums_key else slot_name
            enum_list = enums.get(enum_key, [])
            
            if not isinstance(enum_list, list):
                continue
            
            for enum_item in enum_list:
                if not isinstance(enum_item, dict):
                    continue
                
                label = enum_item.get("label", "")
                aliases = enum_item.get("aliases", [])
                
                # 检查是否匹配任何别名（精确匹配，避免子串误匹配）
                matched = False
                matched_keyword = None
                best_match_length = 0
                
                for alias in aliases:
                    alias_lower = alias.lower()
                    # 精确匹配：要么完全相等，要么作为独立词出现
                    import re
                    # 匹配条件：完全相等 OR 前后有边界
                    if text_lower == alias_lower:
                        # 完全匹配，优先级最高
                        matched = True
                        matched_keyword = alias
                        break
                    elif len(alias_lower) > best_match_length:
                        # 作为子串匹配，但要确保前后是边界
                        pattern = r'(^|[^a-z0-9])' + re.escape(alias_lower) + r'($|[^a-z0-9])'
                        if re.search(pattern, text_lower):
                            matched = True
                            matched_keyword = alias
                            best_match_length = len(alias_lower)
                
                if matched:
                    # 特殊处理：避免 "pro"/"air" 在series槽位的误匹配
                    # 如果是系列名且关键词是短词，要求更严格的匹配
                    if slot_name == "series" and matched_keyword and matched_keyword.lower() in ["pro", "air"]:
                        # 要求完整系列名匹配（如 "macbook pro" 或 "ipad pro"）
                        full_series_matched = False
                        for alias in aliases:
                            if len(alias.split()) > 1 and alias.lower() in text_lower:
                                full_series_matched = True
                                break
                        if not full_series_matched:
                            continue
                    
                    # 计算匹配置信度（所有扫描的都是缺失槽位）
                    confidence = 0.95  # 高置信度，因为是精确别名匹配
                    
                    # 收集候选结果（同一槽位可能有多个匹配）
                    if slot_name not in candidates:
                        candidates[slot_name] = []
                    candidates[slot_name].append((
                        label,
                        confidence,
                        f"关键词'{matched_keyword}'匹配",
                        best_match_length
                    ))
                    
        
        # 消歧选择：每个槽位选择最佳匹配
        for slot_name, matches in candidates.items():
            if not matches:
                continue
            
            # 选择策略：按匹配长度（更具体）和置信度排序
            best_match = max(matches, key=lambda x: (x[3], x[1]))
            
            label, confidence, reason, _ = best_match
            extracted[slot_name] = SlotValue(label, confidence, "direct", reason)
            
            # 系列匹配时自动推断 category 和 brand
            if slot_name == "series" and "category" not in extracted:
                inferred_category = self._infer_category_from_series(label)
                if inferred_category:
                    extracted["category"] = SlotValue(
                        inferred_category, 0.85, "direct", "从系列推断"
                    )
                    extracted["brand"] = SlotValue(
                        "苹果", 0.85, "direct", "从系列推断"
                    )
        
        return extracted
    
    def _infer_category_from_series(self, series_name: str) -> Optional[str]:
        """从产品系列推断大类"""
        # 使用self.business_filters（已在__init__中加载）
        series_by_category = self.business_filters.get("series_by_category", {})
        
        for category, series_list in series_by_category.items():
            if series_name in series_list:
                return category
        return None
    
    def _validate_enum_value(self, slot_name: str, value: str, enum_key: str) -> Optional[str]:
        """
        验证值是否在槽位的有效枚举选项中
        返回规范化后的值，如果无效则返回None
        """
        # 获取枚举选项
        options = get_slot_options(enum_key, self.business_line)
        if not options:
            # 没有枚举定义，接受任何值
            return value
        
        value_lower = value.lower().strip()
        
        # 1. 精确匹配label
        for opt in options:
            if opt.get("label", "").lower() == value_lower:
                return opt["label"]
        
        # 2. 模糊匹配别名（使用精确边界匹配）
        import re
        best_match_label = None
        best_match_length = 0
        
        for opt in options:
            label = opt.get("label", "")
            label_lower = label.lower()
            aliases = opt.get("aliases", [])
            
            # 检查别名精确匹配
            for alias in aliases:
                alias_lower = alias.lower()
                # 完全相等
                if alias_lower == value_lower:
                    return label
                # 词边界匹配（避免"m3"匹配"m3 pro"）
                elif len(alias_lower) > best_match_length:
                    pattern = r'(^|[^a-z0-9])' + re.escape(alias_lower) + r'($|[^a-z0-9])'
                    if re.search(pattern, value_lower):
                        best_match_label = label
                        best_match_length = len(alias_lower)
            
            # Label完全相等
            if label_lower == value_lower and len(label_lower) > best_match_length:
                best_match_label = label
                best_match_length = len(label_lower)
        
        if best_match_label:
            return best_match_label
        
        # 没有匹配，返回None表示无效
        return None
    
    def _semantic_slot_extraction(self, user_input: str, slot_name: str, semantic_mapper) -> Optional[SlotValue]:
        """使用 SlotDefinition.semantic_stage + 当前上下文的语义映射层"""
        sd = self.form_template.get(slot_name)
        if not sd or not sd.semantic_stage:
            return None
        context_view = {n: s.value.value for n, s in self.current_form.items() if s.value}
        context_view["_manager"] = self
        options = OptionBuilder.build(sd.semantic_stage, context_view)
        if not options:
            return None
        match_result = semantic_mapper.map(user_input, options)
        if match_result.chosen_index is None:
            return None
        chosen_opt = options[match_result.chosen_index - 1]
        return SlotValue(
            value=chosen_opt.label,
            confidence=match_result.confidence,
            source="semantic",
            reason=match_result.reason
        )
    
    def _intent_based_recommendation(self, user_input: str, slot_name: str) -> Optional[SlotValue]:
        """基于用户意图的智能推荐（从配置文件加载）
        
        识别用户的使用场景和需求，推荐最合适的配置选项
        例如：
        - "做视频剪辑" → 推荐M3 Pro/Max, 1TB+存储
        - "轻办公" → 推荐M3标准版, 512GB存储
        - "随身携带" → 推荐13寸
        """
        # 新增：检查槽位依赖是否满足
        slot_def = self.form_template.get(slot_name)
        if slot_def and slot_def.dependencies:
            for dep_name in slot_def.dependencies:
                dep_slot = self.current_form.get(dep_name)
                if not dep_slot or dep_slot.status != SlotStatus.FILLED:
                    # 依赖未满足，不进行意图推荐
                    return None
                
        text_lower = user_input.lower()
        
        # 获取槽位定义
        slot_def = self.form_template.get(slot_name)
        if not slot_def or not slot_def.enums_key:
            return None
        
        # 从配置文件加载意图映射
        intent_recommendations = business_config_loader.get_intent_recommendations(self.business_line)
        slot_intents = intent_recommendations.get(slot_name, [])
        
        if not slot_intents:
            return None
        
        # 检测用户意图
        for intent_config in slot_intents:
            keywords = intent_config.get("keywords", [])
            for keyword in keywords:
                if keyword in text_lower:
                    recommended = intent_config.get("recommend")
                    confidence = intent_config.get("confidence", 0.7)
                    reason = intent_config.get("reason", "意图推荐")
                    
                    # 验证推荐值是否在有效枚举中
                    if self._validate_enum_value(slot_name, recommended, slot_def.enums_key):
                        return SlotValue(
                            value=recommended,
                            confidence=confidence,
                            source="intent_recommend",
                            reason=reason
                        )
        
        return None
    
    def _llm_slot_extraction(self, user_input: str, target_slots: List[str], llm_client) -> Dict[str, SlotValue]:
        """LLM 多槽位抽取 - LLM会自动推断和规范化值"""
        if not target_slots:
            return {}
        if not llm_client:
            print("🤖 LLM客户端未初始化，跳过AI分析")
            return {}
        
        # 过滤掉依赖未满足的槽位
        valid_target_slots = []
        for slot_name in target_slots:
            slot_def = self.form_template.get(slot_name)
            if slot_def and slot_def.dependencies:
                dependencies_met = all(
                    self.current_form.get(dep) and 
                    self.current_form[dep].status == SlotStatus.FILLED
                    for dep in slot_def.dependencies
                )
                if not dependencies_met:
                    continue  # 跳过依赖未满足的槽位
            valid_target_slots.append(slot_name)
        
        if not valid_target_slots:
            return {}
        
        # 只向 LLM 请求 allow_llm=true 的槽位
        llm_allowed_slots = [s for s in valid_target_slots if self.form_template.get(s) and self.form_template[s].allow_llm]
        # 只向 LLM 请求 allow_llm=true 的槽位
        if not llm_allowed_slots:
            return {}
        
        current_values = {n: s.value.value for n, s in self.current_form.items() if s.status == SlotStatus.FILLED and s.value}
        raw_result = {}
        print(f"🤖 正在用AI分析: '{user_input}' (目标槽位: {llm_allowed_slots})")
        try:
            raw_result = llm_client.extract_slots(user_input, self.business_line, llm_allowed_slots, current_values)
            print(f"🤖 AI分析结果: {raw_result}")
        except Exception as e:
            print(f"🤖 LLM抽取异常: {e}")
            raw_result = {}
        
        converted: Dict[str, SlotValue] = {}
        for slot, info in raw_result.items():
            # 检查槽位是否存在于表单中
            if slot not in self.form_template:
                print(f"⚠️ LLM返回了未知槽位: {slot}，已忽略")
                continue
            
            slot_def = self.form_template[slot]
            
            # 检查槽位是否允许LLM填充
            if not slot_def.allow_llm:
                print(f"⚠️ LLM返回了禁止AI填充的槽位: {slot}({slot_def.description})，已忽略")
                continue
            
            val = info.get("value")
            conf = info.get("confidence", 0.0)
            
            # 跳过空值或低置信度的结果
            if not val or not isinstance(val, str) or val.strip() == "":
                continue
            if not isinstance(conf, (int, float)) or conf < 0.35:
                continue
            
            # 验证LLM返回的值是否在有效枚举选项中
            if slot_def.enums_key:
                valid_value = self._validate_enum_value(slot, val.strip(), slot_def.enums_key)
                if not valid_value:
                    print(f"⚠️ LLM返回了无效的{slot_def.description}值: '{val}'，已忽略")
                    continue
                # 使用验证后的规范化值
                val = valid_value
            
            # LLM 已经完成了规范化，直接使用返回值
            source = "multi_llm" if len(raw_result) > 1 else "llm"
            converted[slot] = SlotValue(value=val.strip(), confidence=conf, source=source, reason=info.get("reason", "AI智能分析"))
        
        # 显示LLM分析过程
        if converted:
            extracted_count = len(converted)
            print(f"🤖 AI同时识别了 {extracted_count} 个信息项")
        
        return converted
    
    def _update_slot(self, slot_name: str, new_value: SlotValue) -> Dict[str, bool]:
        """更新槽位值，处理冲突 - 同时清除相关验证错误"""
        slot = self.current_form[slot_name]
        result = {"updated": False, "filled": False, "conflict": False}
        
        # 新增：在更新槽位时清除相关的验证错误
        if slot_name in ["chip", "storage", "size", "series"]:  # 与验证相关的槽位
            self.validation_errors = []  # 清除所有验证错误
            print(f"🔄 已清除验证错误（更新了 {slot_name}）")
        if slot.status == SlotStatus.EMPTY:
            # 空槽位直接填充
            slot.value = new_value
            slot.status = SlotStatus.FILLED if new_value.confidence >= 0.7 else SlotStatus.PARTIAL
            result["updated"] = True
            result["filled"] = (slot.status == SlotStatus.FILLED)
        
        elif slot.status == SlotStatus.FILLED:
            # 已填充槽位需要检查冲突
            if self._should_trigger_conflict(slot.value, new_value):
                # 存在冲突，保存候选值并标记冲突状态
                slot.candidates.append(new_value)
                slot.status = SlotStatus.CONFLICTED
                result["conflict"] = True
            else:
                # 相同值或兼容值，更新置信度或保持原值
                if slot.value.value == new_value.value:
                    # 相同值，提高置信度
                    slot.value.confidence = min(1.0, slot.value.confidence + 0.1)
                    result["updated"] = True
                else:
                    # 不同值但不触发冲突（例如低置信度），忽略新值
                    pass
        
        elif slot.status == SlotStatus.CONFLICTED:
            # 已处于冲突状态，添加到候选列表
            if not any(c.value == new_value.value for c in slot.candidates):
                slot.candidates.append(new_value)
        
        return result
    
    def _should_trigger_conflict(self, existing_value: SlotValue, new_value: SlotValue) -> bool:
        """判断是否应该触发冲突处理机制"""
        # 如果值相同，不冲突
        if existing_value.value == new_value.value:
            return False
        
        # 用户明确选择保护：如果现有值是用户明确选择的，AI不能覆盖
        user_explicit_sources = {
            "numeric",      # 数字选择
            "direct",       # 直接关键词匹配
            "single_match", # 唯一匹配
            "semantic",     # 语义映射
            "intent_recommend"  # 意图推荐（用户接受了推荐）
        }
        
        ai_sources = {
            "llm",          # 单个LLM识别
            "multi_llm"     # 多槽位LLM识别
        }
        
        # 保护原则：用户明确选择不能被AI覆盖
        if (existing_value.source in user_explicit_sources and 
            new_value.source in ai_sources):
            print(f"🛡️ 保护用户明确选择: {existing_value.value}({existing_value.source}) "
                f"不被AI识别覆盖: {new_value.value}({new_value.source})")
            return False
        
            
        # 冲突触发策略：
        # 1. 高置信度的新值与现有值不同
        if new_value.confidence >= 0.6:
            return True
            
        # 2. 不同来源的值（特别是AI vs 直接识别）
        source_priorities = {
            "direct": 3,      # 直接关键词匹配
            "numeric": 2,     # 数字选择
            "semantic": 2,    # 语义映射  
            "llm": 1,         # 单个LLM识别
            "multi_llm": 1,   # 多槽位LLM识别
            "single_match": 2 # 唯一匹配
        }
        
        existing_priority = source_priorities.get(existing_value.source, 0)
        new_priority = source_priorities.get(new_value.source, 0)
        
        # 如果新值优先级足够高，且置信度不是太低，触发冲突
        if new_priority >= existing_priority and new_value.confidence >= 0.4:
            return True
            
        # 3. 特殊情况：AI识别与直接识别冲突时，总是提示用户确认
        if (existing_value.source == "direct" and new_value.source in ["llm", "multi_llm"]) or \
           (existing_value.source in ["llm", "multi_llm"] and new_value.source == "direct"):
            return True
            
        return False

    def _resolve_conflict(self, slot_name: str, decision: str):
        """
        根据用户决策处理冲突: 1 保留原值 2 使用新值 3 清空重新说明
        
        新策略：选择"2 使用新值"或"3 清空重新说明"时，清空该槽位及其依赖链，
        避免多值同步问题，让用户重新填充
        """
        slot = self.current_form.get(slot_name)
        if not slot:
            self.awaiting_conflict_slot = None
            return
            
        old_value = slot.value.value if slot.value else "(无)"
        
        if decision == "1":
            # 保留原值，丢弃候选
            slot.status = SlotStatus.FILLED
            slot.candidates = []
            print(f"✅ 保留原值: {slot.definition.description} = {old_value}")
            
        elif decision == "2":
            # 使用新值：清空该槽位及其依赖链，然后填充新值
            if slot.candidates:
                new_val = slot.candidates[-1]
                
                # 先清空依赖链（避免旧值残留）
                self._clear_slot_and_dependencies(slot_name)
                
                # 填充新值
                slot.value = new_val
                slot.status = SlotStatus.FILLED if new_val.confidence >= 0.7 else SlotStatus.PARTIAL
                slot.candidates = []
                
                source_prefix = self._get_source_prefix(new_val.source)
                print(f"✅ 已更新: {source_prefix}{slot.definition.description} = {new_val.value}")
                print(f"🔄 已清空 {slot.definition.description} 的依赖项，请重新填充")
            else:
                slot.candidates = []
                
        elif decision == "3":
            # 清空该槽位及其依赖链，等待重新输入
            self._clear_slot_and_dependencies(slot_name)
            print(f"🔄 已清空 {slot.definition.description} 及其依赖项，请重新输入")
        
        # 清理冲突状态
        self.awaiting_conflict_slot = None
        # 移除对应 pending_conflicts
        self.pending_conflicts = [c for c in self.pending_conflicts if c.get("slot") != slot_name]
    
    def _generate_response(self, extraction_result: Dict[str, Any]) -> str:
        """生成回复消息"""
        response_parts = []
        
        # 确认收到的信息（带来源标识）
        if extraction_result["slots_updated"]:
            filled_info = []
            for slot_name in extraction_result["slots_updated"]:
                slot = self.current_form[slot_name]
                source_prefix = self._get_source_prefix(slot.value.source)
                filled_info.append(f"{source_prefix}{slot.definition.description}: {slot.value.value}")
            if filled_info:
                recorded_template = business_config_loader.get_template(self.business_line, "form_info_recorded")
                recorded_msg = "\n".join(recorded_template) if recorded_template else "✅ 好的，我记下啦："
                response_parts.append(recorded_msg + "\n" + "\n".join(f"   {info}" for info in filled_info))
        
        # 处理冲突 - 增强用户体验
        if extraction_result["conflicts"]:
            for conflict in extraction_result["conflicts"]:
                slot_name = conflict["slot"]
                slot = self.current_form[slot_name]
                existing_sv = conflict.get("existing")
                new_sv = conflict.get("new")
                
                old_val = existing_sv.value if existing_sv else "(空)"
                new_val = new_sv.value if new_sv else "(无)"
                
                # 生成来源描述
                old_source = self._get_source_description(existing_sv.source) if existing_sv else "未知"
                new_source = self._get_source_description(new_sv.source) if new_sv else "未知"
                
                # 使用模板构建冲突消息
                intro_template = business_config_loader.get_template(self.business_line, "form_conflict_intro")
                existing_template = business_config_loader.get_template(self.business_line, "form_conflict_existing")
                new_template = business_config_loader.get_template(self.business_line, "form_conflict_new")
                options_template = business_config_loader.get_template(self.business_line, "form_conflict_options")
                
                conflict_parts = []
                if intro_template:
                    conflict_parts.append("\n".join(intro_template).replace("{slot_desc}", slot.definition.description))
                else:
                    conflict_parts.append(f"🤔 关于 {slot.definition.description} 我看到两个可能：")
                
                if existing_template:
                    conflict_parts.append("\n".join(existing_template).replace("{old_value}", old_val).replace("{old_source}", old_source))
                else:
                    conflict_parts.append(f"   现有：{old_val}（{old_source}）")
                
                if new_template:
                    conflict_parts.append("\n".join(new_template).replace("{new_value}", new_val).replace("{new_source}", new_source))
                else:
                    conflict_parts.append(f"   新识别：{new_val}（{new_source}）")
                
                if options_template:
                    conflict_parts.append("\n".join(options_template))
                else:
                    conflict_parts.append("输入 1 保留现有 | 2 用新识别 | 3 我再说一次")
                
                conflict_msg = "\n".join(conflict_parts)
                response_parts.append(conflict_msg)
                # 冲突时立即返回提示，不再追加其它内容
                return "\n\n".join(response_parts)
        
        # 询问缺失信息 - 考虑依赖关系
        # 按照form_template定义的顺序获取缺失的必填槽位
        missing_required = []
        for slot_name in self.form_template.keys():
            slot = self.current_form.get(slot_name)
            if slot and slot.definition.required and slot.status == SlotStatus.EMPTY:
                missing_required.append(slot_name)
        
        if missing_required and not extraction_result["form_complete"]:
            # 选择下一个可填充的槽位（满足依赖条件）
            next_slot_name = self._get_next_available_slot(missing_required)
            if next_slot_name:
                # 生成针对性问题
                prompt = self._generate_slot_prompt(next_slot_name)
                response_parts.append(prompt)
                # 记录最近提示槽位用于数字选择
                self.last_prompted_slot = next_slot_name
            else:
                # 理论上不应该发生，但作为兜底
                continue_template = business_config_loader.get_template(self.business_line, "form_continue_filling")
                response_parts.append("\n".join(continue_template) if continue_template else "我们继续完善其它信息吧～")
                self.last_prompted_slot = missing_required[0] if missing_required else None
        
        elif extraction_result["form_complete"]:
            # 在完成前运行验证器
            from core.slot_validators import run_validators
            context_view = {n: s.value.value for n, s in self.current_form.items() if s.value}
            errors = run_validators(context_view)
            if errors:
                self.validation_errors = errors
                error_title_template = business_config_loader.get_template(self.business_line, "form_validation_error_title")
                error_footer_template = business_config_loader.get_template(self.business_line, "form_validation_error_footer")
                error_title = "\n".join(error_title_template) if error_title_template else "😮 某些组合暂时不太合适："
                error_footer = "\n".join(error_footer_template) if error_footer_template else "可以调整相关项后再试一下～"
                response_parts.append(error_title)
                response_parts.extend(f"- {msg}" for msg in errors)
                response_parts.append(error_footer)
            else:
                # 设置订单状态为准备确认
                self.order_status = OrderStatus.READY_CONFIRM
                # 显示完整订单信息和选项
                order_summary = self._generate_order_summary()
                response_parts.append(order_summary)
                response_parts.append(self._generate_confirmation_options())
        
        return "\n\n".join(response_parts)
    
    def _generate_slot_prompt(self, slot_name: str) -> str:
        """为特定槽位生成询问提示 (模板 + 动态过滤枚举 + 场景推荐)"""
        # 分类值用于动态选择模板
        category_val = None
        if self.current_form.get("category") and self.current_form["category"].value:
            category_val = self.current_form["category"].value.value

        template_key = f"form_{slot_name}_prompt"
        if slot_name == "series" and self.business_line == "apple_store":
            if category_val == "电脑":
                template_key = "form_series_prompt_computer"
            elif category_val == "手机":
                template_key = "form_series_prompt_phone"
            else:
                template_key = "form_series_prompt"
        
        template_lines = business_config_loader.get_template(self.business_line, template_key)
        sd = self.form_template.get(slot_name)
        enum_key = sd.enums_key if sd and sd.enums_key else slot_name
        options = self._get_filtered_options(enum_key)

        def _has_numbering(lines: List[str]) -> bool:
            return any(l.strip().startswith("1.") for l in lines)

        # 构造输出行集合
        out_lines: List[str] = []
        force_chip_enumerate = slot_name == "chip" and self.business_line == "apple_store" and category_val in {"手机", "平板"}
        if template_lines:
            if force_chip_enumerate:
                # 对手机/平板覆盖芯片模板，使用动态过滤枚举
                out_lines.append("请选择芯片：")
            else:
                out_lines.extend(template_lines)
                # 如果模板本身已有编号列表则不重复附加枚举
                if _has_numbering(template_lines):
                    return "\n".join(out_lines)
        # 如果没有模板或模板没有编号，附加枚举选项
        if options:
            filtered = options
            if enum_key == 'storage':
                # 根据类别过滤后再保留常见容量的简化列表（电脑不显示128/256）
                if category_val == "电脑":
                    filtered = [o for o in options if o['label'] in {'512GB','1TB','2TB'}]
                else:
                    filtered = options
            lines = [f"{i+1}. {opt['label']}" for i, opt in enumerate(filtered)]
            out_lines.extend(lines[:10])
        if out_lines:
            return "\n".join(out_lines)
        # 回退固定提示
        prompts = {
            "series": "先选一个系列：\n1. MacBook Air\n2. MacBook Pro\n3. iMac",
            "chip": "来挑芯片：\n1. M3\n2. M3 Pro\n3. M3 Max",
            "storage": "选存储大小：\n1. 512GB\n2. 1TB\n3. 2TB",
            "color": "选个颜色：\n1. 深空灰\n2. 银色\n3. 午夜色\n4. 星光色"
        }
        default_template = business_config_loader.get_template(self.business_line, "form_default_slot_prompt")
        if default_template:
            return "\n".join(default_template).replace("{slot_desc}", self.current_form[slot_name].definition.description)
        return prompts.get(slot_name, f"告诉我 {self.current_form[slot_name].definition.description} 哦～")

    def _business_numeric_map(self, enum_key: str, number: int) -> Optional[str]:
        """业务线作用域下的数字序号映射（避免统一业务枚举因全局前缀找不到）"""
        options = self._get_filtered_options(enum_key)
        if not options:
            return None
        filtered = options
        if enum_key == "storage":
            # 仅对展示的常规容量做序号映射，避免过多选项导致混乱
            filtered = [o for o in options if o.get("label") in {"256GB", "512GB", "1TB", "2TB"} or len(options) <= 6]
        if number < 1 or number > len(filtered):
            return None
        return filtered[number - 1].get("label")

    def _get_filtered_options(self, enum_key: str) -> List[Dict[str, Any]]:
        """根据已选的上游槽位（category / series / chip）动态过滤枚举选项"""
        raw = get_slot_options(enum_key, self.business_line)
        if not raw:
            return []
        # 只有苹果专卖店执行动态过滤，其他业务线保持原样
        if self.business_line != "apple_store":
            return raw
        # 获取当前已填值
        category = self.current_form.get("category").value.value if self.current_form.get("category") and self.current_form.get("category").value else None
        series = self.current_form.get("series").value.value if self.current_form.get("series") and self.current_form.get("series").value else None
        # 过滤逻辑映射
        series_groups = {k: set(v) for k, v in self.business_filters.get('series_by_category', {}).items()}
        size_by_category = {k: set(v) for k, v in self.business_filters.get('size_by_category', {}).items()}
        size_by_series = {k: set(v) for k, v in self.business_filters.get('size_by_series', {}).items()}
        chip_groups = {k: set(v) for k, v in self.business_filters.get('chip_by_category', {}).items()}
        storage_groups = {k: set(v) for k, v in self.business_filters.get('storage_by_category', {}).items()}
        
        if enum_key == "series" and category:
            allowed = series_groups.get(category)
            if allowed:
                return [o for o in raw if o.get("label") in allowed]
        
        if enum_key == "size":
            # 优先使用 series 级别的过滤，其次使用 category 级别
            if series:
                allowed = size_by_series.get(series)
                if allowed:
                    return [o for o in raw if o.get("label") in allowed]
            if category:
                allowed = size_by_category.get(category)
                if allowed:
                    return [o for o in raw if o.get("label") in allowed]
        
        if enum_key == "chip" and category:
            allowed = chip_groups.get(category)
            if allowed:
                return [o for o in raw if o.get("label") in allowed]
        if enum_key == "storage" and category:
            allowed = storage_groups.get(category)
            if allowed:
                return [o for o in raw if o.get("label") in allowed]
        # 颜色默认不做过滤
        return raw
    
    def _check_form_completeness(self) -> bool:
        """检查必填槽位是否全部填充"""
        for slot in self.current_form.values():
            if slot.definition.required and slot.status != SlotStatus.FILLED:
                return False
        return True
    
    def _get_filled_slots_summary(self) -> str:
        """获取已填充槽位的摘要"""
        filled = []
        for name, slot in self.current_form.items():
            if slot.status == SlotStatus.FILLED:
                filled.append(f"{slot.definition.description}: {slot.value.value}")
        return "; ".join(filled) if filled else "暂无"
    
    def get_form_status(self) -> Dict[str, Any]:
        """获取表单状态概览"""
        return {
            "total_slots": len(self.current_form),
            "filled_slots": len([s for s in self.current_form.values() if s.status == SlotStatus.FILLED]),
            "missing_required": [
                name for name, slot in self.current_form.items()
                if slot.definition.required and slot.status == SlotStatus.EMPTY
            ],
            "conflicts": [
                name for name, slot in self.current_form.items()
                if slot.status == SlotStatus.CONFLICTED
            ],
            "completion_rate": len([s for s in self.current_form.values() if s.status == SlotStatus.FILLED]) / len([s for s in self.current_form.values() if s.definition.required])
        }
    
    def _generate_order_summary(self) -> str:
        """生成订单摘要显示（显示所有必填槽位，未填充的显示'待填写'）"""
        title_template = business_config_loader.get_template(self.business_line, "form_order_summary_title")
        if title_template:
            summary_lines = title_template.copy()
        else:
            summary_lines = ["📝 您的订单信息："]
        summary_lines.append("=" * 30)
        
        # 显示所有必填槽位（包括EMPTY状态）
        for name, slot in self.current_form.items():
            if slot.definition.required:  # 只显示必填槽位
                if slot.status == SlotStatus.FILLED and slot.value:
                    summary_lines.append(f"• {slot.definition.description}: {slot.value.value}")
                elif slot.status == SlotStatus.EMPTY:
                    summary_lines.append(f"• {slot.definition.description}: 待填写")
        
        summary_lines.append("=" * 30)
        return "\n".join(summary_lines)
    
    def _generate_confirmation_options(self) -> str:
        """生成确认选项"""
        options_template = business_config_loader.get_template(self.business_line, "form_confirmation_options")
        if options_template:
            return "\n".join(options_template)
        else:
            return (
                "💬 请选择您的操作：\n"
                "1️⃣ 确认 - 确认订单并提交\n"
                "2️⃣ 重选 - 修改某个选项\n"
                "3️⃣ 继续购物 - 重新开始选择\n\n"
                "💬 可以直接输入序号或关键词（如：确认/重选/继续购物）"
            )
    
    def _generate_reselect_options(self) -> str:
        """生成重选选项列表"""
        title_template = business_config_loader.get_template(self.business_line, "form_reselect_title")
        if title_template:
            options_lines = title_template.copy()
        else:
            options_lines = ["🔄 请选择要修改的项目："]
        
        required_slots = [(name, slot) for name, slot in self.current_form.items() if slot.definition.required and slot.status == SlotStatus.FILLED]
        
        for i, (name, slot) in enumerate(required_slots, 1):
            current_value = slot.value.value if slot.value else "未设置"
            options_lines.append(f"{i}. {slot.definition.description}: {current_value}")
        
        
        footer_template = business_config_loader.get_template(self.business_line, "form_reselect_footer")
        if footer_template:
            options_lines.extend(footer_template)
        else:
            options_lines.append("\n💬 请输入要修改的项目序号")
        
        self.reselect_slot = "waiting"  # 标记正在等待重选
        return "\n".join(options_lines)
    
    def _clear_slot_and_dependencies(self, slot_name: str):
        """清空指定槽位及其所有下游依赖槽位 - 同时清除验证错误"""
        # 清空当前槽位
        self.current_form[slot_name].status = SlotStatus.EMPTY
        self.current_form[slot_name].value = None
        self.current_form[slot_name].candidates = []
        
        # 新增：清除验证错误
        self.validation_errors = []
        print(f"🔄 已清除验证错误（重选了 {slot_name}）")
        
        # 找出所有依赖于当前槽位的下游槽位并清空
        def clear_dependents(current_slot):
            for name, slot in self.current_form.items():
                if current_slot in slot.definition.dependencies:
                    # 清空这个依赖槽位
                    slot.status = SlotStatus.EMPTY
                    slot.value = None
                    slot.candidates = []
                    # 递归清空它的下游依赖
                    clear_dependents(name)
        
        clear_dependents(slot_name)
    
    def _reset_form(self):
        """重置表单到初始状态"""
        for slot in self.current_form.values():
            slot.status = SlotStatus.EMPTY
            slot.value = None
            slot.candidates = []
        
        self.pending_conflicts = []
        self.awaiting_conflict_slot = None
        self.validation_errors = []
        self.order_confirmed = False
        self.order_summary = {}
        self.order_status = OrderStatus.COLLECTING
        self.reselect_slot = None
        self.last_prompted_slot = None
    
    def _get_command_keywords(self, command_type: str, default_keywords: List[str]) -> set:
        """
        从配置获取命令关键词，如果配置中没有则使用默认值
        支持通用命令关键词配置，使系统更灵活
        """
        # 尝试从业务配置的 command_keywords 字段获取
        cfg = business_config_loader.get_business_config(self.business_line)
        if cfg and hasattr(cfg, 'command_keywords'):
            command_keywords = getattr(cfg, 'command_keywords', {})
            if command_type in command_keywords:
                return set(command_keywords[command_type])
        
        # 如果配置中没有，使用默认值
        return set(default_keywords)
    
    def _get_next_missing_slot(self) -> Optional[str]:
        """获取下一个缺失的必填槽位"""
        missing_required = [
            name for name, slot in self.current_form.items()
            if slot.definition.required and slot.status == SlotStatus.EMPTY
        ]
        return missing_required[0] if missing_required else None
    
    def _get_next_available_slot(self, missing_slots: List[str]) -> Optional[str]:
        """获取下一个可以填充的槽位（满足依赖条件）"""
        if not missing_slots:
            return None
            
        # 检查每个缺失槽位的依赖是否满足
        for slot_name in missing_slots:
            slot = self.current_form[slot_name]
            dependencies_satisfied = True
            
            # 检查所有依赖是否已填充
            for dep_name in slot.definition.dependencies:
                if dep_name in self.current_form:
                    dep_slot = self.current_form[dep_name]
                    if dep_slot.status != SlotStatus.FILLED:
                        dependencies_satisfied = False
                        break
            
            if dependencies_satisfied:
                return slot_name
        
        # 如果没有找到满足依赖的槽位，返回第一个（可能存在循环依赖或配置错误）
        return missing_slots[0]
    
    def _auto_fill_single_option_slots(self):
        """自动填充只有单一选项的槽位"""
        for slot_name, slot in self.current_form.items():
            if slot.status == SlotStatus.EMPTY and slot.definition.enums_key:
                enum_key = slot.definition.enums_key
                options = get_slot_options(enum_key, self.business_line)
                if len(options) == 1:
                    # 只有一个选项，自动填充
                    single_option = options[0]
                    slot_value = SlotValue(
                        value=single_option["label"],
                        confidence=1.0,
                        source="auto_single",
                        reason="业务线唯一选项"
                    )
                    slot.value = slot_value
                    slot.status = SlotStatus.FILLED
                    print(f"🤖 自动设置: {slot.definition.description} = {single_option['label']}")
    
    def _get_source_prefix(self, source: str) -> str:
        """获取判断来源的前缀标识（简化字母代码）"""
        source_prefixes = {
            "numeric": "(数字) ",
            "single_match": "(匹配) ",
            "direct": "(直接) ",
            "semantic": "(语义) ",
            "llm": "(LLM) ",
            "multi_llm": "(LLM) ",
            "auto_single": "(自动) ",
            "intent_recommend": "(推荐) "
        }
        return source_prefixes.get(source, "(未知) ")
    
    def _get_source_description(self, source: str) -> str:
        """获取来源的详细描述"""
        descriptions = {
            "direct": "关键词直接匹配",
            "numeric": "用户数字选择",
            "semantic": "语义智能映射", 
            "llm": "AI智能分析",
            "multi_llm": "AI多维度识别",
            "single_match": "唯一关键词匹配",
            "intent_recommend": "智能意图推荐" 
        }
        return descriptions.get(source, "未知识别方式")