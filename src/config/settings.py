"""
项目配置管理
"""

import os
from typing import Dict, Any

class Config:
    """配置管理类"""
    
    # DSL配置
    DSL_SCRIPT_PATH = "src/scripts/ecommerce.dsl"
    
    # LLM配置
    LLM_API_KEY = os.getenv("SPARK_API_KEY", "Bearer UuzpxGawsChJBdvajtVh:AEpkMYQXCPoRxvpQptmj")
    LLM_API_URL = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    LLM_MODEL = "lite"
    
    # 对话配置
    MAX_HISTORY_LENGTH = 10
    RESPONSE_TIMEOUT = 30
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """获取LLM配置"""
        return {
            "api_key": cls.LLM_API_KEY,
            "api_url": cls.LLM_API_URL,
            "model": cls.LLM_MODEL
        }