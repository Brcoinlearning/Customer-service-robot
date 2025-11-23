"""
测试驱动工具类 (Test Driver Utilities)
====================================

提供测试驱动的辅助功能：
- 配置管理
- 测试发现
- 报告格式化
- 性能分析
- 通知发送
"""

import os
import sys
import json
import configparser
import time
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

# 可选依赖处理
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class TestConfig:
    """测试配置数据类"""
    timeout: float = 30.0
    parallel: bool = False
    max_workers: int = 4
    retry_count: int = 0
    fail_fast: bool = False
    coverage_enabled: bool = True
    coverage_threshold: float = 80.0
    output_dir: str = "test_reports"
    verbose: bool = True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file or "tests/test_config.ini"
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
                print(f"✅ 配置文件已加载: {self.config_file}")
            else:
                print(f"⚠️ 配置文件不存在，使用默认配置: {self.config_file}")
                self._create_default_config()
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config.add_section('test_execution')
        self.config.set('test_execution', 'default_timeout', '30.0')
        self.config.set('test_execution', 'parallel_execution', 'false')
        
        self.config.add_section('coverage')
        self.config.set('coverage', 'enable_coverage', 'true')
        self.config.set('coverage', 'min_coverage_threshold', '80.0')
        
        self.config.add_section('reporting')
        self.config.set('reporting', 'output_dir', 'test_reports')
        self.config.set('reporting', 'generate_html', 'true')
    
    def get_test_config(self) -> TestConfig:
        """获取测试配置"""
        try:
            return TestConfig(
                timeout=self.config.getfloat('test_execution', 'default_timeout', fallback=30.0),
                parallel=self.config.getboolean('test_execution', 'parallel_execution', fallback=False),
                max_workers=self.config.getint('test_execution', 'max_workers', fallback=4),
                retry_count=self.config.getint('test_execution', 'retry_count', fallback=0),
                fail_fast=self.config.getboolean('test_execution', 'fail_fast', fallback=False),
                coverage_enabled=self.config.getboolean('coverage', 'enable_coverage', fallback=True),
                coverage_threshold=self.config.getfloat('coverage', 'min_coverage_threshold', fallback=80.0),
                output_dir=self.config.get('reporting', 'output_dir', fallback='test_reports'),
                verbose=self.config.getboolean('logging', 'verbose_output', fallback=True)
            )
        except Exception as e:
            print(f"⚠️ 解析配置失败，使用默认值: {e}")
            return TestConfig()
    
    def get_coverage_config(self) -> Dict[str, Any]:
        """获取覆盖率配置"""
        try:
            # 解析source_dirs（可能是JSON格式的列表）
            source_dirs_str = self.config.get('coverage', 'source_dirs', fallback='["src"]')
            try:
                source_dirs = json.loads(source_dirs_str)
            except json.JSONDecodeError:
                source_dirs = ['src']
            
            # 解析omit_patterns
            omit_patterns_str = self.config.get('coverage', 'omit_patterns', 
                                              fallback='["*/tests/*", "*/test_*", "*/__pycache__/*"]')
            try:
                omit_patterns = json.loads(omit_patterns_str)
            except json.JSONDecodeError:
                omit_patterns = ["*/tests/*", "*/test_*", "*/__pycache__/*"]
            
            return {
                'source_dirs': source_dirs,
                'omit_patterns': omit_patterns,
                'branch_coverage': self.config.getboolean('coverage', 'branch_coverage', fallback=True),
                'threshold': self.config.getfloat('coverage', 'min_coverage_threshold', fallback=80.0)
            }
        except Exception as e:
            print(f"⚠️ 解析覆盖率配置失败: {e}")
            return {
                'source_dirs': ['src'],
                'omit_patterns': ["*/tests/*", "*/test_*", "*/__pycache__/*"],
                'branch_coverage': True,
                'threshold': 80.0
            }


class TestDiscovery:
    """测试发现工具"""
    
    def __init__(self, config: ConfigManager = None):
        """
        初始化测试发现工具
        
        Args:
            config: 配置管理器
        """
        self.config = config or ConfigManager()
    
    def discover_test_files(self, root_dir: str = "tests") -> List[str]:
        """
        发现测试文件
        
        Args:
            root_dir: 搜索根目录
            
        Returns:
            测试文件路径列表
        """
        try:
            patterns = json.loads(
                self.config.config.get('test_discovery', 'test_file_patterns', 
                                     fallback='["test_*.py", "*_test.py"]')
            )
        except:
            patterns = ["test_*.py", "*_test.py"]
        
        test_files = []
        root_path = Path(root_dir)
        
        for pattern in patterns:
            test_files.extend(root_path.rglob(pattern))
        
        return [str(f) for f in test_files]
    
    def load_test_functions(self, test_file: str) -> List[Callable]:
        """
        从测试文件加载测试函数
        
        Args:
            test_file: 测试文件路径
            
        Returns:
            测试函数列表
        """
        test_functions = []
        
        try:
            # 动态导入测试模块
            spec = importlib.util.spec_from_file_location("test_module", test_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找测试函数
            prefix = self.config.config.get('test_discovery', 'test_function_prefix', fallback='test_')
            
            for name in dir(module):
                if name.startswith(prefix) and callable(getattr(module, name)):
                    test_functions.append(getattr(module, name))
        
        except Exception as e:
            print(f"⚠️ 加载测试文件失败 {test_file}: {e}")
        
        return test_functions


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        """初始化性能监控器"""
        self.process = None
        if PSUTIL_AVAILABLE:
            import psutil
            self.process = psutil.Process()
        self.start_time = None
        self.start_memory = None
        
    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        try:
            if self.process:
                self.start_memory = self.process.memory_info().rss
            else:
                self.start_memory = 0
        except:
            self.start_memory = 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if self.start_time is None:
            return {}
        
        try:
            if self.process:
                current_memory = self.process.memory_info().rss
                cpu_percent = self.process.cpu_percent()
                
                return {
                    'duration': time.time() - self.start_time,
                    'memory_usage_mb': current_memory / 1024 / 1024,
                    'memory_delta_mb': (current_memory - self.start_memory) / 1024 / 1024,
                    'cpu_percent': cpu_percent,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'duration': time.time() - self.start_time,
                    'timestamp': datetime.now().isoformat(),
                    'note': 'psutil not available, limited metrics'
                }
        except Exception as e:
            return {'error': str(e)}


class ReportFormatter:
    """报告格式化器"""
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化持续时间"""
        if seconds < 1:
            return f"{seconds*1000:.1f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """格式化百分比"""
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def format_memory(bytes_value: float) -> str:
        """格式化内存大小"""
        if bytes_value < 1024:
            return f"{bytes_value:.1f}B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value/1024:.1f}KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value/1024/1024:.1f}MB"
        else:
            return f"{bytes_value/1024/1024/1024:.1f}GB"
    
    @staticmethod
    def create_progress_bar(current: int, total: int, width: int = 40) -> str:
        """创建进度条"""
        if total == 0:
            return f"[{'█' * width}] 0/0"
        
        progress = current / total
        filled_width = int(width * progress)
        bar = '█' * filled_width + '░' * (width - filled_width)
        percentage = progress * 100
        
        return f"[{bar}] {current}/{total} ({percentage:.1f}%)"
    
    @staticmethod
    def generate_summary_table(data: List[Dict[str, Any]], headers: List[str]) -> str:
        """生成汇总表格"""
        if not data or not headers:
            return ""
        
        # 计算列宽
        col_widths = []
        for header in headers:
            max_width = len(header)
            for row in data:
                cell_value = str(row.get(header, ""))
                max_width = max(max_width, len(cell_value))
            col_widths.append(max_width + 2)
        
        # 生成表格
        lines = []
        
        # 标题行
        header_line = "|"
        for i, header in enumerate(headers):
            header_line += f" {header:<{col_widths[i]-1}}|"
        lines.append(header_line)
        
        # 分隔行
        separator = "|"
        for width in col_widths:
            separator += "-" * width + "|"
        lines.append(separator)
        
        # 数据行
        for row in data:
            data_line = "|"
            for i, header in enumerate(headers):
                cell_value = str(row.get(header, ""))
                data_line += f" {cell_value:<{col_widths[i]-1}}|"
            lines.append(data_line)
        
        return "\n".join(lines)


class NotificationSender:
    """通知发送器"""
    
    def __init__(self, config: ConfigManager = None):
        """
        初始化通知发送器
        
        Args:
            config: 配置管理器
        """
        self.config = config or ConfigManager()
    
    def send_notification(self, title: str, message: str, test_stats: Dict[str, Any] = None):
        """
        发送测试完成通知
        
        Args:
            title: 通知标题
            message: 通知消息
            test_stats: 测试统计信息
        """
        try:
            enabled = self.config.config.getboolean('notifications', 'enable_notifications', fallback=False)
            if not enabled:
                return
            
            # 检查是否只在失败时通知
            notify_failure_only = self.config.config.getboolean('notifications', 'notify_on_failure_only', fallback=True)
            if notify_failure_only and test_stats:
                failed_count = test_stats.get('failed', 0) + test_stats.get('errors', 0)
                if failed_count == 0:
                    return
            
            # 发送Webhook通知
            webhook_url = self.config.config.get('notifications', 'notification_webhook', fallback='')
            if webhook_url:
                self._send_webhook(webhook_url, title, message, test_stats)
            
            # 系统通知（macOS/Linux）
            self._send_system_notification(title, message)
            
        except Exception as e:
            print(f"⚠️ 发送通知失败: {e}")
    
    def _send_webhook(self, url: str, title: str, message: str, stats: Dict[str, Any] = None):
        """发送Webhook通知"""
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests库未安装，无法发送Webhook通知")
            return
            
        try:
            import requests
            payload = {
                "title": title,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            if stats:
                payload["statistics"] = stats
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ Webhook通知已发送: {url}")
            
        except Exception as e:
            print(f"❌ Webhook通知发送失败: {e}")
    
    def _send_system_notification(self, title: str, message: str):
        """发送系统通知"""
        try:
            import platform
            system = platform.system()
            
            if system == "Darwin":  # macOS
                os.system(f'osascript -e \'display notification "{message}" with title "{title}"\'')
            elif system == "Linux":  # Linux
                os.system(f'notify-send "{title}" "{message}"')
            
        except Exception as e:
            print(f"⚠️ 系统通知发送失败: {e}")


# 导入工具函数
def get_project_root() -> Path:
    """获取项目根目录"""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / "requirements.txt").exists() or (current / "setup.py").exists():
            return current
        current = current.parent
    return Path.cwd()


def setup_test_environment():
    """设置测试环境"""
    project_root = get_project_root()
    
    # 添加项目路径到sys.path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 添加src路径
    src_path = project_root / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # 设置环境变量
    os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)
    
    return project_root