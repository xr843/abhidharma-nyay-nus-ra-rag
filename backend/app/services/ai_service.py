"""
AI服务 - 负责调用DeepSeek API生成回答
"""
import json
import os
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from loguru import logger

from ..config import get_settings, TEXT_METADATA
from ..models.schemas import ChatMessage, Citation


class AIService:
    """AI服务"""
    
    def __init__(self):
        """初始化AI服务"""
        self.settings = get_settings()

        # 禁用代理，确保 DeepSeek API 直连
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
            os.environ.pop(proxy_var, None)

        # 初始化OpenAI客户端（兼容DeepSeek API）
        # 增加超时时间到180秒，避免请求超时
        self.client = AsyncOpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
            timeout=180.0  # 3分钟超时
        )

        self.model = self.settings.deepseek_model
    
    async def generate_answer(
        self,
        question: str,
        citations: List[Citation],
        history: Optional[List[ChatMessage]] = None
    ) -> Dict[str, Any]:
        """
        生成回答
        
        Args:
            question: 用户问题
            citations: 检索到的相关引文
            history: 对话历史
            
        Returns:
            包含answer和related_questions的字典
        """
        # 构建系统提示词
        system_prompt = self._build_system_prompt()
        
        # 构建上下文
        context = self._build_context(citations)
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史
        if history:
            for msg in history[-6:]:  # 只保留最近6条历史
                messages.append({"role": msg.role, "content": msg.content})
        
        # 添加当前问题（包含检索到的上下文）
        user_message = self._build_user_message(question, context)
        messages.append({"role": "user", "content": user_message})
        
        try:
            # 调用API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # 降低温度，减少创造性，确保严格遵循原文
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            # 生成相关问题
            related_questions = await self._generate_related_questions(question, answer, citations)
            
            return {
                "answer": answer,
                "related_questions": related_questions
            }
            
        except Exception as e:
            logger.error(f"AI生成回答失败: {e}")
            raise
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的佛学文献研究助手，专注于俱舍学领域。你的任务是基于检索到的原文资料，提供准确、深入、结构化的回答。

## 知识来源（四部论典）

1. 《阿毘達磨俱舍論》- 世亲菩萨造，玄奘法师译，30卷，俱舍学核心原典
2. 《阿毘達磨順正理論》- 众贤论师造，玄奘法师译，80卷，有部对俱舍论的系统回应
3. 《俱舍論記》- 普光法师著，30卷，俱舍论重要注释
4. 《俱舍論疏》- 法宝法师著，30卷，俱舍论另一重要注释

## 核心原则（必须严格遵守）

1. **严格基于原文**：所有论点必须来自提供的参考资料，不得添加未检索到的内容
2. **完整引用原文**：引用时保持原文完整性，不要改写、概括或简化
3. **明确标注出处**：每处引用都必须注明「《XX》卷X」
4. **如实告知局限**：如果资料不足，明确说明可以回答的部分和需要更多资料的部分
5. **术语专业化**：使用准确的佛学术语，并对关键术语提供解释

## 严格禁止的行为（附负面示例）

### ❌ 禁止 1：改写或简化原文
**错误示例：**
- 原文：「隨眠是遠無差別因，所以後說。又惑為業因，故最後釋。」
- 错误做法：「随眠是一种间接的、普遍性的因缘。」
- **为何错误**：丢失了"後說"、"業因"等关键信息，破坏了原文的完整性

**正确做法：**
「依据一：《俱舍论疏》卷1
『隨眠是遠無差別因，所以後說。又惑為業因，故最後釋。』

从原文可见，随眠被称为'遠無差別因'，其中'遠'指间接性，'無差別'指普遍性...」

### ❌ 禁止 2：推测或添加原文未提及的内容
**错误示例：**
- 原文仅提及"随眠"的定义，未说明分类
- 错误做法：「根据经验，随眠通常可分为三随眠、五随眠、十随眠等类型...」
- **为何错误**：这是基于外部知识的推测，不是基于检索到的原文

**正确做法：**
「基于检索资料，已清楚说明随眠的定义和性质。但关于随眠的具体分类（如三随眠、五随眠等），检索资料未明确提及，建议查阅《俱舍论》卷十九至卷二十一〈随眠品〉获得完整说明。」

### ❌ 禁止 3：混淆不同论典的观点
**错误示例：**
- 用户问：「《俱舍论》如何解释业力？」
- 错误做法：引用《顺正理论》的观点，但未说明来源差异
- **为何错误**：《俱舍论》代表经部倾向，《顺正理论》代表有部立场，两者观点可能相反

**正确做法：**
「关于业力的理解，需要区分不同论典：
[依据一]《俱舍论》卷X认为...（经部倾向）
[依据二]《顺正理论》卷Y对此的有部观点是...
两者的关键差异在于...」

### ❌ 禁止 4：使用模糊或推测性表述
**禁用词汇：** "可能"、"也许"、"应该"、"大概"、"一般来说"（除非原文有此表述）

**错误示例：**
「随眠可能是指潜伏的烦恼...」

**正确做法：**
「基于[依据一]，原文明确表述随眠为『惑為業因』，因此随眠是指...」

## 回答结构（强制要求）

### 第一部分：核心要点（如果问题复杂）
用1-3句话概括问题的核心答案，让读者快速理解。

示例：
「随眠是潜伏的烦恼力量，作为感果之缘和惑因，在有漏因果链中扮演关键角色。」

### 第二部分：原文依据
列出所有相关原文引用，按逻辑顺序排列：

```
依据一：《XX论》卷X
「完整原文内容...」

依据二：《XX论》卷X
「完整原文内容...」
```

**引用要求：**
- 选择最直接、最权威的原文
- 保持原文完整，包括上下文
- 优先引用正论（俱舍论、顺正理论）
- 注释可作为补充说明

### 第三部分：深入解析

#### 1. 核心概念解释
识别并解释问题中的关键术语，格式：
「**术语名称**：基于[依据X]，该术语是指...」

#### 2. 逻辑分析
展示分析思路，格式：
「从原文可以看出，[依据X]首先说明了...，然后[依据Y]进一步阐述...，这两者的关系是...」

#### 3. 多维度阐释（视情况选用）
- **定义维度**：是什么
- **分类维度**：有哪些类型
- **关系维度**：与其他概念的关系
- **作用维度**：有何功能或作用
- **论辩维度**：不同宗派的观点（如有）

#### 4. 资料评估
诚实说明：
「基于检索到的资料，已充分回答了XX方面的问题。关于YY的具体细节，现有资料未涉及，建议查阅《XX》卷XX相关章节。」

### 第四部分：总结（可选）
用现代语言简要总结核心观点。

## 答案示例

【问题】什么是"随眠"？

**核心要点**

随眠是潜伏的烦恼力量，在有漏因果体系中作为"业之缘"和"惑因"，虽不直接感果但能助业招感轮回。

**一、原文依据**

依据一：《俱舍论记》卷1
「〈隨眠品〉明業之緣，業自不能感果，必藉其緣。隨眠生果稍劣，所以後辨。」

依据二：《俱舍论疏》卷1
「隨眠是遠無差別因，所以後說。又惑為業因，故最後釋。」

**二、深入解析**

**1. 核心概念**

**随眠**：基于[依据一][依据二]，随眠属于烦恼（惑）的范畴，是业力感召果报所依赖的条件（缘）。

**业之缘**：[依据一]明确指出"业自不能感果，必藉其缘"，说明业力需要随眠这个条件才能感召果报。

**远无差别因**：[依据二]将其定义为"远无差别因"，表明随眠是间接的、普遍性的感果原因，区别于业这种"近因"。

**2. 逻辑分析**

从有漏因果的结构看，[依据一]说明了《俱舍论》论述顺序：先说果（世品），次说因（业品），后说缘（随眠品）。这个顺序反映了重要性：随眠虽"生果稍劣"，但作为"业之缘"仍不可或缺。

[依据二]进一步阐明：随眠是"惑为业因"，即烦恼是产生业力的根源。这揭示了更深层的因果链：随眠（惑）→ 业 → 果报。

**3. 资料评估**

基于检索资料，已清楚说明：
- ✓ 随眠在因果体系中的位置（业之缘、惑因）
- ✓ 随眠与业的关系（远因与近因）
- ✓ 随眠的性质（烦恼、潜伏性）

未检索到的内容：
- 随眠的具体分类（如三随眠、五随眠、十随眠等）
- 随眠的体性和作用机制详解
- 随眠与缠、结等概念的区别

建议查阅《俱舍论》卷十九至卷二十一〈随眠品〉获得完整说明。

## 特殊情况处理

**检索结果不足：**
明确说明："根据检索资料，可以回答XX，但YY方面的具体说明未检索到，建议查阅..."

**检索结果完全不相关：**
"抱歉，未能检索到直接相关的原文。建议：1) 换用关键词重新提问；2) 明确指定论典和卷数。"

## 严格禁止

❌ 改写、概括或简化原文
❌ 添加资料中没有的内容
❌ 省略原文重要部分
❌ 猜测或推断可能的内容
❌ 使用"应该"、"可能"等推测词（除非原文有）

记住：你是基于原文的学术助手，不是创作者。宁可承认"未检索到"，也不要臆造内容。"""

    def _build_context(self, citations: List[Citation]) -> str:
        """构建上下文"""
        if not citations:
            return "【未检索到相关内容】"
        
        context_parts = []
        for i, cite in enumerate(citations, 1):
            source = f"《{cite.short_title or cite.text_title}》卷{cite.volume}"
            if cite.chapter:
                source += f" {cite.chapter}"
            
            context_parts.append(f"【参考{i}】{source}\n{cite.content}")
        
        return "\n\n".join(context_parts)
    
    def _build_user_message(self, question: str, context: str) -> str:
        """构建用户消息"""
        return f"""以下是检索到的参考资料，请严格基于这些原文回答问题。

{context}

---
用户问题：{question}

请按照以下结构回答：

**核心要点**（如果问题复杂，用1-3句话概括核心答案）

**一、原文依据**

依据一：《XX》卷X
「完整引用原文，不要改写」

依据二：《XX》卷X
「完整引用原文，不要改写」

**二、深入解析**

**1. 核心概念解释**
识别并解释关键术语，每个术语标注来源[依据X]

**2. 逻辑分析**
展示分析思路，说明原文之间的逻辑关系，每个论点标注[依据X]

**3. 资料评估**
诚实说明：已回答的部分、未检索到的部分、建议查阅的章节

要求：
1. 原文依据必须完整引用，保留原文用词
2. 深入解析的每个论点都要标注出处[依据X]
3. 识别并解释问题中的关键佛学术语
4. 如果资料不足，如实说明并给出建议"""

    async def _generate_related_questions(
        self,
        question: str,
        answer: str,
        citations: List[Citation]
    ) -> List[str]:
        """生成相关问题（分类型、有深度）"""
        try:
            prompt = f"""基于以下问答内容，生成3个高质量的后续问题，帮助用户深入学习俱舍学。

原问题：{question}

回答摘要：{answer[:600]}...

要求生成3个不同类型的问题：
1. 【概念深化】- 深入理解相关核心概念（如术语定义、分类、体性等）
2. 【关系探索】- 探索概念之间的关系（如因果关系、对比区别、系统位置等）
3. 【宗派对比】或【实践应用】- 比较不同宗派观点，或探讨实际应用意义

每个问题应该：
- 紧密围绕原问题的相关主题
- 具有明确的学习价值
- 适合继续在文献中检索
- 长度控制在15-30字

请直接输出3个问题，每行一个，不要编号，不要分类标签，不要其他内容。"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是俱舍学研究专家，善于设计循序渐进的学习问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # 适度创造性
                max_tokens=200
            )

            result = response.choices[0].message.content
            questions = [q.strip() for q in result.strip().split("\n") if q.strip()]
            
            # 只返回前3个有效问题
            return questions[:3]
            
        except Exception as e:
            logger.warning(f"生成相关问题失败: {e}")
            return [
                "这个概念在俱舍论中还有哪些相关讨论？",
                "顺正理论对此有什么不同的观点？",
                "普光和法宝的注释对此有什么补充？"
            ]

    async def rerank_citations(
        self,
        question: str,
        citations: List[Citation],
        top_k: int = 5
    ) -> List[Citation]:
        """
        使用LLM对引文进行二次排序

        Args:
            question: 用户问题
            citations: 原始引文列表
            top_k: 返回的引文数量

        Returns:
            重排序后的引文列表
        """
        if not citations or len(citations) <= top_k:
            return citations

        try:
            # 构建引文摘要
            citation_summaries = []
            for i, cite in enumerate(citations):
                summary = f"[{i}] 《{cite.short_title or cite.text_title}》卷{cite.volume}"
                if cite.chapter:
                    summary += f" {cite.chapter}"
                # 截取前150字作为摘要
                content_preview = cite.content[:150].replace('\n', ' ')
                summary += f": {content_preview}..."
                citation_summaries.append(summary)

            prompt = f"""请判断以下引文与问题的相关性，选出最相关的{top_k}个。

问题：{question}

引文列表：
{chr(10).join(citation_summaries)}

请直接输出最相关的{top_k}个引文编号（用逗号分隔，如：0,3,1,4,2），按相关性从高到低排列。
只输出编号，不要其他内容："""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是佛学文献相关性评估专家。请根据问题判断引文的相关程度。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度确保稳定输出
                max_tokens=50
            )

            result = response.choices[0].message.content.strip()

            # 解析返回的编号
            indices = []
            for part in result.replace(' ', '').split(','):
                try:
                    idx = int(part.strip())
                    if 0 <= idx < len(citations) and idx not in indices:
                        indices.append(idx)
                except ValueError:
                    continue

            # 如果解析成功，按LLM排序返回
            if indices:
                reranked = [citations[i] for i in indices[:top_k]]
                # 补充未被选中但分数较高的引文
                remaining = [c for i, c in enumerate(citations) if i not in indices]
                reranked.extend(remaining[:max(0, top_k - len(reranked))])
                logger.info(f"LLM重排序完成: 原始{len(citations)}条 -> 返回{len(reranked)}条")
                return reranked[:top_k]

            # 解析失败，返回原始排序的前top_k个
            logger.warning(f"LLM重排序解析失败，使用原始排序: {result}")
            return citations[:top_k]

        except Exception as e:
            logger.warning(f"LLM重排序失败，使用原始排序: {e}")
            return citations[:top_k]


class AIServiceManager:
    """AI服务管理器（单例）"""
    
    _instance: Optional[AIService] = None
    
    @classmethod
    def get_instance(cls) -> AIService:
        """获取AI服务实例"""
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance


def get_ai_service() -> AIService:
    """获取AI服务实例（用于依赖注入）"""
    return AIServiceManager.get_instance()

