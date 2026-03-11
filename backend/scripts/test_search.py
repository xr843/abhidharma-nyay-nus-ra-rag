"""
测试搜索功能
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
from app.config import get_settings


def main():
    """测试搜索"""
    settings = get_settings()
    vector_store = VectorStore(settings.chroma_persist_dir)
    
    print(f"向量存储中共有 {vector_store.get_document_count()} 个文档")
    print()
    
    # 测试问题
    test_questions = [
        "什么是有漏和无漏？",
        "顺正理论如何反驳经部的种子说？",
        "五蕴是什么？",
        "业力如何相续？"
    ]
    
    for question in test_questions:
        print(f"问题: {question}")
        print("-" * 50)
        
        results = vector_store.search(question, top_k=3)
        
        for i, cite in enumerate(results, 1):
            print(f"\n【结果{i}】相似度: {cite.relevance_score:.4f}")
            print(f"来源: {cite.icon} 《{cite.short_title or cite.text_title}》卷{cite.volume}")
            if cite.chapter:
                print(f"章节: {cite.chapter}")
            print(f"内容: {cite.content[:200]}...")
        
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()

