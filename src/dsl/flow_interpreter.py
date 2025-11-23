"""
流程解释器
解释执行基于YAML定义的DSL流程脚本
"""

from typing import Dict, Any, Optional, List
from core.form_based_system import FormBasedDialogSystem, SlotStatus


class FlowInterpreter:
    """基于YAML配置的流程解释器"""
    
    def __init__(self, flow_config: Dict[str, Any], form_system: FormBasedDialogSystem):
        """
        初始化流程解释器
        
        Args:
            flow_config: YAML流程配置字典
            form_system: 表单对话系统实例
        """
        # 使用传入的配置
        self.config = flow_config
        self.form = form_system
        
        # 提取配置
        self.flow_name = self.config['name']
        self.process_order = self.config['process_order']
        self.slots_config = self.config['slots']
        self.events = self.config.get('events', {})
        self.commands = self.config.get('commands', {})
        self.validations = self.config.get('validations', [])
        
        # 注册槽位配置到表单系统
        self._register_slots_to_form()
        
        # 状态
        self.current_slot_index = 0
        self.last_response = None
        
        # 执行on_start事件并保存初始响应
        initial_response = self._trigger_event('on_start')
        if initial_response:
            self.last_response = initial_response
    
    def _register_slots_to_form(self):
        """
        将YAML中的槽位配置注册到表单系统
        这样表单系统就知道每个槽位的enums_key、dependencies等信息
        """
        
        for slot_name, slot_config in self.slots_config.items():
            # 获取槽位对象
            if slot_name not in self.form.current_form:
                continue
                
            slot_obj = self.form.current_form[slot_name]
            
            # 从YAML配置更新槽位属性
            if 'enums_key' in slot_config:
                slot_obj.definition.enums_key = slot_config['enums_key']
            
            if 'semantic_stage' in slot_config:
                slot_obj.definition.semantic_stage = slot_config['semantic_stage']
            
            if 'allow_llm' in slot_config:
                slot_obj.definition.allow_llm = slot_config['allow_llm']
            
            if 'dependencies' in slot_config:
                slot_obj.definition.dependencies = slot_config['dependencies']
            
            # [关键修改] 动态注入 prompt_template 和 conditional_prompts
            # 这些属性原本不在 SlotDefinition 中，我们动态挂载到 FormSlot 对象上
            if 'prompt_template' in slot_config:
                slot_obj.prompt_template = slot_config['prompt_template']
                
            if 'conditional_prompts' in slot_config:
                slot_obj.conditional_prompts = slot_config['conditional_prompts']
    
    def process_input(self, user_input: str, llm_client=None, semantic_mapper=None) -> Dict[str, Any]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入文本
            llm_client: LLM客户端（可选）
            semantic_mapper: 语义映射器（可选）
            
        Returns:
            包含响应的结果字典
        """
        # 1. 检查用户命令
        command_result = self._check_commands(user_input)
        if command_result:
            return command_result
        
        # 2. 调用表单系统处理输入
        result = self.form.process_input(user_input, llm_client, semantic_mapper)
        
        # 3. 检查是否触发事件
        if self._all_slots_filled():
            self._trigger_event('on_all_filled')
        
        self.last_response = result
        return result
    
    def _check_commands(self, user_input: str) -> Optional[Dict[str, Any]]:
        """检查用户输入是否匹配命令"""
        user_input_lower = user_input.lower().strip()
        
        for cmd_name, cmd_config in self.commands.items():
            keywords = cmd_config.get('keywords', [])
            
            # 检查关键词匹配
            if any(kw in user_input_lower for kw in keywords):
                # 检查命令可用条件
                condition = cmd_config.get('condition')
                if condition and not self._evaluate_condition(condition):
                    continue
                
                available_when = cmd_config.get('available_when', 'always')
                if not self._check_availability(available_when):
                    continue
                
                # 执行命令动作
                action = cmd_config.get('action')
                response = cmd_config.get('response')
                
                return self._execute_command_action(action, response, cmd_config)
        
        return None
    
    def _execute_command_action(self, action: str, response: Optional[str], config: dict) -> Dict[str, Any]:
        """执行命令动作"""
        if action == 'confirm_order':
            # 确认订单 - 先检查是否有验证错误
            if not self._all_slots_filled():
                return {"response": "请先完成所有必填项"}
            
            # 检查验证错误
            if self.form.validation_errors:
                return {
                    "response": "⚠️ 订单存在验证错误，请先解决以下问题：\n" + 
                               "\n".join(f"  • {e}" for e in self.form.validation_errors) +
                               "\n\n您可以输入 '重选' 来修改相关配置。"
                }
            
            # 触发on_confirm事件
            return self._trigger_event('on_confirm') or {"response": "订单已确认"}
        
        elif action == 'restart_flow':
            # 重新开始流程
            self._trigger_event('on_restart')
            initial_prompt = self.form.get_initial_prompt()
            return {
                "response": "已重置，让我们重新开始\n\n" + initial_prompt,
                "action": "restart"
            }
        
        elif action == 'enter_reselect_mode':
            # 进入重选模式
            reselect_options = self.form._generate_reselect_options()
            return {"response": reselect_options, "action": "reselect"}
        
        elif action == 'show_summary':
            # 显示订单摘要
            summary = self.form._generate_order_summary()
            return {"response": summary}
        
        elif action == 'show_help':
            # 显示帮助
            help_text = response or "需要帮助吗？"
            return {"response": help_text}
        
        elif action == 'cancel_current_action':
            # 取消当前操作
            return {"response": "已取消", "action": "cancel"}
        
        else:
            # 未知动作
            return {"response": f"未知命令动作: {action}"}
    
    def _trigger_event(self, event_name: str) -> Optional[Dict[str, Any]]:
        """触发事件处理器"""
        if event_name not in self.events:
            return None
        
        handlers = self.events[event_name]
        if not isinstance(handlers, list):
            return None
        
        responses = []
        
        for handler in handlers:
            action = handler.get('action')
            
            if action == 'reset_form':
                # 重置表单(保持business_line)
                business_line = self.form.business_line
                self.form = FormBasedDialogSystem(business_line)
                # 重新注册槽位配置，因为表单被重置了
                self._register_slots_to_form()
            
            elif action == 'auto_fill_single_options':
                self.form._auto_fill_single_option_slots()
            
            elif action == 'show_template':
                template_name = handler.get('template')
                from knowledge.business_config_loader import business_config_loader
                template_lines = business_config_loader.get_template(
                    self.form.business_line, 
                    template_name
                )
                if template_lines:
                    # 这里也可以应用通用的模板处理逻辑（如替换变量），如果需要的话
                    responses.append("\n".join(template_lines))
           
            elif action == 'show_slot_prompt':
                slot_name = handler.get('slot')
                if slot_name:
                    # 调用表单系统的生成逻辑，支持 {options} 替换和动态过滤
                    prompt = self.form._generate_slot_prompt(slot_name)
                    if prompt:
                        responses.append(prompt)
            
            elif action == 'show_summary':
                summary = self.form._generate_order_summary()
                if summary:
                    responses.append(summary)
            
            elif action == 'submit_order':
                self.form.order_confirmed = True
                summary = self.form._generate_order_summary()
                if summary:
                    responses.append(summary)
            
            elif action == 'validate_form':
                # 执行验证
                self._run_validations()
        
        # 返回合并的响应
        if responses:
            return {"response": "\n\n".join(responses)}
        return None
    
    def _evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式"""
        if condition == 'all_slots_filled':
            return self._all_slots_filled()
        
        elif condition == 'any_slot_filled':
            return any(
                slot.status == SlotStatus.FILLED
                for slot in self.form.current_form.values()
            )
        
        return False
    
    def _check_availability(self, available_when: str) -> bool:
        """检查命令可用性"""
        if available_when == 'always':
            return True
        elif available_when == 'any_slot_filled':
            return any(
                slot.status == SlotStatus.FILLED
                for slot in self.form.current_form.values()
            )
        elif available_when == 'all_slots_filled':
            return self._all_slots_filled()
        return True
    
    def _all_slots_filled(self) -> bool:
        """检查所有槽位是否已填充"""
        return self.form._check_form_completeness()
    
    def _run_validations(self):
        """运行配置的验证规则"""
        for validation in self.validations:
            if not validation.get('enabled', True):
                continue
            
            # 检查when条件
            when_config = validation.get('when', {})
            slots_filled = when_config.get('slots_filled', [])
            
            # 检查所需槽位是否已填充
            all_filled = all(
                self.form.current_form.get(slot_name) and 
                self.form.current_form[slot_name].status == SlotStatus.FILLED
                for slot_name in slots_filled
            )
            
            if not all_filled:
                continue
            
            # 执行验证规则（此处仅为占位，实际逻辑在slot_validators中或需扩展）
            pass
    
    def get_flow_info(self) -> Dict[str, Any]:
        """获取流程信息"""
        return {
            'name': self.flow_name,
            'slots_total': len(self.process_order),
            'slots_filled': sum(
                1 for slot in self.form.current_form.values()
                if slot.status == SlotStatus.FILLED
            ),
            'is_complete': self._all_slots_filled(),
        }