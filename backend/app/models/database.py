"""
数据库模型定义
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()


class TextChunkModel(Base):
    """文献段落表"""
    __tablename__ = "text_chunks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text_id = Column(String(10), nullable=False, index=True)  # CBETA编号
    text_title = Column(String(100), nullable=False)
    volume = Column(Integer, nullable=False)  # 卷号
    chapter = Column(String(100), nullable=True)  # 品名
    section = Column(String(50), nullable=True)  # 节名
    content = Column(Text, nullable=False)  # 段落内容
    char_start = Column(Integer, nullable=True)  # 起始字符位置
    char_end = Column(Integer, nullable=True)  # 结束字符位置
    created_at = Column(DateTime, default=datetime.utcnow)
    

class TextMetadataModel(Base):
    """文献元数据表"""
    __tablename__ = "text_metadata"
    
    id = Column(String(10), primary_key=True)  # CBETA编号
    title = Column(String(100), nullable=False)
    short_title = Column(String(50), nullable=True)
    author = Column(String(50), nullable=True)
    translator = Column(String(50), nullable=True)
    volumes = Column(Integer, nullable=False)
    source = Column(String(100), nullable=True)
    license = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatSessionModel(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_question = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("ChatMessageModel", back_populates="session", cascade="all, delete-orphan")


class ChatMessageModel(Base):
    """对话消息表"""
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)  # 引用列表
    related_questions = Column(JSON, nullable=True)  # 相关问题
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSessionModel", back_populates="messages")


# 数据库引擎和会话
_engine = None
_async_session = None


async def init_db(database_url: str):
    """初始化数据库"""
    global _engine, _async_session
    
    _engine = create_async_engine(database_url, echo=False)
    _async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    return _engine


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    if _async_session is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    
    async with _async_session() as session:
        yield session

