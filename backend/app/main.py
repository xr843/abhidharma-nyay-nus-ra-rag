"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from .config import get_settings
from .models.database import init_db
from .api.routes import router


# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    
    # 启动时初始化
    logger.info("正在初始化数据库...")
    await init_db(settings.database_url)
    logger.info("数据库初始化完成")
    
    logger.info(f"应用启动完成，环境: {settings.app_env}")
    
    yield
    
    # 关闭时清理
    logger.info("应用正在关闭...")


# 创建FastAPI应用
app = FastAPI(
    title="《顺正理论》资料库",
    description="基于AI的俱舍学文献智能问答系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "《顺正理论》资料库",
        "version": "1.0.0",
        "description": "基于AI的俱舍学文献智能问答系统",
        "docs": "/docs",
        "api": "/api"
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug
    )

