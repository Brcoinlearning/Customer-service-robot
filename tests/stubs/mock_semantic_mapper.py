"""
语义映射器测试桩
===============

目的：
1. 模拟语义映射器的各种返回结果
2. 控制语义匹配的成功/失败场景
3. 支持自定义匹配规则和置信度
4. 测试语义映射相关的边界情况

设计：
- MockSemanticMapper：模拟语义映射行为
- 支持可配置的匹配结果和失败模式
- 记录所有调用历史便于测试验证
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class MockSemanticResult:
    """模拟语义匹配结果"""
    chosen_index: Optional[int]
    confidence: float
    reason: str
    strategy: str  # 'keyword' | 'fallback' | 'none'


class MockSemanticMapper:
    """
    语义映射器测试桩
    
    模拟语义映射器的行为，支持：
    - 可控的匹配结果
    - 不同置信度级别
    - 各种失败场景
    - 自定义匹配规则
    """
    
    def __init__(self, fail_mode: str = None, custom_results: Dict[str, MockSemanticResult] = None):
        """
        初始化Mock语义映射器
        
        Args:
            fail_mode: 失败模式
                - None: 正常模式
                - "always_fail": 总是匹配失败
                - "low_confidence": 总是返回低置信度
                - "random_error": 随机抛出异常
                - "timeout": 模拟超时
            custom_results: 自定义结果映射 {输入: 结果}
        """
        self.fail_mode = fail_mode
        self.custom_results = custom_results or {}
        self.call_history = []
        self.confidence_threshold = 0.6  # 默认置信度阈值
        
        # 预定义的匹配规则
        self.default_rules = {
            "高性能": MockSemanticResult(
                chosen_index=2,  # M3 Pro
                confidence=0.8,
                reason="关键词匹配：高性能→M3 Pro",
                strategy="keyword"
            ),
            "专业": MockSemanticResult(
                chosen_index=2,
                confidence=0.75,
                reason="关键词匹配：专业→M3 Pro", 
                strategy="keyword"
            ),
            "基础": MockSemanticResult(
                chosen_index=1,  # M3
                confidence=0.7,
                reason="关键词匹配：基础→M3",
                strategy="keyword"
            ),
            "剪辑": MockSemanticResult(
                chosen_index=3,  # M3 Max
                confidence=0.85,
                reason="关键词匹配：剪辑→M3 Max",
                strategy="keyword"
            ),
            "大容量": MockSemanticResult(
                chosen_index=3,  # 2TB
                confidence=0.75,
                reason="关键词匹配：大容量→2TB",
                strategy="keyword"
            )
        }
    
    def semantic_match(
        self,
        user_input: str,
        options: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> MockSemanticResult:
        """
        模拟语义匹配
        
        Args:
            user_input: 用户输入文本
            options: 候选选项列表
            context: 上下文信息
        
        Returns:
            匹配结果
        """
        # 记录调用历史
        self.call_history.append({
            "method": "semantic_match",
            "user_input": user_input,
            "options_count": len(options),
            "context": context
        })
        
        # 模拟各种失败场景
        if self.fail_mode == "always_fail":
            return MockSemanticResult(
                chosen_index=None,
                confidence=0.0,
                reason="模拟匹配失败",
                strategy="none"
            )
        
        elif self.fail_mode == "low_confidence":
            return MockSemanticResult(
                chosen_index=1,
                confidence=0.3,  # 低于阈值
                reason="模拟低置信度匹配",
                strategy="fallback"
            )
        
        elif self.fail_mode == "random_error":
            import random
            if random.random() < 0.3:  # 30%概率抛出异常
                raise Exception("Mock semantic mapping error")
        
        elif self.fail_mode == "timeout":
            import time
            time.sleep(2)  # 模拟超时
            raise TimeoutError("Semantic mapping timeout")
        
        # 检查自定义结果
        if user_input in self.custom_results:
            return self.custom_results[user_input]
        
        # 使用默认规则匹配
        return self._match_by_rules(user_input, options, context)
    
    def _match_by_rules(
        self,
        user_input: str,
        options: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> MockSemanticResult:
        """
        基于预定义规则进行匹配
        """
        user_input_lower = user_input.lower().strip()
        
        # 优先匹配完全匹配的规则
        for keyword, result in self.default_rules.items():
            if keyword in user_input_lower:
                # 检查索引是否在有效范围内
                if result.chosen_index and result.chosen_index <= len(options):
                    return result
        
        # 部分匹配
        for keyword, result in self.default_rules.items():
            if any(char in user_input_lower for char in keyword):
                # 降低置信度
                return MockSemanticResult(
                    chosen_index=result.chosen_index,
                    confidence=max(0.5, result.confidence - 0.2),
                    reason=f"部分匹配：{keyword}",
                    strategy="fallback"
                )
        
        # 无匹配
        return MockSemanticResult(
            chosen_index=None,
            confidence=0.0,
            reason="无语义匹配",
            strategy="none"
        )
    
    def batch_match(
        self,
        inputs: List[str],
        options: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[MockSemanticResult]:
        """
        批量语义匹配
        """
        results = []
        for input_text in inputs:
            try:
                result = self.semantic_match(input_text, options, context)
                results.append(result)
            except Exception as e:
                # 异常情况返回失败结果
                results.append(MockSemanticResult(
                    chosen_index=None,
                    confidence=0.0,
                    reason=f"批量匹配异常: {str(e)}",
                    strategy="none"
                ))
        return results
    
    def set_fail_mode(self, fail_mode: str):
        """设置失败模式"""
        self.fail_mode = fail_mode
    
    def add_custom_result(self, user_input: str, result: MockSemanticResult):
        """添加自定义匹配结果"""
        self.custom_results[user_input] = result
    
    def add_custom_rule(self, keyword: str, result: MockSemanticResult):
        """添加自定义匹配规则"""
        self.default_rules[keyword] = result
    
    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值"""
        self.confidence_threshold = threshold
    
    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self.call_history
    
    def reset_history(self):
        """重置调用历史"""
        self.call_history = []
    
    def get_match_statistics(self) -> Dict[str, Any]:
        """获取匹配统计信息"""
        if not self.call_history:
            return {"total_calls": 0}
        
        total = len(self.call_history)
        successful_matches = sum(1 for call in self.call_history if "semantic_match" in call.get("method", ""))
        
        return {
            "total_calls": total,
            "successful_matches": successful_matches,
            "success_rate": successful_matches / total if total > 0 else 0
        }


class ConfigurableMockSemanticMapper(MockSemanticMapper):
    """
    可配置的Mock语义映射器
    
    支持更细粒度的测试场景：
    - 按次数返回不同结果
    - 模拟性能问题
    - 自定义匹配策略
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_sequence = []  # 按顺序返回的结果列表
        self.current_index = 0
        self.simulate_delay = False
        self.delay_seconds = 0
        self.match_strategy = "default"  # "default", "strict", "fuzzy"
    
    def set_result_sequence(self, results: List[MockSemanticResult]):
        """
        设置结果序列，按调用顺序依次返回
        """
        self.result_sequence = results
        self.current_index = 0
    
    def set_match_strategy(self, strategy: str):
        """
        设置匹配策略
        
        Args:
            strategy: 匹配策略
                - "default": 默认匹配
                - "strict": 严格匹配（高置信度阈值）
                - "fuzzy": 模糊匹配（低置信度阈值）
        """
        self.match_strategy = strategy
        
        if strategy == "strict":
            self.confidence_threshold = 0.8
        elif strategy == "fuzzy":
            self.confidence_threshold = 0.4
        else:
            self.confidence_threshold = 0.6
    
    def semantic_match(
        self,
        user_input: str,
        options: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> MockSemanticResult:
        """覆盖父类方法，支持序列结果和策略"""
        # 记录调用
        self.call_history.append({
            "method": "semantic_match",
            "user_input": user_input,
            "options_count": len(options),
            "context": context,
            "strategy": self.match_strategy
        })
        
        # 模拟延迟
        if self.simulate_delay:
            import time
            time.sleep(self.delay_seconds)
        
        # 如果有结果序列，按序返回
        if self.result_sequence and self.current_index < len(self.result_sequence):
            result = self.result_sequence[self.current_index]
            self.current_index += 1
            return result
        
        # 应用匹配策略
        result = self._match_by_rules(user_input, options, context)
        
        if self.match_strategy == "strict" and result.confidence < self.confidence_threshold:
            return MockSemanticResult(
                chosen_index=None,
                confidence=result.confidence,
                reason=f"严格模式：置信度{result.confidence:.2f}低于阈值{self.confidence_threshold}",
                strategy="none"
            )
        elif self.match_strategy == "fuzzy":
            # 模糊模式：提高置信度
            return MockSemanticResult(
                chosen_index=result.chosen_index,
                confidence=min(0.9, result.confidence + 0.2),
                reason=f"模糊模式增强：{result.reason}",
                strategy=result.strategy
            )
        
        return result


# 便捷工厂函数
def create_mock_semantic_mapper(scenario: str = "normal") -> MockSemanticMapper:
    """
    创建预配置的Mock语义映射器
    
    Args:
        scenario: 测试场景名称
            - "normal": 正常工作模式
            - "failure": 模拟匹配失败
            - "low_confidence": 低置信度模式
            - "error": 随机错误模式
    
    Returns:
        配置好的MockSemanticMapper实例
    """
    scenarios = {
        "normal": MockSemanticMapper(),
        "failure": MockSemanticMapper(fail_mode="always_fail"),
        "low_confidence": MockSemanticMapper(fail_mode="low_confidence"),
        "error": MockSemanticMapper(fail_mode="random_error")
    }
    
    return scenarios.get(scenario, MockSemanticMapper())


def create_high_accuracy_mapper() -> MockSemanticMapper:
    """创建高准确度的Mock映射器"""
    mapper = MockSemanticMapper()
    
    # 添加更多精确的匹配规则
    mapper.add_custom_rule("视频剪辑", MockSemanticResult(
        chosen_index=3, confidence=0.9, reason="专业需求匹配", strategy="keyword"
    ))
    mapper.add_custom_rule("办公", MockSemanticResult(
        chosen_index=1, confidence=0.8, reason="基础需求匹配", strategy="keyword"
    ))
    
    return mapper


def create_unreliable_mapper() -> MockSemanticMapper:
    """创建不可靠的Mock映射器（用于测试错误处理）"""
    return ConfigurableMockSemanticMapper(fail_mode="random_error")