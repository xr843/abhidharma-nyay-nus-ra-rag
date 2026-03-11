"""
应用配置模块
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # DeepSeek API配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    
    # 应用配置
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./data/database.db"
    
    # ChromaDB配置
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "buddhist_texts"
    
    # 向量化配置
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 250  # 目标250字符，配合最小100字符，实际100-350字符
    chunk_overlap: int = 50  # 重叠50字符
    max_chunk_size: int = 500  # 最大500字符

    # 检索配置
    retrieval_top_k: int = 30  # 增加到30，提高召回率
    retrieval_min_score: float = 0.2  # 降低到20%，适配50-50混合检索权重
    retrieval_display_k: int = 8  # 增加到8，展示更多来源

    # 日志配置
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 文献信息配置
TEXT_METADATA = {
    "T1558": {
        "id": "T1558",
        "title": "阿毘達磨俱舍論",
        "short_title": "俱舍论",
        "author": "世亲菩萨",
        "translator": "玄奘法师",
        "volumes": 30,
        "icon": "📕",
        "color": "#e74c3c",
        "description": "俱舍学核心原典"
    },
    "T1562": {
        "id": "T1562",
        "title": "阿毘達磨順正理論",
        "short_title": "顺正理论",
        "author": "众贤论师",
        "translator": "玄奘法师",
        "volumes": 80,
        "icon": "📗",
        "color": "#27ae60",
        "description": "有部对俱舍论的回应"
    },
    "T1821": {
        "id": "T1821",
        "title": "俱舍論記",
        "short_title": "俱舍论记",
        "author": "普光法师",
        "translator": "",
        "volumes": 30,
        "icon": "📘",
        "color": "#3498db",
        "description": "俱舍论注释书"
    },
    "T1822": {
        "id": "T1822",
        "title": "俱舍論疏",
        "short_title": "俱舍论疏",
        "author": "法宝法师",
        "translator": "",
        "volumes": 30,
        "icon": "📙",
        "color": "#e67e22",
        "description": "俱舍论注释书"
    }
}


# 文献目录映射
TEXT_DIRS = {
    "T1558": "阿毘達磨俱舍論-30卷",
    "T1562": "阿毘達磨順正理論-80卷",
    "T1821": "俱舍論記-30卷",
    "T1822": "俱舍論疏-30卷"
}

