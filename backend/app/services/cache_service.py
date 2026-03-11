"""
缓存服务 - 高频问题缓存机制
"""
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from ..config import get_settings
from ..models.schemas import ChatResponse


class QuestionCache:
    """问题缓存管理器"""

    def __init__(self):
        """初始化缓存"""
        self.settings = get_settings()
        self.cache_dir = Path(self.settings.chroma_persist_dir).parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "question_cache.json"

        # 缓存配置
        self.cache_ttl = timedelta(days=30)  # 缓存有效期30天（佛学文献不会变化）
        self.similarity_threshold = 0.95  # 问题相似度阈值
        self.max_cache_size = 1000  # 最大缓存条目数

        # 加载缓存
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()

        logger.info(f"问题缓存初始化完成，当前缓存 {len(self._cache)} 个问题")

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """从文件加载缓存"""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 清理过期缓存
            now = datetime.now()
            valid_cache = {}
            for key, value in cache_data.items():
                expire_time = datetime.fromisoformat(value.get('expire_at', '2000-01-01'))
                if expire_time > now:
                    valid_cache[key] = value

            logger.info(f"加载缓存成功，有效条目 {len(valid_cache)}/{len(cache_data)}")
            return valid_cache

        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return {}

    def _save_cache(self) -> None:
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def _compute_question_hash(self, question: str) -> str:
        """
        计算问题的哈希值（用于精确匹配）

        Args:
            question: 用户问题

        Returns:
            问题的 MD5 哈希值
        """
        # 标准化：去除空格、标点，转小写
        normalized = question.strip().lower()
        for char in ['？', '?', '。', '.', '！', '!', '，', ',', ' ']:
            normalized = normalized.replace(char, '')

        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def get_cached_response(
        self,
        question: str,
        use_embedding: bool = False
    ) -> Optional[ChatResponse]:
        """
        获取缓存的答案

        Args:
            question: 用户问题
            use_embedding: 是否使用向量相似度（暂未实现，预留接口）

        Returns:
            缓存的响应，如果未命中则返回 None
        """
        # 精确匹配（基于哈希）
        question_hash = self._compute_question_hash(question)

        if question_hash in self._cache:
            cached_data = self._cache[question_hash]

            # 检查是否过期
            expire_time = datetime.fromisoformat(cached_data['expire_at'])
            if expire_time > datetime.now():
                # 更新命中次数和最后访问时间
                cached_data['hit_count'] = cached_data.get('hit_count', 0) + 1
                cached_data['last_access'] = datetime.now().isoformat()
                self._save_cache()

                logger.info(f"缓存命中：'{question[:30]}...' (命中次数: {cached_data['hit_count']})")

                # 返回缓存的响应
                return ChatResponse(**cached_data['response'])

        logger.debug(f"缓存未命中：'{question[:30]}...'")
        return None

    def cache_response(
        self,
        question: str,
        response: ChatResponse
    ) -> None:
        """
        缓存问答结果

        Args:
            question: 用户问题
            response: 系统响应
        """
        question_hash = self._compute_question_hash(question)

        # 检查缓存大小，如果超限则清理最少使用的条目
        if len(self._cache) >= self.max_cache_size:
            self._evict_least_used()

        # 存储缓存
        self._cache[question_hash] = {
            'question': question,
            'response': response.model_dump(),
            'cached_at': datetime.now().isoformat(),
            'expire_at': (datetime.now() + self.cache_ttl).isoformat(),
            'hit_count': 0,
            'last_access': datetime.now().isoformat()
        }

        self._save_cache()
        logger.info(f"已缓存问题：'{question[:30]}...'")

    def _evict_least_used(self) -> None:
        """清理最少使用的缓存条目（LFU策略）"""
        if not self._cache:
            return

        # 找到命中次数最少的条目
        least_used_key = min(
            self._cache.keys(),
            key=lambda k: (
                self._cache[k].get('hit_count', 0),
                self._cache[k].get('last_access', '2000-01-01')
            )
        )

        removed_question = self._cache[least_used_key]['question']
        del self._cache[least_used_key]

        logger.info(f"缓存已满，清理最少使用条目：'{removed_question[:30]}...'")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_hits = sum(item.get('hit_count', 0) for item in self._cache.values())

        return {
            'total_cached': len(self._cache),
            'total_hits': total_hits,
            'cache_file': str(self.cache_file),
            'cache_ttl_days': self.cache_ttl.days
        }

    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._save_cache()
        logger.info("缓存已清空")


class CacheManager:
    """缓存管理器（单例）"""

    _instance: Optional[QuestionCache] = None

    @classmethod
    def get_instance(cls) -> QuestionCache:
        """获取缓存实例"""
        if cls._instance is None:
            cls._instance = QuestionCache()
        return cls._instance


def get_cache() -> QuestionCache:
    """获取缓存实例（用于依赖注入）"""
    return CacheManager.get_instance()
