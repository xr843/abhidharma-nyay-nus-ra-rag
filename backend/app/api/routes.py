"""
API路由定义
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from ..models.database import get_db
from ..models.schemas import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    HealthResponse,
    TextMetadata
)
from ..services.chat_service import ChatService
from ..services.vector_store import get_vector_store
from ..config import TEXT_METADATA

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    对话接口
    
    接收用户问题，返回AI回答和相关引文
    """
    try:
        chat_service = ChatService(db)
        response = await chat_service.chat(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    session_id: Optional[str] = Query(None, description="会话ID"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取历史记录
    """
    try:
        chat_service = ChatService(db)
        sessions, total = await chat_service.get_history(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        return HistoryResponse(sessions=sessions, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.delete("/history/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除会话
    """
    try:
        chat_service = ChatService(db)
        success = await chat_service.delete_session(session_id)
        if success:
            return {"status": "ok", "message": "会话已删除"}
        else:
            raise HTTPException(status_code=404, detail="会话不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.get("/texts")
async def get_texts():
    """
    获取文献列表
    """
    return {
        "texts": [
            TextMetadata(
                id=meta["id"],
                title=meta["title"],
                short_title=meta.get("short_title"),
                author=meta.get("author"),
                translator=meta.get("translator"),
                volumes=meta["volumes"],
                icon=meta.get("icon"),
                color=meta.get("color"),
                description=meta.get("description")
            )
            for meta in TEXT_METADATA.values()
        ]
    }


@router.get("/stats")
async def get_stats():
    """
    获取统计信息
    """
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        return {
            "status": "ok",
            "vector_store": stats,
            "texts": {
                text_id: {
                    "title": meta["title"],
                    "volumes": meta["volumes"]
                }
                for text_id, meta in TEXT_METADATA.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

