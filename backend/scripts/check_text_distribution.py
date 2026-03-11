"""
检查各文献的文档分布
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.services.vector_store import VectorStore
from app.config import get_settings, TEXT_METADATA


def main():
    """检查文档分布"""
    settings = get_settings()
    vector_store = VectorStore(settings.chroma_persist_dir)

    print("=" * 60)
    print("文档分布诊断")
    print("=" * 60)
    print()

    total = vector_store.get_document_count()
    print(f"总文档数: {total}")
    print()

    # 统计各文献的文档数量
    print("各文献文档分布:")
    print("-" * 60)

    for text_id, metadata in TEXT_METADATA.items():
        # 直接查询该文献的所有文档
        results = vector_store.collection.get(
            where={"text_id": text_id},
            limit=10000  # 足够大
        )

        count = len(results['ids']) if results and 'ids' in results else 0
        percentage = (count / total * 100) if total > 0 else 0

        print(f"{metadata['icon']} {metadata['short_title']:12s}: {count:5d} ({percentage:5.2f}%)")

    print()
    print("=" * 60)

    # 测试：直接搜索包含"有漏"的文档
    print()
    print("直接文本搜索测试（包含'有漏'的文档）:")
    print("-" * 60)

    # 使用ChromaDB的where_document功能
    results = vector_store.collection.get(
        where_document={"$contains": "有漏"},
        limit=5
    )

    if results and results['documents']:
        for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas']), 1):
            text_id = meta.get('text_id', 'unknown')
            volume = meta.get('volume', '?')
            text_meta = TEXT_METADATA.get(text_id, {})
            title = text_meta.get('short_title', text_id)

            print(f"\n【结果{i}】")
            print(f"来源: {title} 卷{volume}")
            print(f"内容: {doc[:100]}...")
    else:
        print("未找到包含'有漏'的文档")


if __name__ == "__main__":
    main()
