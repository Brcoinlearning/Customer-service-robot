#!/usr/bin/env python3
"""
增强的覆盖率测试脚本 (Enhanced Coverage Runner)
==============================================

功能扩展:
1. 若安装 coverage 库: 生成 XML(`coverage.xml`) + HTML(`htmlcov/`) + JSON + 终端汇总
2. 未安装 coverage 时: 回退使用 run_all_tests.py 并提示安装方式
3. 支持阈值: 环境变量 MIN_LINE_RATE 或脚本常量 DEFAULT_MIN_LINE_RATE
4. 集成 run_all_tests.py 运行器，包含异常测试套件
5. 详细的覆盖率统计和文件级分析
6. 支持CI/CD集成和自动化测试

使用示例:
    python tests/run_coverage.py                    # 普通运行
    python tests/run_coverage.py --html            # 生成HTML报告
    python tests/run_coverage.py --xml             # 生成XML报告  
    python tests/run_coverage.py --json            # 生成JSON报告
    python tests/run_coverage.py --threshold=85    # 设置覆盖率阈值
    MIN_LINE_RATE=0.85 python tests/run_coverage.py  # 动态阈值

退出码:
    0 正常且达到阈值
    1 测试失败或覆盖率低于阈值或发生异常
"""
import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

DEFAULT_MIN_LINE_RATE = 0.80  # 默认最小行覆盖率阈值
SOURCE_DIRS = ["src"]         # 覆盖统计范围
OMIT_PATTERNS = [             # 排除模式
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/site-packages/*",
    "*/venv/*",
    "*/.venv/*"
]


def _run_tests_only() -> int:
    """回退模式：未安装coverage时运行基础测试"""
    print("[Coverage] 未检测到 coverage 库，退回使用 run_all_tests.py 执行。")
    print("[Hint] 安装覆盖率支持: pip install coverage -i https://pypi.tuna.tsinghua.edu.cn/simple")
    
    # 使用项目的测试运行器
    test_script = Path(__file__).parent / "run_all_tests.py"
    if test_script.exists():
        print(f"[Test] 使用 {test_script} 运行测试...")
        return subprocess.call([
            sys.executable, str(test_script), 
            "--verbose", "--include-exceptions"
        ])
    else:
        # 回退到pytest
        try:
            import pytest  # noqa
            print("[Test] 使用 pytest 运行测试...")
            return subprocess.call([sys.executable, "-m", "pytest"])
        except ImportError:
            print("[Error] pytest 未安装，请先: pip install pytest")
            return 1


def _import_coverage():
    try:
        import coverage  # type: ignore
        return coverage
    except Exception as e:
        print(f"[Warn] 无法导入 coverage 库: {e}")
        return None


def _run_tests_with_coverage(cov_module, args) -> int:
    """使用coverage运行测试并生成报告"""
    try:
        # 初始化覆盖率收集器
        cov = cov_module.Coverage(
            source=SOURCE_DIRS, 
            branch=True,
            omit=OMIT_PATTERNS
        )
        cov.erase()
        
        print("[Coverage] 🚀 开始覆盖率测试...")
        print(f"[Coverage] 📁 源码目录: {', '.join(SOURCE_DIRS)}")
        
        # 开始覆盖率收集
        start_time = time.time()
        cov.start()
        
        # 运行测试
        exit_code = _run_project_tests()
        
        # 停止覆盖率收集
        cov.stop()
        cov.save()
        
        execution_time = time.time() - start_time
        print(f"[Coverage] ⏱️ 测试执行时间: {execution_time:.2f}秒")
        
        # 生成覆盖率统计
        coverage_stats = _generate_coverage_reports(cov, args)
        
        # 检查阈值
        threshold = args.threshold if hasattr(args, 'threshold') else float(os.getenv("MIN_LINE_RATE", DEFAULT_MIN_LINE_RATE))
        
        if exit_code != 0:
            print("[Result] ❌ 测试存在失败, 退出码!=0")
            return 1
            
        line_rate = coverage_stats.get('line_rate', 0)
        if line_rate < threshold * 100:
            print(f"[Result] ❌ 覆盖率 {line_rate:.1f}% 低于阈值 {threshold*100:.0f}%")
            return 1
            
        print(f"[Result] ✅ 测试通过且覆盖率 {line_rate:.1f}% 达标!")
        
        # 提示查看报告
        if hasattr(args, 'html') and args.html:
            print("[Open] 🌐 macOS 可执行: open htmlcov/index.html 查看详细报告")
        
        return 0
        
    except Exception as e:
        print(f"[Error] ❌ 运行覆盖率时出现异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


def _run_project_tests() -> int:
    """运行项目测试套件"""
    test_script = Path(__file__).parent / "run_all_tests.py"
    
    if test_script.exists():
        print("[Test] 📋 使用 run_all_tests.py 运行完整测试套件...")
        return subprocess.call([
            sys.executable, str(test_script), 
            "--verbose", "--include-exceptions", "--no-coverage"
        ])
    else:
        # 回退到pytest
        try:
            from importlib import import_module
            pytest = import_module("pytest")
            print("[Test] 📋 使用 pytest 运行测试...")
            return pytest.main([])
        except ImportError:
            print("[Error] ❌ pytest 未安装，请执行: pip install pytest")
            return 1


def _generate_coverage_reports(cov, args) -> Dict[str, Any]:
    """生成各种格式的覆盖率报告"""
    reports_dir = Path("coverage_reports")
    reports_dir.mkdir(exist_ok=True)
    
    stats = {}
    
    # 生成终端报告并获取统计
    print("[Coverage] 📊 生成覆盖率统计...")
    try:
        line_rate = cov.report(show_missing=True)
        stats['line_rate'] = line_rate
        print(f"[Coverage] 📈 总体覆盖率: {line_rate:.1f}%")
    except Exception as e:
        print(f"[Coverage] ⚠️ 生成终端报告失败: {e}")
        stats['line_rate'] = 0
    
    # 生成HTML报告
    if not hasattr(args, 'html') or args.html:
        try:
            html_dir = reports_dir / "html"
            cov.html_report(directory=str(html_dir))
            print(f"[Coverage] 📄 HTML报告: {html_dir}/index.html")
            stats['html_report'] = str(html_dir / "index.html")
        except Exception as e:
            print(f"[Coverage] ⚠️ 生成HTML报告失败: {e}")
    
    # 生成XML报告
    if not hasattr(args, 'xml') or args.xml:
        try:
            xml_file = reports_dir / "coverage.xml"
            cov.xml_report(outfile=str(xml_file))
            print(f"[Coverage] 📄 XML报告: {xml_file}")
            stats['xml_report'] = str(xml_file)
        except Exception as e:
            print(f"[Coverage] ⚠️ 生成XML报告失败: {e}")
    
    # 生成JSON报告
    if hasattr(args, 'json') and args.json:
        try:
            json_file = reports_dir / "coverage.json"
            cov.json_report(outfile=str(json_file))
            print(f"[Coverage] 📄 JSON报告: {json_file}")
            stats['json_report'] = str(json_file)
        except Exception as e:
            print(f"[Coverage] ⚠️ 生成JSON报告失败: {e}")
    
    # 生成详细统计
    stats.update(_get_detailed_coverage_stats(cov))
    
    return stats


def _get_detailed_coverage_stats(cov) -> Dict[str, Any]:
    """获取详细的覆盖率统计信息"""
    try:
        coverage_data = cov.get_data()
        file_stats = {}
        
        for filename in coverage_data.measured_files():
            # 跳过测试文件和第三方库
            if any(pattern.replace('*', '') in filename for pattern in OMIT_PATTERNS):
                continue
                
            try:
                analysis = cov.analysis2(filename)
                executed_lines = len(analysis.executed)
                missing_lines = len(analysis.missing)
                total_lines = executed_lines + missing_lines
                
                if total_lines > 0:
                    coverage_pct = (executed_lines / total_lines) * 100
                    file_stats[filename] = {
                        'coverage': coverage_pct,
                        'executed': executed_lines,
                        'missing': missing_lines,
                        'total': total_lines
                    }
            except Exception:
                continue
        
        return {
            'file_count': len(file_stats),
            'file_stats': file_stats,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[Coverage] ⚠️ 获取详细统计失败: {e}")
        return {}


def _parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='增强的覆盖率测试运行器')
    
    parser.add_argument('--html', action='store_true', default=True,
                       help='生成HTML格式报告 (默认启用)')
    parser.add_argument('--xml', action='store_true', default=True,
                       help='生成XML格式报告 (默认启用)')
    parser.add_argument('--json', action='store_true',
                       help='生成JSON格式报告')
    parser.add_argument('--threshold', type=float, 
                       default=float(os.getenv("MIN_LINE_RATE", DEFAULT_MIN_LINE_RATE)),
                       help=f'覆盖率阈值 (默认: {DEFAULT_MIN_LINE_RATE*100:.0f}%%)')
    parser.add_argument('--no-html', action='store_true',
                       help='禁用HTML报告生成')
    parser.add_argument('--no-xml', action='store_true',
                       help='禁用XML报告生成')
    
    args = parser.parse_args()
    
    # 处理禁用选项
    if args.no_html:
        args.html = False
    if args.no_xml:
        args.xml = False
    
    return args


def main():
    """主函数"""
    # 解析参数
    args = _parse_arguments()
    
    # 显示启动信息
    print("🚀 增强的覆盖率测试运行器")
    print("=" * 50)
    print(f"📁 源码目录: {', '.join(SOURCE_DIRS)}")
    print(f"🎯 覆盖率阈值: {args.threshold*100:.0f}%")
    print(f"📊 生成报告: HTML={args.html}, XML={args.xml}, JSON={args.json}")
    print("-" * 50)
    
    # 检查coverage库
    cov_module = _import_coverage()
    if cov_module is None:
        code = _run_tests_only()
        sys.exit(code)
    
    # 运行覆盖率测试
    code = _run_tests_with_coverage(cov_module, args)
    sys.exit(code)


if __name__ == "__main__":
    main()
