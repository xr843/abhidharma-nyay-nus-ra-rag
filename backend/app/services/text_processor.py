"""
文本处理服务 - 负责文献清洗、解析和分段
"""
import os
import re
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
from loguru import logger

from ..config import TEXT_METADATA, TEXT_DIRS, get_settings


@dataclass
class TextSegment:
    """文本段落"""
    text_id: str
    text_title: str
    volume: int
    chapter: Optional[str]
    section: Optional[str]
    content: str
    char_start: int
    char_end: int


class TextProcessor:
    """文本处理器"""
    
    def __init__(self, data_dir: str):
        """
        初始化文本处理器
        
        Args:
            data_dir: 数据目录路径（包含四部论典文件夹的目录）
        """
        self.data_dir = Path(data_dir)
        self.settings = get_settings()
        
    def process_all_texts(self) -> Generator[TextSegment, None, None]:
        """
        处理所有文献
        
        Yields:
            TextSegment: 文本段落
        """
        for text_id, dir_name in TEXT_DIRS.items():
            text_dir = self.data_dir / dir_name
            if text_dir.exists():
                logger.info(f"处理文献: {text_id} - {TEXT_METADATA[text_id]['title']}")
                yield from self.process_text(text_id, text_dir)
            else:
                logger.warning(f"文献目录不存在: {text_dir}")
    
    def process_text(self, text_id: str, text_dir: Path) -> Generator[TextSegment, None, None]:
        """
        处理单部文献
        
        Args:
            text_id: CBETA编号
            text_dir: 文献目录路径
            
        Yields:
            TextSegment: 文本段落
        """
        metadata = TEXT_METADATA.get(text_id, {})
        text_title = metadata.get("title", text_id)
        volumes = metadata.get("volumes", 0)
        
        # 加载目录结构
        toc = self._load_toc(text_dir, text_id)
        
        # 处理每一卷
        for vol in range(1, volumes + 1):
            vol_file = text_dir / f"{text_id}_{vol:03d}.txt"
            if vol_file.exists():
                yield from self._process_volume(
                    text_id=text_id,
                    text_title=text_title,
                    volume=vol,
                    file_path=vol_file,
                    toc=toc
                )
            else:
                logger.warning(f"卷文件不存在: {vol_file}")
    
    def _load_toc(self, text_dir: Path, text_id: str) -> Dict:
        """加载目录结构"""
        toc_file = text_dir / f"{text_id}-toc.txt"
        toc = {"chapters": []}
        
        if toc_file.exists():
            try:
                with open(toc_file, "r", encoding="utf-8") as f:
                    current_chapter = None
                    for line in f:
                        line = line.rstrip()
                        if not line:
                            continue
                        
                        # 解析目录结构
                        if not line.startswith("  "):
                            # 品名
                            parts = line.split(" ", 1)
                            if len(parts) >= 2:
                                current_chapter = {
                                    "num": parts[0],
                                    "name": parts[1],
                                    "sections": []
                                }
                                toc["chapters"].append(current_chapter)
                        else:
                            # 节名
                            if current_chapter:
                                parts = line.strip().split(" ", 1)
                                if len(parts) >= 2:
                                    current_chapter["sections"].append({
                                        "num": parts[0],
                                        "name": parts[1]
                                    })
            except Exception as e:
                logger.error(f"加载目录失败: {toc_file}, 错误: {e}")
        
        return toc
    
    def _process_volume(
        self,
        text_id: str,
        text_title: str,
        volume: int,
        file_path: Path,
        toc: Dict
    ) -> Generator[TextSegment, None, None]:
        """
        处理单卷文献
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 清洗文本
            cleaned_content, chapter_info = self._clean_and_parse(content, text_id, volume)
            
            # 分段
            yield from self._segment_text(
                text_id=text_id,
                text_title=text_title,
                volume=volume,
                content=cleaned_content,
                chapter_info=chapter_info
            )
            
        except Exception as e:
            logger.error(f"处理卷文件失败: {file_path}, 错误: {e}")
    
    def _clean_and_parse(self, content: str, text_id: str, volume: int) -> tuple:
        """
        清洗文本并提取结构信息
        
        Returns:
            (cleaned_content, chapter_info)
        """
        lines = content.split("\n")
        cleaned_lines = []
        chapter_info = {
            "current_chapter": None,
            "chapters": []
        }
        
        in_header = True
        
        for line in lines:
            line = line.strip()
            
            # 跳过头部注释
            if in_header:
                if line.startswith("#"):
                    continue
                elif line == "" or line.startswith("No."):
                    continue
                elif "卷第" in line or f"卷{self._num_to_chinese(volume)}" in line:
                    in_header = False
                    continue
                elif line and not line.startswith("#"):
                    in_header = False
            
            # 跳过作者/译者行
            if "造" in line and len(line) < 20:
                continue
            if "譯" in line and len(line) < 30:
                continue
            if "奉　詔" in line:
                continue
                
            # 检测品名
            chapter_match = re.match(r'^([一二三四五六七八九十]+品|辯\w+品第[一二三四五六七八九十]+(?:之[一二三四五六七八九十]+)?)', line)
            if chapter_match or (line.endswith("品") and len(line) < 20):
                chapter_info["current_chapter"] = line
                chapter_info["chapters"].append({
                    "name": line,
                    "start": len("\n".join(cleaned_lines))
                })
            
            # 跳过空行
            if not line:
                continue
                
            # 跳过尾部
            if line.startswith("說一切有部") or line.startswith("阿毘達磨"):
                if "卷第" in line:
                    continue
            
            cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines), chapter_info
    
    def _segment_text(
        self,
        text_id: str,
        text_title: str,
        volume: int,
        content: str,
        chapter_info: Dict
    ) -> Generator[TextSegment, None, None]:
        """
        将文本分段 - 优化为按句子粒度分块

        策略：
        1. 优先在"论曰"、"頌曰"等标志处分段
        2. 每段内按句号、问号、感叹号等标点分句
        3. 合并过短的句子（确保语义完整）
        4. 分割过长的句子（避免超过max_chunk_size）
        5. 保留适当的上下文重叠
        """
        chunk_size = self.settings.chunk_size  # 目标200字符
        chunk_overlap = self.settings.chunk_overlap  # 重叠50字符
        max_chunk_size = getattr(self.settings, 'max_chunk_size', 400)  # 最大400字符

        # 分段标志
        segment_markers = ["論曰", "论曰", "頌曰", "颂曰", "問曰", "问曰", "答曰"]

        current_chapter = None
        for ch in chapter_info.get("chapters", []):
            if ch["start"] <= 0:
                current_chapter = ch["name"]
                break

        # 预处理：在标志处插入分隔符
        processed_content = content
        for marker in segment_markers:
            processed_content = processed_content.replace(marker, f"\n【SPLIT】{marker}")

        # 按分隔符初步分段
        raw_segments = processed_content.split("【SPLIT】")

        char_position = 0

        for raw_seg in raw_segments:
            raw_seg = raw_seg.strip()
            if not raw_seg:
                continue

            # 更新当前品名
            for ch in chapter_info.get("chapters", []):
                if ch["start"] <= char_position:
                    current_chapter = ch["name"]

            # 按句子分割每个段落
            sentences = self._split_by_sentences(raw_seg)

            # 合并句子形成chunk
            current_chunk = []
            current_length = 0

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                sentence_len = len(sentence)

                # 如果当前chunk加上这个句子会超过目标大小
                # 重要：只有当chunk已经达到最小长度(100字符)时才分割
                min_chunk_length = 100
                if current_length + sentence_len > chunk_size and current_chunk and current_length >= min_chunk_length:
                    # 输出当前chunk
                    chunk_text = "".join(current_chunk)
                    if len(chunk_text) >= min_chunk_length:  # 确保chunk足够长
                        yield TextSegment(
                            text_id=text_id,
                            text_title=text_title,
                            volume=volume,
                            chapter=current_chapter,
                            section=None,
                            content=chunk_text,
                            char_start=char_position,
                            char_end=char_position + len(chunk_text)
                        )
                        char_position += len(chunk_text)

                    # 开始新chunk，保留overlap
                    # overlap策略：保留上一个chunk的最后一个句子作为上下文
                    if current_chunk:
                        overlap_text = current_chunk[-1] if len(current_chunk[-1]) <= chunk_overlap else ""
                        current_chunk = [overlap_text] if overlap_text else []
                        current_length = len(overlap_text)
                    else:
                        current_chunk = []
                        current_length = 0

                # 如果单个句子就超过max_chunk_size，需要进一步分割
                if sentence_len > max_chunk_size:
                    # 输出之前积累的chunk
                    if current_chunk:
                        chunk_text = "".join(current_chunk)
                        min_chunk_length = 100
                        if len(chunk_text) >= min_chunk_length:
                            yield TextSegment(
                                text_id=text_id,
                                text_title=text_title,
                                volume=volume,
                                chapter=current_chapter,
                                section=None,
                                content=chunk_text,
                                char_start=char_position,
                                char_end=char_position + len(chunk_text)
                            )
                            char_position += len(chunk_text)
                        current_chunk = []
                        current_length = 0

                    # 硬分割长句
                    sub_chunks = self._split_long_segment(sentence, chunk_size, chunk_overlap)
                    min_chunk_length = 100
                    for sub_chunk in sub_chunks:
                        if len(sub_chunk) >= min_chunk_length:
                            yield TextSegment(
                                text_id=text_id,
                                text_title=text_title,
                                volume=volume,
                                chapter=current_chapter,
                                section=None,
                                content=sub_chunk,
                                char_start=char_position,
                                char_end=char_position + len(sub_chunk)
                            )
                            char_position += len(sub_chunk)
                else:
                    # 添加句子到当前chunk
                    current_chunk.append(sentence)
                    current_length += sentence_len

            # 输出最后的chunk
            if current_chunk:
                chunk_text = "".join(current_chunk)
                min_chunk_length = 100
                if len(chunk_text) >= min_chunk_length:
                    yield TextSegment(
                        text_id=text_id,
                        text_title=text_title,
                        volume=volume,
                        chapter=current_chapter,
                        section=None,
                        content=chunk_text,
                        char_start=char_position,
                        char_end=char_position + len(chunk_text)
                    )
                    char_position += len(chunk_text)

    def _split_by_sentences(self, text: str) -> List[str]:
        """
        按句子分割文本

        识别的句子结束标志：。！？；
        """
        sentence_ends = ["。", "！", "？", "；"]

        sentences = []
        current_sentence = []

        for char in text:
            current_sentence.append(char)
            if char in sentence_ends:
                sentences.append("".join(current_sentence))
                current_sentence = []

        # 添加剩余内容
        if current_sentence:
            sentences.append("".join(current_sentence))

        return sentences
    
    def _split_long_segment(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        分割过长的段落
        """
        segments = []
        
        # 句子结束符
        sentence_ends = ["。", "！", "？", "；"]
        
        start = 0
        while start < len(text):
            end = start + chunk_size
            
            if end >= len(text):
                segments.append(text[start:])
                break
            
            # 在句子结束处分割
            best_end = end
            for i in range(end, max(start + chunk_size // 2, start), -1):
                if text[i-1] in sentence_ends:
                    best_end = i
                    break
            
            segments.append(text[start:best_end])
            start = best_end - overlap if best_end - overlap > start else best_end
        
        return segments
    
    @staticmethod
    def _num_to_chinese(num: int) -> str:
        """数字转中文"""
        chinese_nums = "零一二三四五六七八九十"
        if num <= 10:
            return chinese_nums[num]
        elif num < 20:
            return f"十{chinese_nums[num - 10]}" if num > 10 else "十"
        elif num < 100:
            tens = num // 10
            ones = num % 10
            return f"{chinese_nums[tens]}十{chinese_nums[ones] if ones else ''}"
        else:
            return str(num)


def test_processor():
    """测试文本处理器"""
    import sys
    
    # 获取项目根目录
    project_dir = Path(__file__).parent.parent.parent.parent
    
    processor = TextProcessor(str(project_dir))
    
    count = 0
    for segment in processor.process_all_texts():
        count += 1
        if count <= 5:
            print(f"\n--- 段落 {count} ---")
            print(f"文献: {segment.text_title} 卷{segment.volume}")
            print(f"品名: {segment.chapter}")
            print(f"内容: {segment.content[:100]}...")
        
    print(f"\n总共处理 {count} 个段落")


if __name__ == "__main__":
    test_processor()

