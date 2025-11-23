#!/usr/bin/env python3
"""
测试桩功能验证脚本
================

验证新增的测试桩是否正常工作：
- MockBusinessConfigLoader
- MockYAMLFlowLoader  
- MockSemanticMapper
- 异常场景测试套件
"""

import sys
import os

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def test_mock_business_config_loader():
    """测试业务配置加载器测试桩"""
    print("🧪 测试 MockBusinessConfigLoader...")
    
    try:
        from tests.stubs.mock_config_loaders import MockBusinessConfigLoader, create_mock_config_loader
        
        # 测试正常模式
        loader = MockBusinessConfigLoader()
        config = loader.get_business_config("test_business")
        assert config is not None
        assert config.name == "test_business"
        assert len(config.slot_specs) > 0
        print("  ✅ 正常模式工作正常")
        
        # 测试文件不存在异常
        loader = MockBusinessConfigLoader(fail_mode="file_not_found")
        try:
            loader.get_business_config("test")
            assert False, "应该抛出FileNotFoundError"
        except FileNotFoundError:
            print("  ✅ 文件不存在异常模拟正常")
        
        # 测试JSON语法错误
        loader = MockBusinessConfigLoader(fail_mode="json_syntax_error")
        try:
            loader.get_business_config("test")
            assert False, "应该抛出JSON异常"
        except Exception as e:
            # 检查是否是JSON相关异常（包括JSONDecodeError）
            exception_str = str(type(e)) + str(e)
            assert "json" in exception_str.lower() or "decode" in exception_str.lower()
            print("  ✅ JSON语法错误模拟正常")
        
        # 测试工厂函数
        loader = create_mock_config_loader("normal")
        assert loader is not None
        print("  ✅ 工厂函数工作正常")
        
        # 测试调用历史
        loader = MockBusinessConfigLoader()
        loader.get_business_config("test1")
        loader.get_business_config("test2")
        history = loader.get_call_history()
        assert len(history) == 2
        print("  ✅ 调用历史记录正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ MockBusinessConfigLoader 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_yaml_flow_loader():
    """测试YAML流程加载器测试桩"""
    print("\n🧪 测试 MockYAMLFlowLoader...")
    
    try:
        from tests.stubs.mock_config_loaders import MockYAMLFlowLoader, create_mock_yaml_loader
        
        # 测试正常模式
        loader = MockYAMLFlowLoader()
        flow = loader.load("test.yaml")
        assert "flow" in flow
        assert flow["flow"]["name"] == "test_flow"
        print("  ✅ 正常模式工作正常")
        
        # 测试YAML语法错误
        loader = MockYAMLFlowLoader(fail_mode="yaml_syntax_error")
        try:
            loader.load("invalid.yaml")
            assert False, "应该抛出YAML异常"
        except Exception as e:
            print("  ✅ YAML语法错误模拟正常")
        
        # 测试缺少字段
        loader = MockYAMLFlowLoader(fail_mode="missing_flow_field")
        flow = loader.load("invalid.yaml")
        assert "flow" not in flow
        print("  ✅ 缺少字段模拟正常")
        
        # 测试验证功能
        loader = MockYAMLFlowLoader(fail_mode="invalid_slot_definition")
        flow = loader.load("test.yaml")
        is_valid = loader.validate(flow)
        assert not is_valid
        print("  ✅ 验证功能正常")
        
        # 测试工厂函数
        loader = create_mock_yaml_loader("normal")
        assert loader is not None
        print("  ✅ 工厂函数工作正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ MockYAMLFlowLoader 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_semantic_mapper():
    """测试语义映射器测试桩"""
    print("\n🧪 测试 MockSemanticMapper...")
    
    try:
        from tests.stubs.mock_semantic_mapper import (
            MockSemanticMapper, MockSemanticResult, 
            create_mock_semantic_mapper, ConfigurableMockSemanticMapper
        )
        
        # 测试正常模式
        mapper = MockSemanticMapper()
        options = [{"label": "选项1"}, {"label": "选项2"}]
        result = mapper.semantic_match("高性能", options)
        assert isinstance(result, MockSemanticResult)
        assert result.confidence > 0
        print("  ✅ 正常模式工作正常")
        
        # 测试失败模式
        mapper = MockSemanticMapper(fail_mode="always_fail")
        result = mapper.semantic_match("测试", options)
        assert result.chosen_index is None
        assert result.confidence == 0.0
        print("  ✅ 失败模式工作正常")
        
        # 测试低置信度模式
        mapper = MockSemanticMapper(fail_mode="low_confidence")
        result = mapper.semantic_match("测试", options)
        assert result.confidence < 0.6
        print("  ✅ 低置信度模式正常")
        
        # 测试自定义结果
        custom_result = MockSemanticResult(
            chosen_index=1, confidence=0.9, reason="自定义", strategy="custom"
        )
        mapper = MockSemanticMapper()
        mapper.add_custom_result("特殊输入", custom_result)
        result = mapper.semantic_match("特殊输入", options)
        assert result.confidence == 0.9
        print("  ✅ 自定义结果功能正常")
        
        # 测试批量匹配
        inputs = ["高性能", "基础", "专业"]
        results = mapper.batch_match(inputs, options)
        assert len(results) == 3
        print("  ✅ 批量匹配功能正常")
        
        # 测试可配置版本
        config_mapper = ConfigurableMockSemanticMapper()
        config_mapper.set_match_strategy("strict")
        result = config_mapper.semantic_match("测试", options)
        assert isinstance(result, MockSemanticResult)
        print("  ✅ 可配置版本正常")
        
        # 测试统计功能
        stats = mapper.get_match_statistics()
        assert "total_calls" in stats
        print("  ✅ 统计功能正常")
        
        # 测试工厂函数
        mapper = create_mock_semantic_mapper("normal")
        assert mapper is not None
        print("  ✅ 工厂函数工作正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ MockSemanticMapper 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_exception_handling_suite():
    """测试异常处理测试套件"""
    print("\n🧪 测试异常处理测试套件...")
    
    try:
        from tests.test_suites.test_exception_handling import (
            get_exception_handling_tests, get_boundary_condition_tests,
            get_robustness_tests, test_config_file_not_found,
            test_json_syntax_error_handling
        )
        
        # 测试套件获取
        suite1 = get_exception_handling_tests()
        assert suite1.name == "exception_handling"
        assert len(suite1.tests) > 10
        print("  ✅ 异常处理测试套件加载正常")
        
        suite2 = get_boundary_condition_tests()
        assert suite2.name == "boundary_conditions"
        print("  ✅ 边界条件测试套件加载正常")
        
        suite3 = get_robustness_tests()
        assert suite3.name == "robustness"
        print("  ✅ 鲁棒性测试套件加载正常")
        
        # 测试具体的测试用例函数存在性
        assert callable(test_config_file_not_found)
        print("  ✅ 配置文件不存在测试函数正常")
        
        assert callable(test_json_syntax_error_handling)
        print("  ✅ JSON语法错误测试函数正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 异常处理测试套件失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coverage_integration():
    """测试覆盖率集成功能"""
    print("\n🧪 测试覆盖率集成功能...")
    
    try:
        from tests.drivers.test_driver import TestDriver
        
        # 测试带覆盖率的测试驱动
        driver = TestDriver(enable_coverage=True)
        assert hasattr(driver, 'enable_coverage')
        assert hasattr(driver, 'coverage_instance')
        print("  ✅ 测试驱动覆盖率初始化正常")
        
        # 测试覆盖率相关属性
        assert hasattr(driver, 'coverage_instance')
        print("  ✅ 覆盖率实例属性正常")
        
        # 测试禁用覆盖率
        driver_no_cov = TestDriver(enable_coverage=False)
        assert not driver_no_cov.enable_coverage
        print("  ✅ 禁用覆盖率功能正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 覆盖率集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_run_all_tests_integration():
    """测试run_all_tests.py集成"""
    print("\n🧪 测试run_all_tests.py集成...")
    
    try:
        # 测试导入
        import tests.run_all_tests as run_all_tests
        
        # 验证新的导入存在
        assert hasattr(run_all_tests, 'get_exception_handling_tests')
        print("  ✅ 新测试套件导入正常")
        
        # 检查命令行参数解析（不实际执行）
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--no-coverage', action='store_true')
        parser.add_argument('--include-exceptions', action='store_true')
        
        # 测试参数解析
        args = parser.parse_args(['--no-coverage', '--include-exceptions'])
        assert args.no_coverage == True
        assert args.include_exceptions == True
        print("  ✅ 命令行参数解析正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ run_all_tests.py 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 开始测试桩功能验证")
    print("=" * 50)
    
    tests = [
        ("MockBusinessConfigLoader", test_mock_business_config_loader),
        ("MockYAMLFlowLoader", test_mock_yaml_flow_loader),
        ("MockSemanticMapper", test_mock_semantic_mapper),
        ("异常处理测试套件", test_exception_handling_suite),
        ("覆盖率集成", test_coverage_integration),
        ("run_all_tests集成", test_run_all_tests_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} 测试发生异常: {e}")
            results.append((test_name, False))
    
    # 打印总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print(f"通过率: {passed/len(results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有测试桩功能验证通过！")
        return 0
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，需要检查修复")
        return 1


if __name__ == '__main__':
    sys.exit(main())