from __future__ import annotations

from pathlib import Path
from typing import Optional

from config.settings import settings
from config.llm_config import LLMFactory, EmbeddingConfig


def build_knowledge_base(
    vendor_id: str,
    sub_platform_id: str,
    docs_dir: Optional[str] = None,
) -> None:
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    base_dir = Path(settings.KNOWLEDGE_BASE_DIR) / vendor_id / sub_platform_id
    platform_docs_dir = Path(docs_dir) if docs_dir else base_dir / "platform_docs"
    vectorstore_dir = base_dir / "vectorstore"

    if not platform_docs_dir.exists():
        print(f"文档目录不存在: {platform_docs_dir}")
        print("请先创建目录并放入文档文件")
        return

    print(f"构建知识库: {vendor_id}/{sub_platform_id}")
    print(f"文档目录: {platform_docs_dir}")
    print(f"向量库目录: {vectorstore_dir}")

    loader = DirectoryLoader(
        str(platform_docs_dir),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()
    print(f"加载了 {len(documents)} 个文档")

    if not documents:
        print("没有文档可处理，退出")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    splits = text_splitter.split_documents(documents)
    print(f"分割为 {len(splits)} 个文本块")

    embedding_config = EmbeddingConfig.from_settings()
    try:
        embeddings = LLMFactory.create_embeddings(embedding_config)
        test_result = embeddings.embed_query("test")
        if not test_result:
            raise ValueError("Embedding API returned empty result")
        print(f"使用 {embedding_config.provider} Embedding")
    except Exception as e:
        print(f"外部 Embedding 不可用 ({e})，切换到本地 Embedding")
        from langchain_community.embeddings import FakeEmbeddings
        embeddings = FakeEmbeddings(size=768)

    collection_name = f"{vendor_id}_{sub_platform_id}_platform"

    from langchain_chroma import Chroma

    vectorstore_dir.mkdir(parents=True, exist_ok=True)
    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(vectorstore_dir),
    )
    print(f"知识库构建完成，向量存储在: {vectorstore_dir}")


def init_knowledge_dirs(vendor_id: str, sub_platform_id: str) -> None:
    base_dir = Path(settings.KNOWLEDGE_BASE_DIR) / vendor_id / sub_platform_id
    (base_dir / "platform_docs").mkdir(parents=True, exist_ok=True)
    (base_dir / "vectorstore").mkdir(parents=True, exist_ok=True)
    (base_dir / "projects").mkdir(parents=True, exist_ok=True)
    print(f"知识库目录已初始化: {base_dir}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python -m knowledge.builder <vendor_id> <sub_platform_id> [--init|--build]")
        print("示例: python -m knowledge.builder mtk mt6985 --init")
        print("      python -m knowledge.builder mtk mt6985 --build")
        sys.exit(1)

    vendor = sys.argv[1]
    sub_platform = sys.argv[2]
    action = sys.argv[3] if len(sys.argv) > 3 else "--init"

    if action == "--init":
        init_knowledge_dirs(vendor, sub_platform)
    elif action == "--build":
        build_knowledge_base(vendor, sub_platform)
    else:
        print(f"未知操作: {action}")
