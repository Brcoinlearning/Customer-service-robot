from core.interfaces import IInterpreter, IKnowledgeProvider
from knowledge.product_knowledge import ProductKnowledge
from typing import Dict, List, Any


class DSLInterpreter(IInterpreter):
    """支持记忆上下文的 DSL 解释器"""

    def __init__(self, parsed_dsl: Dict[str, Any]):
        self.intents = parsed_dsl["intents"]
        self.rules = parsed_dsl["rules"]
        # 动作类型到处理函数的映射，便于后续扩展新动作
        self._action_handlers = {
            "respond": self._handle_respond,
            "respond_kb": self._handle_respond_kb,
            "set_variable": self._handle_set_variable,
            "set_stage": self._handle_set_stage,
            "add_to_chain": self._handle_add_to_chain,
            "increment": self._handle_increment,
            "record_preference": self._handle_record_preference,
            "reset_shopping_context": self._handle_reset_shopping_context,
            # 基于知识库的动态推荐类动作
            "suggest_brands": self._handle_suggest_brands,
            "suggest_series": self._handle_suggest_series,
            "describe_series_config": self._handle_describe_series_config,
            "suggest_dates": self._handle_suggest_dates,
        }

    # 在 DSLInterpreter.execute() 方法中添加
    def execute(self, detected_intent: str, context: Dict[str, Any] = None) -> List[str]:
        """根据意图和上下文执行规则"""

        responses: List[str] = []
        context = context or {}
        current_stage = context.get('current_stage', 'welcome')
        user_text = str(context.get('user_input', '')).strip()
        manager = context.get('_manager')

        cart_stages = {"cart_added", "viewing_cart", "checkout"}
        if user_text:
            normalized_text = user_text.lower()
            if "取消" in normalized_text and context.get('current_stage') in {"final_confirm", "contact_collect", "budget_collect", "date_collect"}:
                detected_intent = "cancel"
            if "继续" in normalized_text and context.get('current_stage') in {"brand_select", "series_select", "config_select", "final_confirm"}:
                detected_intent = "booking_query"
            if current_stage in cart_stages and (
                user_text in {"1", "2", "3", "4", "5"} or
                normalized_text in {"继续", "继续购物", "继续看", "继续浏览", "再看看"}
            ):
                detected_intent = "cart_operation"

            # 通用输入验证系统 - 仅适用于需要数字选择的阶段
            numeric_choice_stages = [
                # 电商产品选择阶段
                "config_select", "storage_select", "color_select", "chip_select", "series_select",
                "phone_model_select", "phone_storage_select", "phone_color_select", 
                "size_select", "subtype_select", "brand_select",
                # 餐饮数字选择阶段
                "date_collect", "final_confirm"
                # 注意：details_collect, budget_collect, contact_collect 是自由文本输入，不需要验证
            ]
            if user_text and current_stage in numeric_choice_stages:
                validation_result = self._validate_stage_input(user_text, current_stage, context)
                if validation_result["valid"]:
                    # 有效输入：根据阶段类型处理
                    if current_stage == "config_select":
                        return self._process_valid_config_choice(user_text, context, manager)
                    # 其他阶段的有效输入让DSL规则处理
                    detected_intent = "product_query"
                else:
                    # 无效输入：返回阶段特定的引导信息，不改变状态
                    return validation_result["error_response"]

            # 在细节收集阶段支持人数与包间偏好
            if current_stage == "details_collect":
                knowledge = context.get("knowledge")
                text_lower = normalized_text
                if user_text.isdigit():
                    try:
                        party_size = int(user_text)
                        context["party_size"] = party_size
                        if manager:
                            manager.update_context("party_size", party_size)
                    except Exception:
                        context["party_size"] = None
                if any(k in text_lower for k in ["包间", "大厅"]):
                    private_room = "包间" if "包间" in text_lower else "大厅"
                    context["private_room"] = private_room
                    if manager:
                        manager.update_context("private_room", private_room)
                    # 已有private_room，应该进入日期选择阶段
                    # 让DSL规则处理，不直接返回

            # 日期收集阶段 - 支持数字选择和直接输入日期
            if current_stage == "date_collect" and user_text:
                selected_date = None
                if user_text.isdigit():
                    # 数字选择(1/2/3)
                    try:
                        idx = int(user_text) - 1
                        date_options = context.get("date_options", [])
                        if 0 <= idx < len(date_options):
                            selected_date = date_options[idx]
                    except Exception:
                        pass
                if not selected_date:
                    selected_date = user_text
                context["selected_date"] = selected_date
                if manager:
                    manager.update_context("selected_date", selected_date)

            if current_stage == "budget_collect" and user_text:
                context["budget"] = user_text
                if manager:
                    manager.update_context("budget", user_text)

            if current_stage == "contact_collect" and user_text:
                context["contact"] = user_text
                if manager:
                    manager.update_context("contact", user_text)

            # 在品牌选择阶段支持数字选择品牌
            if current_stage == "brand_select" and user_text.isdigit():
                knowledge = context.get("knowledge")
                category = context.get("current_category")
                if knowledge and category:
                    try:
                        brands = knowledge.get_brands_in_category(category)
                    except Exception:
                        brands = []
                    try:
                        idx = int(user_text) - 1
                        if 0 <= idx < len(brands):
                            brand = brands[idx]
                            manager = context.get('_manager')
                            if manager:
                                manager.update_context("current_brand", brand)
                                manager.add_to_chain("brand", brand)
                                manager.set_stage("series_select")
                            action = {'type': 'suggest_series'}
                            context_manager = context.get('_manager')
                            series_responses = self._handle_suggest_series(action, context, context_manager)
                            if series_responses:
                                return series_responses
                    except Exception:
                        pass

            # 在系列选择阶段支持数字选择系列
            if current_stage == "series_select" and user_text.isdigit():
                knowledge = context.get("knowledge")
                category = context.get("current_category")
                brand = context.get("current_brand")
                context_manager = context.get('_manager')
                if knowledge and category and brand:
                    try:
                        series_list = knowledge.get_series_in_brand(category, brand)
                        subtype = context.get("current_subtype")
                        if context_manager and not subtype:
                            cm_ctx = context_manager.get_context()
                            subtype = cm_ctx.get("current_subtype")
                        series_list = knowledge.filter_series_by_subtype(category, subtype, series_list)
                    except Exception:
                        series_list = []
                    try:
                        idx = int(user_text) - 1
                        if 0 <= idx < len(series_list):
                            series = series_list[idx]
                            manager = context.get('_manager')
                            if manager:
                                manager.update_context("current_series", series)
                                manager.add_to_chain("series", series)
                                manager.set_stage("config_select")
                            action = {'type': 'describe_series_config'}
                            desc_responses = self._handle_describe_series_config(action, context, context_manager)
                            if desc_responses:
                                return desc_responses
                    except Exception:
                        pass

        # 额外处理：基于用途场景（学习/办公/游戏等）的推荐
        scenario_responses = self._handle_usage_scenario(user_text, context)
        if scenario_responses:
            return scenario_responses

        self._apply_direct_shortcuts(context)

        if context.get('__do_describe'):
            action = {'type': 'describe_series_config'}
            context_manager = context.get('_manager')
            desc_responses = self._handle_describe_series_config(action, context, context_manager)
            if desc_responses:
                return desc_responses

        # 1. 直接进行规则匹配
        for rule in self.rules:
            if self._match_rule(rule, detected_intent, context):
                rule_responses = self._execute_actions(rule["actions"], context)
                responses.extend(rule_responses)
                break

        # 2. 如果没有匹配，提供上下文相关的提示
        if not responses:
            responses.extend(self._get_context_aware_fallback(current_stage, context))

        return responses

    def _get_context_aware_fallback(self, current_stage: str, context: Dict[str, Any]) -> List[str]:
        """根据当前阶段提供智能回退提示

        优先使用 DSL 中以 `fallback_` 开头的规则（INTENT_IS fallback），
        若未命中任何规则，再退回到一个通用提示，保证系统健壮性。
        """

        responses: List[str] = []

        # 1. 先尝试使用 DSL 中的 fallback 规则
        for rule in self.rules:
            name = rule.get("name")
            if not isinstance(name, str) or not name.startswith("fallback_"):
                continue

            if self._match_rule(rule, "fallback", context):
                rule_responses = self._execute_actions(rule["actions"], context)
                responses.extend(rule_responses)
                if responses:
                    break

        if responses:
            return responses

        # 2. 如果 DSL 中没有定义对应的 fallback 规则，则提供一个简短通用提示
        return ["抱歉，我没有理解。您可以重新描述需求，或说'重新开始'来重置对话。"]

    def _handle_usage_scenario(self, user_text: str, context: Dict[str, Any]) -> List[str]:
        """基于用途场景（学习/办公/游戏/创作等）给出知识库推荐

        设计目标：不通过 DSL 扩展场景规则，而是在解释器层拦截带有
        “适合学习/办公/游戏/创作”等表达的语句，结合 ProductKnowledge
        动态生成一段推荐文案。
        """
        text = (user_text or "").strip()
        if not text:
            return []

        knowledge = context.get("knowledge")
        if not knowledge:
            return []

        category = context.get("current_category") or ""

        # 可根据需要扩展的场景映射：用户表达 -> 知识库中的场景标签
        scenario_map = {
            "学习": "学习",
            "上课": "学习",
            "自习": "学习",
            "学生": "学习",
            "办公": "办公",
            "办公室": "办公",
            "表格": "办公",
            "文档": "办公",
            "游戏": "游戏",
            "打游戏": "游戏",
            "玩游戏": "游戏",
            "创作": "创意工作",
            "创意": "创意工作",
            "设计": "创意工作",
            "剪辑": "创意工作",
        }

        text_lower = text.lower()
        matched_scenario = None
        for phrase, scenario in scenario_map.items():
            # 这里既考虑中文短语，也兼顾可能的大小写变化
            if phrase in text or phrase.lower() in text_lower:
                matched_scenario = scenario
                break

        if not matched_scenario:
            return []

        try:
            recommendations = knowledge.get_recommendations_by_scenario(category, matched_scenario)
        except Exception as e:
            print(f"根据用途场景获取推荐时出错: {e}")
            return []

        # 如果知识库暂时没有对应场景的数据，给一个温和的兜底提示
        if not recommendations:
            return [
                f"[KB] 目前知识库中还没有专门标注‘{matched_scenario}’场景的电脑。",
                "一般来说，轻薄本/商务本会更适合学习和办公，您可以先选择品牌和系列，我再帮您细化配置。",
            ]

        # 如果有推荐，将场景偏好记录到上下文，便于后续扩展
        context_manager = context.get("_manager")
        if context_manager:
            try:
                # 这里不强依赖 EnhancedConversationContext 的具体实现，失败时静默略过
                context_manager.record_preference("usage_scenario", matched_scenario)
            except Exception:
                pass

        # 只展示前若干条，避免一次输出过长
        top_recs = recommendations[:3]
        lines: List[str] = []
        for idx, rec in enumerate(top_recs, start=1):
            brand = rec.get("brand", "")
            series_list = rec.get("series", []) or []
            price_range = rec.get("price_range", "-")
            reason = rec.get("reason", "")
            series_text = "、".join(series_list)
            lines.append(f"{idx}. {brand}：{series_text}（价格档位：{price_range}，{reason}）")

        header = f"[KB] 针对{matched_scenario}场景，我可以在【{category}】里给您这样的推荐："
        footer = "您可以告诉我更偏向哪一个品牌或系列，或者补充预算范围，我再帮您缩小范围。"

        return [header, *lines, footer]

    def _apply_direct_shortcuts(self, context: Dict[str, Any]):
        """在规则匹配前，基于用户表达进行轻量级的直接归类和阶段设置，减少直达型 DSL 规则"""
        user_text = (context.get("user_input") or "").strip()
        if not user_text:
            return

        current_stage = context.get("current_stage") or "welcome"
        manager = context.get("_manager")
        if not manager:
            return

        text_lower = user_text.lower()

        laptop_keys = ["笔记本", "笔记本电脑", "手提电脑", "macbook"]
        desktop_keys = ["台式机", "台式电脑", "桌面电脑"]

        if any(k in user_text for k in laptop_keys) or any(k in text_lower for k in ["macbook"]):
            if current_stage in {"welcome", "category_select", "subtype_select"}:
                if manager.get_context().get("current_category") != "电脑":
                    manager.update_context("current_category", "电脑")
                    context["current_category"] = "电脑"
                    manager.add_to_chain("category", "电脑")
                if manager.get_context().get("current_subtype") != "笔记本":
                    manager.update_context("current_subtype", "笔记本")
                    context["current_subtype"] = "笔记本"
                    manager.add_to_chain("subtype", "笔记本")
                manager.set_stage("brand_select")
                context["current_stage"] = "brand_select"

        if any(k in user_text for k in desktop_keys):
            if current_stage in {"welcome", "category_select", "subtype_select"}:
                if manager.get_context().get("current_category") != "电脑":
                    manager.update_context("current_category", "电脑")
                    context["current_category"] = "电脑"
                    manager.add_to_chain("category", "电脑")
                if manager.get_context().get("current_subtype") != "台式机":
                    manager.update_context("current_subtype", "台式机")
                    context["current_subtype"] = "台式机"
                    manager.add_to_chain("subtype", "台式机")
                manager.set_stage("brand_select")
                context["current_stage"] = "brand_select"

        knowledge = context.get("knowledge")
        if not knowledge:
            try:
                knowledge = ProductKnowledge()
            except Exception:
                knowledge = None
        if not knowledge:
            return

        words = [w.strip() for w in user_text.replace('，', ' ').replace(',', ' ').split() if w.strip()]

        # 品类/品牌别名识别（保持保守，仅在早期阶段触发）
        if current_stage in {"welcome", "category_select", "subtype_select", "brand_select"}:
            for w in words:
                canonical_category = knowledge.canonicalize('category', w)
                if not canonical_category:
                    aliases = getattr(knowledge, 'aliases', {}).get('category', {})
                    for k in aliases.keys():
                        if k and k in text_lower:
                            canonical_category = aliases[k]
                            break
                if canonical_category and manager.get_context().get("current_category") != canonical_category:
                    manager.update_context("current_category", canonical_category)
                    context["current_category"] = canonical_category
                    manager.add_to_chain("category", canonical_category)
                    default_brand = None
                    try:
                        default_brand = knowledge.get_default_brand_for_category(canonical_category)
                    except Exception:
                        default_brand = None
                    if default_brand:
                        manager.update_context("current_brand", default_brand)
                        context["current_brand"] = default_brand
                        manager.add_to_chain("brand", default_brand)
                        manager.set_stage("series_select")
                        context["current_stage"] = "series_select"
                    else:
                        manager.set_stage("brand_select")
                        context["current_stage"] = "brand_select"
                    break

            for w in words:
                canonical_brand = knowledge.canonicalize('brand', w)
                if not canonical_brand:
                    aliases = getattr(knowledge, 'aliases', {}).get('brand', {})
                    for k in aliases.keys():
                        if k and k in text_lower:
                            canonical_brand = aliases[k]
                            break
                if canonical_brand:
                    if not manager.get_context().get("current_category"):
                        target_cat = None
                        try:
                            target_cat = knowledge.infer_category_for_brand(canonical_brand)
                        except Exception:
                            target_cat = None
                        if target_cat:
                            manager.update_context("current_category", target_cat)
                            manager.add_to_chain("category", target_cat)
                    if manager.get_context().get("current_brand") != canonical_brand:
                        manager.update_context("current_brand", canonical_brand)
                        context["current_brand"] = canonical_brand
                        manager.add_to_chain("brand", canonical_brand)
                        manager.set_stage("series_select")
                        context["current_stage"] = "series_select"
                        break
        for w in words:
            canonical_series = knowledge.canonicalize('series', w)
            if canonical_series:
                if not manager.get_context().get("current_category"):
                    cats = list(getattr(knowledge, 'categories', {}).keys())
                    target_cat = cats[0] if cats else None
                    if target_cat:
                        manager.update_context("current_category", target_cat)
                        context["current_category"] = target_cat
                        manager.add_to_chain("category", target_cat)
                if not manager.get_context().get("current_brand"):
                    if manager.get_context().get("current_category"):
                        brands_map = getattr(knowledge, 'categories', {}).get(manager.get_context().get("current_category"), {}).get('brands', {})
                        if brands_map:
                            first_brand = next(iter(brands_map.keys()))
                            manager.update_context("current_brand", first_brand)
                            context["current_brand"] = first_brand
                            manager.add_to_chain("brand", first_brand)
                if manager.get_context().get("current_series") != canonical_series:
                    manager.update_context("current_series", canonical_series)
                    context["current_series"] = canonical_series
                    manager.add_to_chain("series", canonical_series)
                manager.set_stage("config_select")
                context["current_stage"] = "config_select"
                context['__do_describe'] = True
                break


    def _match_rule(self, rule: Dict, detected_intent: str, context: Dict[str, Any]) -> bool:
        """检查规则是否匹配，支持意图和上下文条件"""

        # print(f"正在匹配规则: {rule['name']}")
        # print(f"当前上下文: {context}")

        for condition in rule["conditions"]:
            ctype = condition["type"]
            # print(f"  检查条件: {ctype} - {condition}")

            if ctype == "intent":
                if condition.get("intent_name") != detected_intent:
                    # print(f"  意图不匹配: 期望{condition.get('intent_name')}, 实际{detected_intent}")
                    return False

            elif ctype == "user_mention":
                user_text = context.get("user_input", "")
                keyword = condition.get("keyword", "")
                if keyword and keyword not in user_text:
                    """print(f"关键词不匹配: 期望包含'{keyword}', 实际'{user_text}'")"""
                    return False

            elif ctype == "user_mention_any":
                user_text = context.get("user_input", "").lower()
                keywords = condition.get("keywords", [])
                matched = any(keyword.lower() in user_text for keyword in keywords)
                if not matched:
                    # print(f"任意关键词不匹配: 期望包含{keywords}之一, 实际'{user_text}'")
                    return False


            elif ctype == "context_not_set":
                var_name = condition.get("var_name")
                if var_name in context and context.get(var_name) is not None:
                    return False

            elif ctype == "context_eq":
                var_name = condition.get("var_name")
                expected = condition.get("value")
                # 首先从context中获取值
                value = context.get(var_name)
                # 如果context中没有，尝试从context_manager中获取
                if value is None:
                    manager = context.get('_manager')
                    if manager:
                        cm_ctx = manager.get_context()
                        value = cm_ctx.get(var_name)
                if value != expected:
                    return False

            elif ctype == "context_has":
                var_name = condition.get("var_name")
                if not var_name:
                    return False
                # 
                value = context.get(var_name)
                # 
                if value is None and "session_variables" in context:
                    value = context["session_variables"].get(var_name)
                # 
                if value is None:
                    return False
                # 
                if "value" in condition and condition["value"] is not None:
                    if value != condition["value"]:
                        return False

            elif ctype == "stage_is":
                stage = context.get("current_stage")
                # 如果context中没有，尝试从context_manager中获取
                if stage is None:
                    manager = context.get('_manager')
                    if manager:
                        stage = manager.get_stage()
                expected = condition.get("stage")
                if stage != expected:
                    return False

        return True

    def _execute_actions(self, actions: List[Dict], context: Dict[str, Any]) -> List[str]:
        """执行动作序列，并操作上下文管理器"""

        responses: List[str] = []
        context_manager = context.get("_manager")

        for action in actions:
            atype = action.get("type")
            handler = self._action_handlers.get(atype)
            if not handler:
                continue

            result = handler(action, context, context_manager)
            if isinstance(result, list):
                responses.extend(result)

        return responses

    # 以下为各类动作的具体处理函数，便于后续扩展
    def _handle_respond(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        message = action.get("message", "")
        message = self._replace_variables(message, context)
        # 标记：该回复来源于 DSL 中的 RESPOND 规则
        return [f"[DSL] {message}"]

    def _handle_respond_kb(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        knowledge = context.get("knowledge")
        if not knowledge:
            try:
                knowledge = ProductKnowledge()
            except Exception:
                knowledge = None
        if not knowledge:
            return []
        key = action.get("template_key", "")
        try:
            lines = knowledge.get_template(key)
        except Exception:
            lines = []
        if not lines:
            return []
        responses: List[str] = []
        for line in lines:
            line_text = self._replace_variables(line, context)
            responses.append(f"[KB] {line_text}")
        return responses

    def _handle_set_variable(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        if context_manager:
            context_manager.update_context(action["var_name"], action["value"])
        return []

    def _handle_set_stage(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        if context_manager:
            context_manager.set_stage(action["stage"])
        return []

    def _handle_add_to_chain(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        if context_manager:
            context_manager.add_to_chain(action["item_type"], action["item_value"])
        return []
    def _handle_suggest_brands(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        """基于 ProductKnowledge 动态列出当前品类下的品牌"""
        knowledge = context.get("knowledge")
        if not knowledge:
            return []

        category = context.get("current_category") or "产品"
        try:
            brands = knowledge.get_brands_in_category(category)
        except Exception as e:
            print(f"获取品类 {category} 的品牌信息时出错: {e}")
            return []

        if not brands:
            return [f"[KB] 当前暂时没有找到【{category}】的品牌信息，请尝试更换品类或具体说明品牌。"]

        # 如果只有一个品牌（通常是苹果），直接进入系列选择
        if len(brands) == 1:
            brand = brands[0]
            # 自动设置品牌并进入系列选择
            if context_manager:
                context_manager.update_context("current_brand", brand)
                context_manager.add_to_chain("brand", brand)
                context_manager.set_stage("series_select")
            # 直接调用系列建议，不显示额外的提示
            action = {'type': 'suggest_series'}
            return self._handle_suggest_series(action, context, context_manager)
        
        # 多个品牌时才显示选择
        brand_list = "、".join(brands)
        return [
            f"[KB] 目前{category}主流品牌有：{brand_list}。",
            "您更倾向哪个品牌？"
        ]

    def _handle_suggest_series(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        """基于 ProductKnowledge 动态列出当前品类+品牌下的系列/型号

        设计要点：
        - 优先从当前上下文中读取品类/品牌；
        - 若本轮对话中刚通过 SET_VAR 设置（在同一个 THEN 里紧跟着 SUGGEST_SERIES），
          则需要从 context_manager 的最新状态中补偿读取，避免因为 context 仍是旧快照而丢失信息。
        - 完全依赖知识库的数据来组织语言，避免在 DSL 中硬编码每个品牌的系列列表。
        """
        knowledge = context.get("knowledge")
        if not knowledge:
            return []

        # 1. 先从本次 execute 传入的上下文中读取品类和品牌
        category = context.get("current_category")
        brand = context.get("current_brand")

        # 2. 如果缺失，再尝试从上下文管理器中获取最新值（支持“同一 THEN 内先 SET_VAR 再 SUGGEST_SERIES”的场景）
        if context_manager is not None:
            cm_ctx = context_manager.get_context()
            if not category:
                category = cm_ctx.get("current_category")
            if not brand:
                brand = cm_ctx.get("current_brand")

        if not category or not brand:
            return ["[KB] 要为您推荐系列，请先确定品类和品牌，例如先说‘我要买苹果的电脑/手机’。"]

        try:
            series_list = knowledge.get_series_in_brand(category, brand)
        except Exception as e:
            print(f"获取品类 {category} 品牌 {brand} 的系列信息时出错: {e}")
            return []

        subtype = context.get("current_subtype")
        if context_manager is not None and not subtype:
            cm_ctx = context_manager.get_context()
            subtype = cm_ctx.get("current_subtype")

        try:
            series_list = knowledge.filter_series_by_subtype(category, subtype, series_list)
        except Exception:
            series_list = series_list

        if not series_list:
            return [f"[KB] 暂时没有找到【{category} - {brand}】的系列信息，请尝试直接说明具体型号。"]

        responses: List[str] = []
        # 根据品类使用更自然的表达
        if category == "电脑":
            responses.append(f"[KB] {brand} {category}系列：")
        elif category == "手机":
            responses.append(f"[KB] 当前在售的 iPhone 系列：")
        elif category == "平板":
            responses.append(f"[KB] iPad 系列：")
        else:
            responses.append(f"[KB] {brand} {category}系列：")
        
        for idx, s in enumerate(series_list, start=1):
            responses.append(f"{idx}. {s}")
        responses.append("您对哪一款更感兴趣？可以说序号或具体系列名称。")
        return responses
    def _handle_describe_series_config(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        """基于 ProductKnowledge 列出当前系列的主要配置选项

        依赖 current_category / current_brand / current_series 三个维度，从知识库中
        读取该系列的配置列表，避免在 DSL 中硬编码每一条配置文案。
        """
        knowledge = context.get("knowledge")
        if not knowledge:
            return []

        # 从上下文和上下文管理器中获取最新的品类、品牌和系列
        category = context.get("current_category")
        brand = context.get("current_brand")
        series = context.get("current_series")

        if context_manager is not None:
            cm_ctx = context_manager.get_context()
            if not category:
                category = cm_ctx.get("current_category")
            if not brand:
                brand = cm_ctx.get("current_brand")
            if not series:
                series = cm_ctx.get("current_series")

        if not category or not brand or not series:
            return ["[KB] 要为您介绍详细配置，请先确定品类、品牌和系列名称，例如先选定 MacBook Air 或 MacBook Pro。"]

        try:
            configs = knowledge.get_series_configs(category, brand, series)
        except Exception as e:
            print(f"根据系列获取配置选项时出错: {e}")
            return []

        if not configs:
            return [f"[KB] 当前知识库中还没有【{series}】的详细配置，请尝试直接说明您关心的配置参数（如内存、硬盘容量等）。"]

        responses: List[str] = [f"[KB] {series} 主要配置："]
        responses.extend(configs)
        count = len(configs)
        if count > 0:
            indices = "、".join(str(i) for i in range(1, count + 1))
            responses.append(f"您对哪个配置更感兴趣？可以说 {indices} 等编号。")
        return responses

    def _handle_suggest_dates(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        """生成未来三天的日期选项"""
        from datetime import datetime, timedelta
        
        today = datetime.now()
        date_options = []
        for i in range(3):
            future_date = today + timedelta(days=i)
            date_str = future_date.strftime("%Y-%m-%d")
            date_options.append(date_str)
        
        # 保存到上下文供后续使用
        context["date_options"] = date_options
        if context_manager:
            context_manager.update_context("date_options", date_options)
        
        # 获取已选择的时间
        selected_time = context.get("selected_time", "")
        if not selected_time and context_manager:
            cm_ctx = context_manager.get_context()
            selected_time = cm_ctx.get("selected_time", "")
        
        responses = ["[KB] 请选择用餐日期："]
        for idx, date in enumerate(date_options, 1):
            weekday = (today + timedelta(days=idx-1)).strftime("%A")
            weekday_cn = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三", 
                         "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
            responses.append(f"{idx}. {date} ({weekday_cn.get(weekday, weekday)})")
        
        if selected_time:
            responses.append(f"用餐时间为：{selected_time}")
        
        return responses



    def _handle_increment(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        if context_manager:
            var_name = action["var_name"]
            current_value = context_manager.get_context().get(var_name, 0)
            context_manager.update_context(var_name, current_value + 1)
        return []

    def _handle_record_preference(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        if context_manager:
            context_manager.record_preference(action["key"], action["value"])
        return []

    def _handle_reset_shopping_context(self, action: Dict[str, Any], context: Dict[str, Any], context_manager: Any) -> List[str]:
        if not context_manager:
            return []

        if hasattr(context_manager, 'reset_shopping_context'):
            context_manager.reset_shopping_context()
        else:
            # 后备方案：手动重置关键变量
            reset_vars = ["current_category", "current_subtype", "current_brand", "current_series", "product_chain"]
            for var in reset_vars:
                context_manager.update_context(var, None)
            context_manager.set_stage("welcome")
            print("⚠️ 使用后备方案重置上下文")

        return []

    def _validate_config_input(self, user_input: str, context: Dict[str, Any]) -> bool:
        """验证配置选择阶段的用户输入是否合法"""
        if not user_input.strip():
            return False
        
        # 检查是否为有效的数字选择
        if user_input.isdigit():
            try:
                choice_num = int(user_input)
                current_series = context.get("current_series", "")
                
                # 根据不同系列验证有效范围 - 大部分系列都有2个配置选项
                if current_series in ["Mac mini", "MacBook Air", "MacBook Pro", "iMac", "Mac Studio"]:
                    return choice_num in [1, 2]
                elif current_series in ["iPad Pro", "iPad Air", "iPad", "iPad mini"]:
                    return choice_num in [1, 2]
                # 默认允许1和2
                else:
                    return choice_num in [1, 2]
                    
            except ValueError:
                pass
        
        # 检查是否为有效的关键词选择（暂时不支持，可以后续扩展）
        return False
    
    def _process_valid_config_choice(self, user_input: str, context: Dict[str, Any], manager: Any) -> List[str]:
        """处理有效的配置选择"""
        try:
            choice_num = int(user_input)
            current_series = context.get("current_series", "")
            
            if current_series == "Mac mini":
                config_name = "基础版" if choice_num == 1 else "增强版"
                if manager:
                    manager.update_context("selected_config", config_name)
                    manager.set_stage("completed")
                
                return [
                    f"✅ 已选择 {current_series} - {config_name}",
                    "🎉 配置选择完成！",
                    "📦 您可以继续了解其他产品或询问更多详情。"
                ]
            
            elif current_series == "MacBook Air":
                config_name = "13.6寸" if choice_num == 1 else "15.3寸"
                if manager:
                    manager.update_context("selected_config", config_name)
                    manager.set_stage("storage_select")  # MacBook Air需要选择存储配置
                
                # 调用存储配置显示
                knowledge = context.get("knowledge")
                if knowledge:
                    storage_template = "air_13_storage_options" if choice_num == 1 else "air_15_storage_options"
                    return knowledge.get_template(storage_template)
                
                return [
                    f"✅ 已选择 {current_series} {config_name}",
                    "💾 请选择存储配置"
                ]
            
            elif current_series == "MacBook Pro":
                config_name = "14寸" if choice_num == 1 else "16寸"
                if manager:
                    manager.update_context("selected_config", config_name)
                    manager.set_stage("chip_select")  # MacBook Pro需要选择芯片
                
                # 调用芯片配置显示
                knowledge = context.get("knowledge")
                if knowledge:
                    chip_template = "mbp_14_chip_options" if choice_num == 1 else "mbp_16_chip_options"
                    return knowledge.get_template(chip_template)
                
                return [
                    f"✅ 已选择 {current_series} {config_name}",
                    "🔧 请选择芯片配置"
                ]
            
            elif current_series in ["iMac", "Mac Studio"]:
                config_name = "基础配置" if choice_num == 1 else "高级配置"
                if manager:
                    manager.update_context("selected_config", config_name)
                    manager.set_stage("completed")
                
                return [
                    f"✅ 已选择 {current_series} - {config_name}",
                    "🎉 配置选择完成！",
                    "📦 您可以继续了解其他产品或询问更多详情。"
                ]
            
            # 如果没有匹配到系列，返回通用成功消息
            if manager:
                manager.update_context("selected_config", f"配置{choice_num}")
                manager.set_stage("completed")
            
            return [
                f"✅ 已选择 {current_series} 配置 {choice_num}",
                "🎉 配置选择完成！"
            ]
            
        except ValueError:
            pass
        
        return ["❌ 处理配置选择时出现错误"]

    def _replace_variables(self, message: str, context: Dict[str, Any]) -> str:
        """替换消息中的变量占位符"""
        
        # 优先从 context_manager获取最新值
        context_manager = context.get("_manager")
        if context_manager:
            cm_context = context_manager.get_context()
        else:
            cm_context = {}

        # 合并context和context_manager的数据，context_manager优先
        merged_context = {**context, **cm_context}

        replacements = {
            "current_category": str(merged_context.get("current_category", "")),
            "current_subtype": str(merged_context.get("current_subtype", "")),
            "current_brand": str(merged_context.get("current_brand", "")),
            "current_series": str(merged_context.get("current_series", "")),
            "query_count": str(merged_context.get("query_count", 0)),
            "party_size": str(merged_context.get("party_size", "")),
            "private_room": str(merged_context.get("private_room", "")),
            "selected_date": str(merged_context.get("selected_date", "")),
            "selected_time": str(merged_context.get("selected_time", "")),
            "budget": str(merged_context.get("budget", "")),
            "contact": str(merged_context.get("contact", "")),
            "selected_config_index": str(merged_context.get("selected_config_index", "")),
        }

        for var_name, value in replacements.items():
            placeholder = f"${{{var_name}}}"
            message = message.replace(placeholder, value)

        # product_chain 展示
        if "product_chain" in merged_context:
            chain_text = " → ".join(item["value"] for item in merged_context["product_chain"])
            message = message.replace("${product_chain}", chain_text)
        else:
            message = message.replace("${product_chain}", "")

        return message
    
    def _validate_stage_input(self, user_input: str, stage: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """通用阶段输入验证方法"""
        if not user_input.strip():
            return {"valid": False, "error_response": []}
        
        # 检查是否为数字输入
        if user_input.isdigit():
            try:
                choice_num = int(user_input)
                valid_range = self._get_valid_range_for_stage(stage, context)
                
                if choice_num in valid_range:
                    return {"valid": True}
                else:
                    # 生成错误响应
                    error_msg = f"❌ 无效的选项，请输入 {self._format_valid_range(valid_range)}"
                    guide_msg = "💡 提示：直接输入数字即可选择"
                    
                    # 根据阶段获取重新显示的内容
                    stage_content = self._get_stage_content(stage, context)
                    
                    return {
                        "valid": False, 
                        "error_response": [error_msg, guide_msg] + stage_content
                    }
                    
            except ValueError:
                pass
        
        # 非数字输入让DSL规则处理（可能是关键词）
        return {"valid": True}
    
    def _get_valid_range_for_stage(self, stage: str, context: Dict[str, Any]) -> List[int]:
        """获取不同阶段的有效输入范围"""
        # 电商阶段
        if stage == "config_select":
            return [1, 2]  # 大部分配置选择都是2个选项
        elif stage == "storage_select":
            return [1, 2, 3]  # 存储选择一般有3个选项
        elif stage == "color_select":
            return [1, 2, 3, 4]  # 颜色选择一般有4个选项
        elif stage == "chip_select":
            return [1, 2, 3]  # 芯片选择一般有2-3个选项
        elif stage == "series_select":
            return [1, 2, 3, 4, 5]  # 系列选择有5个选项
        elif stage == "subtype_select":
            return [1, 2]  # 子类型选择（笔记本/台式机）
        elif stage == "brand_select":
            return [1, 2, 3, 4, 5]  # 品牌选择（根据具体情况）
        elif stage == "size_select":
            return [1, 2]  # 尺寸选择
        # 手机相关阶段
        elif stage == "phone_model_select":
            return [1, 2, 3]  # iPhone型号选择
        elif stage == "phone_storage_select":
            return [1, 2, 3, 4]  # 手机存储选择
        elif stage == "phone_color_select":
            return [1, 2, 3, 4]  # 手机颜色选择
        # 餐饮阶段
        elif stage == "date_collect":
            return [1, 2, 3]  # 日期选择（未来3天）
        elif stage == "final_confirm":
            return [1, 2]  # 确认/取消
        
        return [1, 2]  # 默认范围
    
    def _format_valid_range(self, valid_range: List[int]) -> str:
        """格式化有效范围显示"""
        if len(valid_range) <= 1:
            return str(valid_range[0]) if valid_range else "1"
        elif len(valid_range) == 2:
            return f"{valid_range[0]} 或 {valid_range[1]}"
        else:
            return f"{valid_range[0]} 到 {valid_range[-1]}"
    
    def _get_stage_content(self, stage: str, context: Dict[str, Any]) -> List[str]:
        """根据阶段获取重新显示的内容"""
        try:
            if stage == "config_select":
                return self._handle_describe_series_config(
                    {'type': 'describe_series_config'}, context, None
                )
            elif stage in ["series_select", "phone_model_select"]:
                return self._handle_suggest_series(
                    {'type': 'suggest_series'}, context, None
                )
            elif stage == "brand_select":
                return self._handle_suggest_brands(
                    {'type': 'suggest_brands'}, context, None
                )
            elif stage == "date_collect":
                return self._handle_suggest_dates(
                    {'type': 'suggest_dates'}, context, None
                )
            # 其他阶段的内容可以根据需要添加
        except Exception:
            pass
        
        return []