"""
向量存储服务 - 负责文本向量化和检索
"""
import os
import re
from typing import List, Optional, Dict, Any, Set
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from loguru import logger

from ..config import get_settings, TEXT_METADATA
from ..models.schemas import TextChunk, Citation


class VectorStore:
    """向量存储服务"""
    
    def __init__(self, persist_dir: Optional[str] = None):
        """
        初始化向量存储

        Args:
            persist_dir: 持久化目录，默认使用配置中的目录
        """
        self.settings = get_settings()
        self.persist_dir = persist_dir or self.settings.chroma_persist_dir
        self.collection_name = self.settings.chroma_collection_name

        # 确保目录存在
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False
            )
        )

        # 使用 GuwenBERT 古文专用 embedding 模型
        # ethanyt/guwenbert-base 专为古汉语优化，基于BERT在古文语料上预训练
        # 针对佛教经典、古籍文献有更强的语义理解能力
        # 尝试使用 GPU 加速（如果可用）
        import torch

        # 强制使用本地缓存，避免网络请求
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"使用设备: {device} {'(GPU 加速)' if device == 'cuda' else '(CPU 模式)'}")

        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="ethanyt/guwenbert-base",
            device=device
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,  # 使用中文 BGE embedding
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

        logger.info(f"向量存储初始化完成，集合: {self.collection_name}, 文档数: {self.collection.count()}")
        logger.info(f"使用 embedding 模型: ethanyt/guwenbert-base（古文专用优化）")
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        添加文本到向量存储
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            ids: ID列表
        """
        if not texts:
            return
        
        # ChromaDB会自动进行向量化
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"添加 {len(texts)} 个文档到向量存储")
    
    def add_text(
        self,
        text: str,
        metadata: Dict[str, Any],
        doc_id: str
    ) -> None:
        """添加单个文本"""
        self.add_texts([text], [metadata], [doc_id])
    
    def search(
        self,
        query: str,
        top_k: int = None,
        filter_dict: Optional[Dict] = None,
        min_score: float = None
    ) -> List[Citation]:
        """
        搜索相关文本（向量检索 + 关键词混合检索）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件
            min_score: 最低相关度阈值

        Returns:
            相关引文列表（已按相关度排序，过滤低分结果）
        """
        top_k = top_k or self.settings.retrieval_top_k
        min_score = min_score if min_score is not None else self.settings.retrieval_min_score

        # 提取查询中的关键词（用于混合检索加权）
        keywords = self._extract_keywords(query)

        # 执行向量查询
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter_dict
        )

        citations = []

        if results and results["documents"] and results["documents"][0]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
            distances = results["distances"][0] if results["distances"] else [0] * len(documents)

            for doc, meta, dist in zip(documents, metadatas, distances):
                # 将距离转换为相似度分数 (余弦距离转相似度)
                vector_similarity = 1 - dist

                # 计算关键词匹配加权分数
                keyword_boost = self._calculate_keyword_boost(doc, keywords)

                # 混合分数：向量相似度 * 0.7 + 关键词加权 * 0.3
                # GuwenBERT 古文语义能力强，进一步增加向量权重
                final_score = vector_similarity * 0.7 + keyword_boost * 0.3

                # 过滤低于阈值的结果
                if final_score < min_score:
                    continue

                text_id = meta.get("text_id", "")
                text_meta = TEXT_METADATA.get(text_id, {})

                citation = Citation(
                    text_id=text_id,
                    text_title=meta.get("text_title", ""),
                    short_title=text_meta.get("short_title", ""),
                    volume=meta.get("volume", 0),
                    chapter=meta.get("chapter"),
                    content=doc,
                    relevance_score=round(final_score, 4),
                    icon=text_meta.get("icon", "📄"),
                    color=text_meta.get("color", "#666666")
                )
                citations.append(citation)

        # 按混合分数重新排序
        citations.sort(key=lambda x: x.relevance_score, reverse=True)

        logger.info(f"检索完成: 查询='{query[:30]}...', 原始结果={top_k}, 过滤后={len(citations)}")

        return citations

    def _extract_keywords(self, query: str) -> Set[str]:
        """
        从查询中提取关键词

        Args:
            query: 查询文本

        Returns:
            关键词集合
        """
        # 佛学术语库（专为《俱舍论》《顺正理论》优化，共300+术语）
        buddhist_terms = {
            # === 基础佛学术语（原50个） ===
            '有漏', '无漏', '烦恼', '无明', '贪', '嗔', '痴', '慢', '疑', '见',
            '五蕴', '色', '受', '想', '行', '识', '十二处', '十八界',
            '四谛', '苦', '集', '灭', '道', '八正道', '涅槃', '解脱',
            '业', '果', '因', '缘', '缘起', '无常', '无我', '空',
            '戒', '定', '慧', '三学', '六度', '布施', '持戒', '忍辱', '精进', '禅定', '般若',
            '根', '力', '觉支', '道支', '三十七道品',
            '有为', '无为', '有漏法', '无漏法', '世间', '出世间',
            '阿罗汉', '菩萨', '佛', '声闻', '缘觉', '独觉',
            '心', '心所', '心法', '色法', '不相应行法',
            '俱舍', '顺正理', '毗婆沙', '阿毗达磨',

            # === 俱舍学专业术语（新增150个） ===
            # 随眠与烦恼
            '随眠', '缠', '使', '随烦恼', '根本烦恼', '枝末烦恼',
            '见惑', '思惑', '五钝使', '五利使', '十使', '九十八使',
            '身见', '边见', '邪见', '见取', '戒禁取',
            '大地法', '大善地法', '大烦恼地法', '大不善地法', '小烦恼地法',

            # 时间与相续
            '刹那', '相续', '前念', '后念', '俱时', '同时',
            '刹那灭', '念念生灭', '相续转变', '转变差别',

            # 因果业力
            '因果', '能依', '所依', '能生', '所生', '能引', '所引',
            '异熟', '异熟果', '等流果', '增上果', '离系果', '士用果',
            '业力', '业果', '业道', '业种', '业感', '业报',
            '定业', '不定业', '顺现受业', '顺生受业', '顺后受业',

            # 修道阶位
            '见道', '修道', '无学道', '有学', '无学',
            '预流果', '一来果', '不还果', '阿罗汉果',
            '预流向', '一来向', '不还向', '阿罗汉向',
            '须陀洹', '斯陀含', '阿那含',

            # 界地与禅定
            '欲界', '色界', '无色界', '三界',
            '初禅', '二禅', '三禅', '四禅', '四无色定',
            '静虑', '等至', '等持', '定心', '散心',
            '根本定', '未至定', '中间定', '近分定',

            # 法数分类
            '五取蕴', '五蕴', '十二处', '十八界', '二十二根',
            '六识', '六境', '六根', '六触', '六受', '六想', '六思', '六爱',
            '四大', '四大种', '造色', '极微', '微聚',

            # 心所法
            '大地法', '受', '想', '思', '触', '欲', '慧', '念', '作意', '胜解',
            '信', '精进', '轻安', '不放逸', '行舍', '不害',
            '寻', '伺', '恶作', '睡眠', '贪', '嗔', '慢', '无明', '疑', '恶见',

            # 有为无为
            '有为法', '无为法', '三无为', '虚空', '择灭', '非择灭',
            '生', '住', '异', '灭', '四相', '本有', '死有', '中有', '生有',

            # 谛理
            '苦谛', '集谛', '灭谛', '道谛', '四圣谛',
            '苦苦', '坏苦', '行苦', '八苦',

            # 缘起
            '十二因缘', '无明', '行', '识', '名色', '六入', '触', '受', '爱', '取', '有', '生', '老死',
            '缘起', '缘生', '此生故彼生', '此灭故彝灭',

            # === 顺正理论专用术语（新增100个） ===
            # 部派宗义
            '经部', '正量部', '大众部', '说一切有部', '萨婆多', '上座部',
            '毘婆沙师', '譬喻论师', '分别论者', '犊子部', '化地部',

            # 论师人名
            '世亲', '众贤', '法救', '觉天', '妙音', '世友',
            '大德', '尊者', '论主', '对法诸师',

            # 经部学说
            '种子说', '熏习', '功能差别', '相续转变',
            '种子', '熏成', '能熏', '所熏', '熏习力',
            '随界', '随眠', '随增', '随逐', '随系',

            # 论辩术语（新增50个）
            '反驳', '破斥', '对论', '问答', '问难', '释难',
            '颂曰', '论曰', '问曰', '答曰', '有说', '有余师说',
            '此说不然', '此义不成', '理必不然', '云何通释',
            '如何建立', '所以者何', '何以故', '云何', '如何',
            '应知', '应说', '应辩', '应思', '应观',
            '谓', '即', '所谓', '如是', '如前', '如后', '如说',
            '非', '非唯', '非但', '非谓', '非有', '非无',
            '或', '或有', '或说', '或言', '或复', '或时',
            '若', '若有', '若无', '若尔', '若谓',
            '云何', '何者', '何等', '何故', '何缘', '何以',

            # 有部特色术语
            '实有', '假有', '实法', '假法',
            '自相', '共相', '自性', '自体',
            '三世实有', '法体恒有',
            '得', '非得', '同分', '众同分',
            '无想定', '灭尽定', '命根', '众同分',

            # 文献相关
            '俱舍论', '顺正理论', '俱舍论记', '俱舍论疏',
            '大毘婆沙论', '阿毘达磨', '对法藏', '胜义', '世俗'
        }

        keywords = set()

        # 提取佛学术语
        for term in buddhist_terms:
            if term in query:
                keywords.add(term)

        # 提取引号内的关键词
        quoted = re.findall(r'[「」""](.+?)[」""]', query)
        keywords.update(quoted)

        # 如果没有提取到特定术语，将查询分词作为关键词
        if not keywords:
            # 简单分词：按标点和空格分割，过滤短词
            words = re.split(r'[，。？！、\s]+', query)
            keywords.update(w for w in words if len(w) >= 2)

        return keywords

    def _calculate_keyword_boost(self, content: str, keywords: Set[str]) -> float:
        """
        计算关键词匹配加权分数

        Args:
            content: 文档内容
            keywords: 关键词集合

        Returns:
            加权分数 (0-1)
        """
        if not keywords:
            return 0.5  # 无关键词时返回中性分数

        matched = 0
        total_weight = 0

        for keyword in keywords:
            weight = len(keyword)  # 长词权重更高
            total_weight += weight
            if keyword in content:
                # 计算关键词出现次数，最多计3次
                count = min(content.count(keyword), 3)
                matched += weight * (count / 3)

        if total_weight == 0:
            return 0.5

        return min(matched / total_weight, 1.0)
    
    def get_document_count(self) -> int:
        """获取文档总数"""
        return self.collection.count()
    
    def clear(self) -> None:
        """清空集合"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,  # 使用中文 embedding
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("向量存储已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        count = self.collection.count()
        
        # 统计各文献的文档数
        text_counts = {}
        for text_id in TEXT_METADATA.keys():
            result = self.collection.get(
                where={"text_id": text_id},
                limit=1
            )
            # ChromaDB不直接支持count with filter，这里用一个近似方法
            # 实际应用中可能需要在数据库中维护计数
            
        return {
            "total_documents": count,
            "collection_name": self.collection_name,
            "persist_dir": self.persist_dir
        }


class VectorStoreManager:
    """向量存储管理器（单例）"""
    
    _instance: Optional[VectorStore] = None
    
    @classmethod
    def get_instance(cls) -> VectorStore:
        """获取向量存储实例"""
        if cls._instance is None:
            cls._instance = VectorStore()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """重置实例"""
        cls._instance = None


def get_vector_store() -> VectorStore:
    """获取向量存储实例（用于依赖注入）"""
    return VectorStoreManager.get_instance()

