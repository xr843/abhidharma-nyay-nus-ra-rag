"""
预检索服务 - 异步预取相关问题的完整答案
"""
import asyncio
from typing import List, TYPE_CHECKING
from loguru import logger

from .vector_store import get_vector_store
from .cache_service import get_cache

if TYPE_CHECKING:
    from .ai_service import AIService

from ..models.schemas import ChatResponse


class PrefetchService:
    """预检索服务"""

    def __init__(self):
        """初始化预检索服务"""
        self.vector_store = get_vector_store()
        self.cache = get_cache()
        self.ai_service = None  # 延迟初始化，避免循环依赖

        # 预检索配置
        self.prefetch_enabled = True  # 是否启用预检索
        self.prefetch_count = 1  # 只预取第一个相关问题（最可能被点击）

        logger.info("预检索服务初始化完成")

    def set_ai_service(self, ai_service: 'AIService') -> None:
        """设置 AI 服务（避免循环依赖）"""
        self.ai_service = ai_service

    async def prefetch_related_questions(
        self,
        related_questions: List[str]
    ) -> None:
        """
        异步预取相关问题的完整答案

        Args:
            related_questions: 相关问题列表
        """
        if not self.prefetch_enabled or not related_questions or not self.ai_service:
            return

        # 只预取前 N 个问题（避免资源浪费）
        questions_to_prefetch = related_questions[:self.prefetch_count]

        logger.info(f"🚀 开始预检索 {len(questions_to_prefetch)} 个相关问题...")

        # 并发预取（但不阻塞主流程）
        tasks = [
            self._prefetch_single_question(q)
            for q in questions_to_prefetch
        ]

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"✅ 预检索完成")
        except Exception as e:
            logger.warning(f"预检索失败（不影响主流程）: {e}")

    async def _prefetch_single_question(self, question: str) -> None:
        """
        预取单个问题的完整答案

        Args:
            question: 问题文本
        """
        try:
            # 检查是否已经缓存
            cached = self.cache.get_cached_response(question)
            if cached:
                logger.debug(f"预检索跳过（已缓存）: {question[:30]}...")
                return

            # 1. 执行向量检索
            citations = self.vector_store.search(question)
            if not citations:
                logger.debug(f"预检索无结果: {question[:30]}...")
                return

            # 2. LLM 重排序（如果需要）
            display_k = self.ai_service.settings.retrieval_display_k
            if len(citations) > display_k:
                citations = await self.ai_service.rerank_citations(
                    question=question,
                    citations=citations,
                    top_k=display_k
                )

            # 3. 生成完整答案
            result = await self.ai_service.generate_answer(
                question=question,
                citations=citations,
                history=None  # 预检索不包含历史
            )

            # 4. 构建响应并缓存
            response = ChatResponse(
                answer=result["answer"],
                citations=citations,
                related_questions=result["related_questions"],
                session_id=""  # 预检索时无 session_id
            )

            self.cache.cache_response(question, response)
            logger.info(f"✅ 预检索并缓存完成: '{question[:30]}...'")

        except Exception as e:
            logger.warning(f"预检索单个问题失败: {question[:30]}... - {e}")


class PrefetchManager:
    """预检索管理器（单例）"""

    _instance: PrefetchService = None

    @classmethod
    def get_instance(cls) -> PrefetchService:
        """获取预检索服务实例"""
        if cls._instance is None:
            cls._instance = PrefetchService()
        return cls._instance


def get_prefetch_service() -> PrefetchService:
    """获取预检索服务实例（用于依赖注入）"""
    return PrefetchManager.get_instance()
