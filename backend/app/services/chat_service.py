"""
对话服务 - 整合向量检索和AI生成
"""
import uuid
import asyncio
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger

from .vector_store import get_vector_store
from .ai_service import get_ai_service
from .cache_service import get_cache
from .prefetch_service import get_prefetch_service
from ..models.database import ChatSessionModel, ChatMessageModel
from ..models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    ChatSession,
    Citation
)


class ChatService:
    """对话服务"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化对话服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.vector_store = get_vector_store()
        self.ai_service = get_ai_service()
        self.cache = get_cache()  # 初始化缓存
        self.prefetch = get_prefetch_service()  # 初始化预检索服务

        # 设置 AI 服务引用（避免循环依赖）
        self.prefetch.set_ai_service(self.ai_service)
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理用户对话请求
        
        Args:
            request: 对话请求
            
        Returns:
            对话响应
        """
        question = request.question.strip()
        session_id = request.session_id
        history = request.history or []

        # 检查缓存（仅当无历史对话时才使用缓存）
        # 原因：有历史对话时，答案可能依赖上下文，不应使用全局缓存
        if not history:
            cached_response = self.cache.get_cached_response(question)
            if cached_response:
                # 缓存命中，直接返回
                # 但需要更新 session_id
                if not session_id:
                    session = await self._create_session(question)
                    session_id = session.id

                # 保存消息到数据库
                await self._save_message(
                    session_id=session_id,
                    role="user",
                    content=question
                )

                await self._save_message(
                    session_id=session_id,
                    role="assistant",
                    content=cached_response.answer,
                    citations=[c.model_dump() for c in cached_response.citations],
                    related_questions=cached_response.related_questions
                )

                await self._update_session(session_id)

                # 返回缓存结果，更新 session_id
                cached_response.session_id = session_id
                logger.info(f"✅ 缓存命中，瞬间返回答案")
                return cached_response

        # 获取或创建会话
        if session_id:
            session = await self._get_session(session_id)
            if not session:
                session = await self._create_session(question)
                session_id = session.id
        else:
            session = await self._create_session(question)
            session_id = session.id
        
        # 检索相关文本
        citations = self.vector_store.search(question)
        logger.info(f"检索到 {len(citations)} 个相关段落（已过滤低相关度）")

        # 使用LLM进行二次排序（提高相关性）
        display_k = self.ai_service.settings.retrieval_display_k
        if len(citations) > display_k:
            citations = await self.ai_service.rerank_citations(
                question=question,
                citations=citations,
                top_k=display_k
            )
            logger.info(f"LLM重排序后保留 {len(citations)} 个最相关段落")

        # 生成回答
        result = await self.ai_service.generate_answer(
            question=question,
            citations=citations,
            history=history
        )
        
        answer = result["answer"]
        related_questions = result["related_questions"]
        
        # 保存消息到数据库
        await self._save_message(
            session_id=session_id,
            role="user",
            content=question
        )
        
        await self._save_message(
            session_id=session_id,
            role="assistant",
            content=answer,
            citations=[c.model_dump() for c in citations],  # 保存重排序后的引用
            related_questions=related_questions
        )

        # 更新会话
        await self._update_session(session_id)

        # 构建响应对象
        response = ChatResponse(
            answer=answer,
            citations=citations,  # 返回重排序后的引用
            related_questions=related_questions,
            session_id=session_id
        )

        # 缓存结果（仅当无历史对话时才缓存）
        if not history:
            self.cache.cache_response(question, response)
            logger.info(f"💾 答案已缓存，下次相同问题将瞬间返回")

        # 触发异步预检索（不阻塞返回）
        if related_questions:
            # 创建后台任务，不等待其完成
            asyncio.create_task(
                self.prefetch.prefetch_related_questions(related_questions)
            )
            logger.debug(f"🔮 已触发预检索任务（后台执行）")

        return response
    
    async def get_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple:
        """
        获取历史记录
        
        Args:
            session_id: 会话ID（可选）
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            (sessions, total)
        """
        query = select(ChatSessionModel).order_by(desc(ChatSessionModel.updated_at))
        
        if session_id:
            query = query.where(ChatSessionModel.id == session_id)
        
        # 获取总数
        count_result = await self.db.execute(
            select(ChatSessionModel)
        )
        total = len(count_result.scalars().all())
        
        # 获取分页数据
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        sessions = result.scalars().all()
        
        return [ChatSession.model_validate(s) for s in sessions], total
    
    async def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """获取会话的所有消息"""
        result = await self.db.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at)
        )
        messages = result.scalars().all()
        
        return [
            ChatMessage(role=m.role, content=m.content)
            for m in messages
        ]
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        session = await self._get_session(session_id)
        if session:
            await self.db.delete(session)
            await self.db.commit()
            return True
        return False
    
    async def _get_session(self, session_id: str) -> Optional[ChatSessionModel]:
        """获取会话"""
        result = await self.db.execute(
            select(ChatSessionModel).where(ChatSessionModel.id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def _create_session(self, first_question: str) -> ChatSessionModel:
        """创建新会话"""
        session = ChatSessionModel(
            id=str(uuid.uuid4()),
            first_question=first_question[:100],  # 截取前100字
            message_count=0
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def _update_session(self, session_id: str) -> None:
        """更新会话"""
        session = await self._get_session(session_id)
        if session:
            session.message_count += 2  # 一问一答
            session.updated_at = datetime.utcnow()
            await self.db.commit()
    
    async def _save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[List] = None,
        related_questions: Optional[List] = None
    ) -> ChatMessageModel:
        """保存消息"""
        message = ChatMessageModel(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
            related_questions=related_questions
        )
        self.db.add(message)
        await self.db.commit()
        return message

