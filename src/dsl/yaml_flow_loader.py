"""
YAML流程定义加载器
用于加载和验证基于YAML语法的DSL流程脚本
"""

import yaml
import os
from typing import Dict, Any, List


class YAMLFlowLoader:
    """YAML格式的流程定义加载器"""
    
    @staticmethod
    def load(yaml_file: str) -> Dict[str, Any]:
        """
        加载YAML流程定义文件
        
        Args:
            yaml_file: YAML文件路径
            
        Returns:
            流程配置字典
            
        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML格式错误
            ValueError: 流程配置验证失败
        """
        if not os.path.exists(yaml_file):
            raise FileNotFoundError(f"流程文件不存在: {yaml_file}")
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"YAML解析错误: {e}")
        
        if not config or 'flow' not in config:
            raise ValueError("无效的流程配置文件，缺少'flow'根节点")
        
        flow_config = config['flow']
        
        # 验证配置完整性
        YAMLFlowLoader.validate(flow_config)
        
        return flow_config
    
    @staticmethod
    def validate(flow_config: Dict[str, Any]) -> bool:
        """
        验证流程配置的完整性和正确性
        
        Args:
            flow_config: 流程配置字典
            
        Returns:
            True if valid
            
        Raises:
            ValueError: 配置验证失败
        """
        # 必需字段检查
        required_fields = ['name', 'process_order', 'slots']
        for field in required_fields:
            if field not in flow_config:
                raise ValueError(f"流程配置缺少必需字段: {field}")
        
        # 验证process_order
        process_order = flow_config['process_order']
        if not isinstance(process_order, list) or len(process_order) == 0:
            raise ValueError("process_order必须是非空列表")
        
        # 验证slots定义
        slots = flow_config['slots']
        if not isinstance(slots, dict):
            raise ValueError("slots必须是字典类型")
        
        # 检查process_order中的每个槽位都有定义
        for slot_name in process_order:
            if slot_name not in slots:
                raise ValueError(f"process_order中的槽位'{slot_name}'未在slots中定义")
        
        # 验证每个槽位的必需属性
        for slot_name, slot_config in slots.items():
            if not isinstance(slot_config, dict):
                raise ValueError(f"槽位'{slot_name}'的配置必须是字典类型")
            
            # 检查必需属性
            if 'label' not in slot_config:
                raise ValueError(f"槽位'{slot_name}'缺少'label'属性")
            
            if 'required' not in slot_config:
                raise ValueError(f"槽位'{slot_name}'缺少'required'属性")
            
            # 验证depends_on引用
            if 'depends_on' in slot_config:
                depends = slot_config['depends_on']
                if not isinstance(depends, list):
                    raise ValueError(f"槽位'{slot_name}'的depends_on必须是列表")
                
                for dep in depends:
                    if dep not in slots:
                        raise ValueError(f"槽位'{slot_name}'依赖的槽位'{dep}'未定义")
        
        return True
    
    @staticmethod
    def load_all_flows(scripts_dir: str) -> Dict[str, Dict[str, Any]]:
        """
        加载目录中所有的流程定义文件
        
        Args:
            scripts_dir: 脚本文件目录
            
        Returns:
            流程名称到流程配置的映射
        """
        flows = {}
        
        if not os.path.exists(scripts_dir):
            return flows
        
        for filename in os.listdir(scripts_dir):
            if filename.endswith('.flow.yaml') or filename.endswith('.flow.yml'):
                filepath = os.path.join(scripts_dir, filename)
                try:
                    flow_config = YAMLFlowLoader.load(filepath)
                    flow_name = flow_config['name']
                    flows[flow_name] = flow_config
                    print(f"✅ 已加载流程: {flow_name} (文件: {filename})")
                except Exception as e:
                    print(f"⚠️ 加载流程失败 {filename}: {e}")
        
        return flows
    
    @staticmethod
    def get_flow_info(flow_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取流程的基本信息
        
        Args:
            flow_config: 流程配置
            
        Returns:
            流程信息字典
        """
        return {
            'name': flow_config.get('name'),
            'version': flow_config.get('version'),
            'description': flow_config.get('description'),
            'business_line': flow_config.get('business_line'),
            'slots_count': len(flow_config.get('slots', {})),
            'commands_count': len(flow_config.get('commands', {})),
        }
