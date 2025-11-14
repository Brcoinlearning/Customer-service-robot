import os
import sys

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser.dsl_parser import DSLParser
from interpreter.interpreter import DSLInterpreter
from llm.spark_client import SparkLLMClient
from config.settings import Config
from core.enhanced_context import EnhancedConversationContext
from knowledge.product_knowledge import ProductKnowledge
from knowledge.dining_knowledge import DiningKnowledgeProvider

def load_dsl_script(file_path: str) -> str:
    """加载DSL脚本文件"""
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(script_dir, file_path)
        print(f"尝试加载DSL脚本: {full_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"DSL脚本加载成功，内容长度: {len(content)} 字符")
            return content
    except FileNotFoundError:
        print(f"错误: 找不到DSL脚本文件 {full_path}")
        return ""
    except Exception as e:
        print(f"加载DSL脚本时发生错误: {e}")
        return ""

def main():
    print("=" * 50)
    print("DSL客服机器人启动中...")
    print("=" * 50)
    
    print("步骤1: 选择并加载DSL脚本...")
    print("可选脚本:")
    print("  1) 电商顾问 (ecommerce.dsl)")
    print("  2) 餐饮预订 (dining.dsl)")
    choice = input("请输入序号选择脚本，回车使用默认[1]: ").strip()
    if choice == "2":
        selected_script_path = "src/scripts/dining.dsl"
        selected_provider = "dining"
    else:
        selected_script_path = Config.DSL_SCRIPT_PATH
        selected_provider = "product"
    dsl_content = load_dsl_script(selected_script_path)
    if not dsl_content:
        print("❌ DSL脚本加载失败，程序退出")
        return
    print("✅ DSL脚本加载成功")
    
    # 2. 解析DSL
    print("步骤2: 正在解析DSL脚本...")
    parser = DSLParser()
    try:
        parsed_dsl = parser.parse(dsl_content)
        print(f"✅ DSL解析成功: 找到 {len(parsed_dsl['intents'])} 个意图, {len(parsed_dsl['rules'])} 个规则")
        
        print("解析到的意图:")
        for intent_name, description in parsed_dsl['intents'].items():
            print(f"  - {intent_name}: {description}")
            
    except Exception as e:
        print(f"❌ DSL解析错误: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 初始化解释器、上下文管理器和知识库
    print("步骤3: 正在初始化解释器...")
    try:
        interpreter = DSLInterpreter(parsed_dsl)
        context_manager = EnhancedConversationContext()
        context_manager.update_context("user_id", "current_user")
        if selected_provider == "dining":
            knowledge = DiningKnowledgeProvider()
        else:
            knowledge = ProductKnowledge()
        print("✅ 解释器和知识库初始化成功")
    except Exception as e:
        print(f"❌ 解释器或知识库初始化失败: {e}")
        return

    # 4. 初始化LLM客户端 - 使用配置类
    print("步骤4: 正在初始化LLM客户端...")
    try:
        llm_client = SparkLLMClient(**Config.get_llm_config())  # 使用配置类
        print("✅ LLM客户端初始化成功")
    except Exception as e:
        print(f"❌ LLM客户端初始化失败: {e}")
        return
    
    print("\n" + "=" * 50)
    print("🎉 DSL客服机器人启动完成！")
    print("可用指令:")
    print("  - 输入任何问题与机器人对话")
    print("  - 输入 'exit' 退出程序")
    print("=" * 50)
    
    # 5. 主循环
    while True:
        try:
            user_input = input("\n👤 用户: ").strip()
            
            if user_input.lower() == 'exit':
                print("再见！")
                break
            
            if not user_input:
                continue
            
            # 使用LLM识别意图（携带当前上下文摘要）
            print("🤖 正在分析意图...", end="")
            context_for_llm = context_manager.get_context()
            detected_intent = llm_client.detect_intent(user_input, parsed_dsl['intents'], context_for_llm)
            print(f" [{detected_intent}]")

            # 更新上下文
            context_manager.update_context("current_intent", detected_intent)
            context_manager.add_message("user", user_input)

            # 构造传给解释器的上下文：包含原始上下文、知识库引用、管理器引用和本轮输入
            ctx = context_manager.get_context()
            ctx["_manager"] = context_manager
            ctx["user_input"] = user_input
            ctx["knowledge"] = knowledge

            # 执行DSL规则 - 传递上下文
            responses = interpreter.execute(detected_intent, ctx)

            # 输出响应并更新上下文
            print("🤖 客服:", end="")
            for i, response in enumerate(responses):
                if i == 0:
                    print(f" {response}")
                else:
                    print(f"       {response}")
            
            # 将机器人响应添加到上下文
            for response in responses:
                context_manager.add_message("assistant", response)
                    
        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()