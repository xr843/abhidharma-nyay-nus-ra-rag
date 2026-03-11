"""
Pydantic数据模式定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TextChunk(BaseModel):
    """文献段落"""
    id: str
    text_id: str
    text_title: str
    volume: int
    chapter: Optional[str] = None
    section: Optional[str] = None
    content: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    relevance_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class TextMetadata(BaseModel):
    """文献元数据"""
    id: str
    title: str
    short_title: Optional[str] = None
    author: Optional[str] = None
    translator: Optional[str] = None
    volumes: int
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None


class Citation(BaseModel):
    """引文"""
    text_id: str
    text_title: str
    short_title: Optional[str] = None
    volume: int
    chapter: Optional[str] = None
    content: str
    relevance_score: float
    icon: Optional[str] = None
    color: Optional[str] = None


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # user / assistant
    content: str


class ChatSession(BaseModel):
    """对话会话"""
    id: str
    first_question: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """对话请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID，用于多轮对话")
    history: Optional[List[ChatMessage]] = Field(None, description="对话历史")


class ChatResponse(BaseModel):
    """对话响应"""
    answer: str = Field(..., description="AI回答")
    citations: List[Citation] = Field(default_factory=list, description="引用列表")
    related_questions: List[str] = Field(default_factory=list, description="相关问题")
    session_id: str = Field(..., description="会话ID")


class ContextRequest(BaseModel):
    """上下文请求"""
    text_id: str
    volume: int
    position: int
    range: int = 500


class ContextResponse(BaseModel):
    """上下文响应"""
    text_id: str
    text_title: str
    volume: int
    chapter: Optional[str] = None
    content: str
    highlight_start: int
    highlight_end: int


class HistoryResponse(BaseModel):
    """历史记录响应"""
    sessions: List[ChatSession]
    total: int


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: datetime

