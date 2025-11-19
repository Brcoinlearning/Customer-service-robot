#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
表单模式客服系统入口
使用表单填充方式进行多槽位信息抽取，支持自然语言输入
"""
import os
import sys

# 保证可以从 src 内进行包导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.form_based_system import FormBasedDialogSystem
from semantics.option_mapping import SemanticMapper
from llm.spark_client import SparkLLMClient
from config.settings import Config


def choose_business_line() -> str:
    """选择业务线（使用统一配置系统）"""
    from knowledge.business_config_loader import business_config_loader
    
    print("📋 可用业务线：")
    businesses = business_config_loader.list_businesses()
    display_names = business_config_loader.get_business_display_names()
    
    if not businesses:
        print("⚠️ 未找到任何业务配置，使用默认配置")
        return "apple_store"
    
    for i, business in enumerate(businesses, 1):
        display_name = display_names.get(business, business)
        print(f"  {i}) {display_name}")
    
    try:
        c = input(f"请输入序号 (1-{len(businesses)})，回车默认[1]: ").strip()
        if c and c.isdigit():
            idx = int(c) - 1
            if 0 <= idx < len(businesses):
                return businesses[idx]
    except (ValueError, IndexError):
        pass
    
    return businesses[0] if businesses else "apple_store"


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


def print_intro(business_line: str = "apple_store"):
    """根据业务线显示欢迎信息"""
    from knowledge.business_config_loader import business_config_loader
    welcome_template = business_config_loader.get_template(business_line, "form_welcome")
    if welcome_template:
        print("=" * 50)
        for line in welcome_template:
            print(line)
        print("=" * 50)
    else:
        print("=" * 50)
        print("🍎 智能客服助手 为您服务")
        print("- 您可以直接说需求，也可以按我的引导一步步选择")
        print("=" * 50)
    print("💡 命令: exit 退出 | reset 重新开始")


def main():
    """主程序"""
    business_line = choose_business_line()
    print_intro(business_line)
    form = FormBasedDialogSystem(business_line)
    semantic_mapper = SemanticMapper()
    llm_client = build_llm_client()

    # 显示初始提示
    initial_prompt = form.get_initial_prompt()
    if initial_prompt:
        print("\n🤖 客服:")
        for line in initial_prompt.split("\n"):
            if line.strip():
                print(f"  {line}")

        # 显示初始提示（更贴近购物场景）
    while True:
        try:
            text = input("\n👤 用户: ").strip()
            if not text:
                continue
            
            low = text.lower()
            
            # 基本命令
            if low in {"exit", "quit", "q", "退出"}:
                print("👋 再见！")
                break
            if low in {"reset", "重置", "重新开始"}:
                form = FormBasedDialogSystem(business_line)
                print("🌟 好的，我们重新开始挑选～")
                intro = form.get_initial_prompt()
                if intro:
                    print("🤖 客服:")
                    for line in intro.split("\n"):
                        if line.strip():
                            print(f"  {line}")
                else:
                    print("🤖 客服: 可以先告诉我您想看电脑、手机还是平板呀～")
                continue

            # 餐饮业务线仍允许快捷切换，其余在苹果专卖店内部用品类槽位完成
            if any(k in text for k in ["餐饮", "订位", "预订"]) and business_line != "dining":
                business_line = "dining"
                form = FormBasedDialogSystem(business_line)
                print("🔁 已切换至【餐饮预订】")
                continue

            # 表单处理
            result = form.process_input(text, llm_client, semantic_mapper)
            resp = result.get("response", "")
            if resp:
                print("🤖 客服:")
                for line in resp.split("\n"):
                    if line.strip():
                        print(f"  {line}")
            
            # 检查是否需要退出（用户在订单确认后选择结束）
            if result.get("should_exit"):
                break

        except KeyboardInterrupt:
            print("\n👋 用户中断，已退出")
            break
        except Exception as e:
            print(f"❌ 运行时异常: {e}")


if __name__ == "__main__":
    main()

