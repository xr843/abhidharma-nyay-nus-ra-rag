"""
数据库诊断脚本 - 检查向量数据库状态
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
    """数据库诊断"""
    settings = get_settings()

    print("=" * 60)
    print("向量数据库诊断报告")
    print("=" * 60)
    print()

    # 0. 显示当前配置
    print("📋 当前配置:")
    print(f"   chunk_size: {settings.chunk_size}")
    print(f"   chunk_overlap: {settings.chunk_overlap}")
    print(f"   max_chunk_size: {getattr(settings, 'max_chunk_size', '未设置')}")
    print(f"   retrieval_top_k: {settings.retrieval_top_k}")
    print(f"   retrieval_min_score: {settings.retrieval_min_score}")
    print()

    # 1. 检查数据库目录
    chroma_dir = Path(settings.chroma_persist_dir)
    print(f"📁 数据库目录: {chroma_dir.absolute()}")

    if not chroma_dir.exists():
        print("❌ 数据库目录不存在！")
        print()
        print("💡 解决方案:")
        print("   1. 运行数据导入脚本:")
        print("      cd backend")
        print("      python scripts/process_texts.py")
        return
    else:
        print("✅ 数据库目录存在")

    print()

    # 2. 初始化向量存储
    try:
        vector_store = VectorStore(settings.chroma_persist_dir)
        total_docs = vector_store.get_document_count()

        print(f"📊 总文档数: {total_docs}")

        if total_docs == 0:
            print("❌ 数据库为空！")
            print()
            print("💡 解决方案:")
            print("   运行数据导入脚本:")
            print("   python scripts/process_texts.py")
            return
        else:
            print(f"✅ 数据库包含 {total_docs} 个文档段落")

        # 检查实际 chunk 大小
        print()
        print("📏 实际文档长度采样（随机抽取5个）:")
        sample_results = vector_store.search("佛法", top_k=5)
        chunk_lengths = [len(r.content) for r in sample_results]
        if chunk_lengths:
            print(f"   样本长度: {chunk_lengths}")
            print(f"   平均长度: {sum(chunk_lengths) / len(chunk_lengths):.0f} 字符")
            print(f"   最小长度: {min(chunk_lengths)} 字符")
            print(f"   最大长度: {max(chunk_lengths)} 字符")
            print()
            if sum(chunk_lengths) / len(chunk_lengths) > 400:
                print("⚠️  警告：实际文档长度远大于配置的chunk_size，可能使用了旧数据！")
                print("   需要重新运行 process_texts.py 来重新处理文本")

    except Exception as e:
        print(f"❌ 初始化向量存储失败: {e}")
        return

    print()
    print("-" * 60)
    print()

    # 3. 测试检索功能
    print("🔍 测试检索功能...")
    print()

    test_question = "什么是有漏和无漏？"
    print(f"测试问题: {test_question}")
    print()

    try:
        results = vector_store.search(test_question, top_k=5)

        if not results:
            print("❌ 检索无结果！")
            print()
            print("💡 可能原因:")
            print("   1. 数据库数据不完整")
            print("   2. Embedding模型问题")
            print("   3. 检索参数设置过严")
        else:
            print(f"✅ 检索到 {len(results)} 个结果")
            print()

            for i, cite in enumerate(results, 1):
                print(f"【结果{i}】")
                print(f"  来源: 《{cite.short_title}》卷{cite.volume}")
                print(f"  相关度: {cite.relevance_score:.2%}")
                print(f"  内容: {cite.content[:60]}...")
                print()

            # 4. 分析检索质量
            print("-" * 60)
            print()
            print("📈 检索质量分析:")
            print()

            avg_score = sum(c.relevance_score for c in results) / len(results)
            max_score = max(c.relevance_score for c in results)
            min_score = min(c.relevance_score for c in results)

            print(f"  平均相关度: {avg_score:.2%}")
            print(f"  最高相关度: {max_score:.2%}")
            print(f"  最低相关度: {min_score:.2%}")
            print()

            # 5. 诊断建议
            print("-" * 60)
            print()
            print("💡 优化建议:")
            print()

            if max_score < 0.7:
                print("⚠️  最高相关度低于70%，建议:")
                print("   1. 检查分词策略是否合理")
                print(f"   2. 调整chunk_size (当前{settings.chunk_size})")
                print(f"   3. 增加chunk_overlap (当前{settings.chunk_overlap})")

            if min_score < 0.3:
                print("⚠️  最低相关度低于30%，建议:")
                print("   1. 提高 retrieval_min_score 阈值")
                print("   2. 减少 retrieval_top_k")

            if len(results) < 3:
                print("⚠️  检索结果过少，建议:")
                print("   1. 降低 retrieval_min_score")
                print("   2. 增加 retrieval_top_k")

            # 检查来源多样性
            sources = set(c.text_id for c in results)
            print()
            print(f"📚 来源多样性: {len(sources)}/4 部论典")
            for text_id in TEXT_METADATA.keys():
                if text_id in sources:
                    print(f"  ✅ {TEXT_METADATA[text_id]['short_title']}")
                else:
                    print(f"  ❌ {TEXT_METADATA[text_id]['short_title']} (未检索到)")

            if len(sources) < 2:
                print()
                print("⚠️  只从一部论典检索到结果，建议:")
                print("   1. 降低相关度阈值")
                print("   2. 增加检索数量")
                print("   3. 优化关键词提取")

    except Exception as e:
        print(f"❌ 检索测试失败: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
