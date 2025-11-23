#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于YAML-DSL的智能表单客服系统
使用声明式DSL定义对话流程，简化脚本开发
"""
import os
import sys

# 保证可以从 src 内进行包导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dsl.yaml_flow_loader import YAMLFlowLoader
from dsl.flow_interpreter import FlowInterpreter
from core.form_based_system import FormBasedDialogSystem
from semantics.option_mapping import SemanticMapper
from llm.spark_client import SparkLLMClient
from config.settings import Config


def choose_flow() -> tuple[str, str]:
    """选择业务流程"""
    print("📋 可用业务流程：")
    
    flows = {
        "1": ("apple_store", "src/scripts/apple_store.flow.yaml", "🍎 苹果专卖店购物流程"),
        "2": ("dining", "src/scripts/dining.flow.yaml", "🍽️ 餐厅预订流程"),
    }
    
    for key, (_, _, desc) in flows.items():
        print(f"  {key}) {desc}")
    
    try:
        choice = input(f"请输入序号 (1-{len(flows)})，回车默认[1]: ").strip()
        if choice and choice in flows:
            business_line, yaml_file, _ = flows[choice]
            return business_line, yaml_file
    except (ValueError, KeyError):
        pass
    
    # 默认返回第一个
    return flows["1"][0], flows["1"][1]


def build_llm_client():
    """构建LLM客户端"""
    try:
        client = SparkLLMClient(**Config.get_llm_config())
        print("✅ LLM客户端初始化成功")
        return client
    except Exception as e:
        print(f"⚠️ LLM 初始化失败，改为不使用 LLM: {e}")
        print("   这意味着系统只会使用本地关键词匹配，不会有AI智能分析")
        return None


def print_intro():
    """显示介绍"""
    print("=" * 70)
    print("🤖 智能表单客服系统 - 基于YAML声明式DSL")
    print("=" * 70)
    print("• 本系统使用YAML定义的DSL脚本驱动对话流程")
    print("• 支持自然语言输入和智能意图识别")
    print("• 命令: exit 退出 | reset 重新开始 | help 帮助")
    print("=" * 70)


def main():
    """主程序"""
    print_intro()
    
    # 选择业务流程
    business_line, yaml_file = choose_flow()
    
    try:
        # 加载YAML流程定义
        print(f"\n📄 正在加载流程定义: {yaml_file}")
        flow_config = YAMLFlowLoader.load(yaml_file)
        flow_info = YAMLFlowLoader.get_flow_info(flow_config)
        
        print(f"✅ 流程加载成功:")
        print(f"   名称: {flow_info['name']}")
        print(f"   版本: {flow_info['version']}")
        print(f"   描述: {flow_info['description']}")
        print(f"   槽位数: {flow_info['slots_count']}")
        print(f"   命令数: {flow_info['commands_count']}")
        
    except Exception as e:
        print(f"❌ 流程加载失败: {e}")
        return
    
    # 从YAML配置构建槽位规格并注入到业务配置
    from knowledge.business_config_loader import business_config_loader, SlotSpec
    slot_specs = []
    for slot_name in flow_config['process_order']:
        slot_cfg = flow_config['slots'].get(slot_name, {})
        if slot_cfg:
            slot_spec = SlotSpec(
                name=slot_name,
                required=slot_cfg.get('required', True),
                description=slot_cfg.get('description', slot_cfg.get('label', '')),
                dependencies=slot_cfg.get('dependencies', []),
                enums_key=slot_cfg.get('enums_key'),
                semantic_stage=slot_cfg.get('semantic_stage'),
                allow_llm=slot_cfg.get('allow_llm', False)
            )
            slot_specs.append(slot_spec)
    
    # 注入槽位规格到业务配置
    business_config_loader.inject_slot_specs(business_line, slot_specs)
    
    # 创建表单系统
    form = FormBasedDialogSystem(business_line)
    
    # 创建流程解释器
    interpreter = FlowInterpreter(flow_config, form)
    
    # 创建语义映射器和LLM客户端
    semantic_mapper = SemanticMapper()
    llm_client = build_llm_client()
    
    # 显示初始提示(来自DSL的on_start事件)
    if interpreter.last_response:
        print("\n🤖 客服:")
        for line in interpreter.last_response.get("response", "").split("\n"):
            if line.strip():
                print(f"  {line}")
    
    # 对话循环
    while True:
        try:
            text = input("\n👤 用户: ").strip()
            if not text:
                continue
            
            low = text.lower()
            
            # 基本命令
            if low in {"exit", "quit", "q", "退出"}:
                print("👋 再见！感谢使用")
                break
            
            if low in {"reset", "重置", "重新开始"}:
                # 重新加载流程
                form = FormBasedDialogSystem(business_line)
                interpreter = FlowInterpreter(flow_config, form)
                print("🌟 已重置，我们重新开始")
                # 显示初始提示(来自DSL的on_start事件)
                if interpreter.last_response:
                    print("🤖 客服:")
                    for line in interpreter.last_response.get("response", "").split("\n"):
                        if line.strip():
                            print(f"  {line}")
                continue
            
            # 通过DSL解释器处理输入
            result = interpreter.process_input(text, llm_client, semantic_mapper)
            
            resp = result.get("response", "")
            if resp:
                print("🤖 客服:")
                for line in resp.split("\n"):
                    if line.strip():
                        print(f"  {line}")
            
            # 检查是否需要退出
            if result.get("should_exit"):
                break

        except KeyboardInterrupt:
            print("\n👋 用户中断，已退出")
            break
        except Exception as e:
            print(f"❌ 运行时异常: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
