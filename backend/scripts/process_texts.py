"""
文本处理脚本 - 处理文献并导入向量数据库
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(project_root / ".env")

from app.services.text_processor import TextProcessor
from app.services.vector_store import VectorStore
from app.config import get_settings


def main():
    """主函数"""
    settings = get_settings()
    
    # 数据目录（论典文件所在目录）
    data_dir = project_root.parent
    
    logger.info(f"数据目录: {data_dir}")
    logger.info(f"向量存储目录: {settings.chroma_persist_dir}")
    
    # 初始化处理器和存储
    processor = TextProcessor(str(data_dir))
    vector_store = VectorStore(settings.chroma_persist_dir)
    
    # 询问是否清空现有数据
    current_count = vector_store.get_document_count()
    if current_count > 0:
        logger.warning(f"向量存储中已有 {current_count} 个文档")
        response = input("是否清空现有数据并重新处理？(y/N): ")
        if response.lower() == 'y':
            vector_store.clear()
            logger.info("已清空向量存储")
        else:
            logger.info("将追加到现有数据")
    
    # 处理文本
    logger.info("开始处理文献...")
    
    batch_size = 100
    batch_texts = []
    batch_metadatas = []
    batch_ids = []
    total_count = 0
    
    for segment in processor.process_all_texts():
        # 准备数据
        doc_id = f"{segment.text_id}_v{segment.volume}_{total_count}"
        
        metadata = {
            "text_id": segment.text_id,
            "text_title": segment.text_title,
            "volume": segment.volume,
            "chapter": segment.chapter or "",
            "section": segment.section or "",
            "char_start": segment.char_start,
            "char_end": segment.char_end
        }
        
        batch_texts.append(segment.content)
        batch_metadatas.append(metadata)
        batch_ids.append(doc_id)
        total_count += 1
        
        # 批量写入
        if len(batch_texts) >= batch_size:
            vector_store.add_texts(batch_texts, batch_metadatas, batch_ids)
            logger.info(f"已处理 {total_count} 个段落...")
            batch_texts = []
            batch_metadatas = []
            batch_ids = []
    
    # 处理剩余数据
    if batch_texts:
        vector_store.add_texts(batch_texts, batch_metadatas, batch_ids)
    
    logger.info(f"处理完成！总共处理 {total_count} 个段落")
    logger.info(f"向量存储中现有 {vector_store.get_document_count()} 个文档")


if __name__ == "__main__":
    main()

