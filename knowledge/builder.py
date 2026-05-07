from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from config.settings import settings
from config.llm_config import LLMFactory, EmbeddingConfig

MANIFEST_FILENAME = ".kb_manifest.json"


def _get_file_hash(filepath: Path) -> str:
    h = hashlib.md5()
    with filepath.open("rb") as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        return {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(manifest_path: Path, manifest: dict) -> None:
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _get_embeddings():
    embedding_config = EmbeddingConfig.from_settings()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    try:
        embeddings = LLMFactory.create_embeddings(embedding_config)
        test_result = embeddings.embed_query("test")
        if not test_result:
            raise ValueError("Embedding API returned empty result")
        print(f"  使用 {embedding_config.provider} Embedding")
        return embeddings
    except Exception as e:
        print(f"  外部 Embedding 不可用 ({e})，切换到本地 Embedding")
        from langchain_community.embeddings import FakeEmbeddings
        return FakeEmbeddings(size=768)


def _auto_convert_docs(platform_docs_dir: Path) -> list[str]:
    from knowledge.converter import is_convertible, is_direct, convert_to_markdown

    converted = []
    all_files = [f for f in platform_docs_dir.iterdir() if f.is_file()]

    for f in all_files:
        if is_convertible(f):
            md_name = f.stem + ".md"
            md_path = platform_docs_dir / md_name
            need_convert = False
            if not md_path.exists():
                need_convert = True
            elif md_path.stat().st_mtime < f.stat().st_mtime:
                need_convert = True

            if need_convert:
                print(f"  自动转换: {f.name} -> {md_name}")
                try:
                    md_content, _ = convert_to_markdown(f)
                    if md_content and md_content.strip():
                        md_path.write_text(md_content, encoding="utf-8")
                        converted.append(f.name)
                    else:
                        print(f"  警告: {f.name} 转换结果为空，跳过")
                except Exception as e:
                    print(f"  转换失败: {f.name}: {e}")
    return converted


def update_knowledge_base(
    vendor_id: str,
    sub_platform_id: str,
) -> dict:
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma

    base_dir = Path(settings.KNOWLEDGE_BASE_DIR) / vendor_id / sub_platform_id
    platform_docs_dir = base_dir / "platform_docs"
    vectorstore_dir = base_dir / "vectorstore"
    manifest_path = base_dir / MANIFEST_FILENAME

    if not platform_docs_dir.exists():
        return {"status": "error", "message": f"文档目录不存在: {platform_docs_dir}"}

    converted = _auto_convert_docs(platform_docs_dir)
    if converted:
        print(f"  已自动转换 {len(converted)} 个文档为 Markdown")

    manifest = _load_manifest(manifest_path)
    current_files: dict[str, str] = {}

    for doc_file in list(platform_docs_dir.glob("*.md")) + list(platform_docs_dir.glob("*.txt")):
        file_hash = _get_file_hash(doc_file)
        current_files[doc_file.name] = file_hash

    new_files = []
    changed_files = []
    deleted_files = []

    for name, hash_val in current_files.items():
        if name not in manifest:
            new_files.append(name)
        elif manifest[name] != hash_val:
            changed_files.append(name)

    for name in manifest:
        if name not in current_files:
            deleted_files.append(name)

    total_changes = len(new_files) + len(changed_files) + len(deleted_files)

    if total_changes == 0:
        print("  知识库已是最新，无需更新")
        return {"status": "up_to_date", "new": 0, "changed": 0, "deleted": 0}

    print(f"  检测到变更:")
    if new_files:
        print(f"    新增: {', '.join(new_files)}")
    if changed_files:
        print(f"    修改: {', '.join(changed_files)}")
    if deleted_files:
        print(f"    删除: {', '.join(deleted_files)}")

    print("  正在增量更新索引...")

    files_to_index = new_files + changed_files
    documents = []
    for fname in files_to_index:
        fpath = platform_docs_dir / fname
        try:
            loader = TextLoader(str(fpath), encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = fname
            documents.extend(docs)
        except Exception as e:
            print(f"  警告: 加载 {fname} 失败: {e}")

    embeddings = _get_embeddings()
    collection_name = f"{vendor_id}_{sub_platform_id}_platform"
    vectorstore_dir.mkdir(parents=True, exist_ok=True)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    if deleted_files:
        try:
            db = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(vectorstore_dir),
            )
            for fname in deleted_files:
                try:
                    db._collection.delete(where={"source": fname})
                    print(f"    已删除索引: {fname}")
                except Exception:
                    pass
        except Exception as e:
            print(f"  警告: 删除旧索引失败: {e}")

    if documents:
        splits = text_splitter.split_documents(documents)
        if deleted_files or changed_files:
            db = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(vectorstore_dir),
            )
            for fname in changed_files:
                try:
                    db._collection.delete(where={"source": fname})
                except Exception:
                    pass
            db.add_documents(splits)
            print(f"    已更新 {len(splits)} 个文本块")
        else:
            Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                collection_name=collection_name,
                persist_directory=str(vectorstore_dir),
            )
            print(f"    已添加 {len(splits)} 个文本块")

    new_manifest = dict(current_files)
    _save_manifest(manifest_path, new_manifest)

    result = {
        "status": "updated",
        "new": len(new_files),
        "changed": len(changed_files),
        "deleted": len(deleted_files),
    }
    print(f"  知识库更新完成: +{len(new_files)} 修改{len(changed_files)} -{len(deleted_files)}")
    return result


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
    manifest_path = base_dir / MANIFEST_FILENAME

    if not platform_docs_dir.exists():
        print(f"文档目录不存在: {platform_docs_dir}")
        print("请先创建目录并放入文档文件")
        return

    converted = _auto_convert_docs(platform_docs_dir)
    if converted:
        print(f"已自动转换 {len(converted)} 个文档为 Markdown")

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

    embeddings = _get_embeddings()

    collection_name = f"{vendor_id}_{sub_platform_id}_platform"

    from langchain_chroma import Chroma

    vectorstore_dir.mkdir(parents=True, exist_ok=True)
    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(vectorstore_dir),
    )

    current_files = {}
    for doc_file in list(platform_docs_dir.glob("*.md")) + list(platform_docs_dir.glob("*.txt")):
        current_files[doc_file.name] = _get_file_hash(doc_file)
    _save_manifest(manifest_path, current_files)

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
        print("用法: python -m knowledge.builder <vendor_id> <sub_platform_id> [--init|--build|--update]")
        print("示例: python -m knowledge.builder mtk mt6985 --init")
        print("      python -m knowledge.builder mtk mt6985 --build")
        print("      python -m knowledge.builder mtk mt6985 --update")
        sys.exit(1)

    vendor = sys.argv[1]
    sub_platform = sys.argv[2]
    action = sys.argv[3] if len(sys.argv) > 3 else "--init"

    if action == "--init":
        init_knowledge_dirs(vendor, sub_platform)
    elif action == "--build":
        build_knowledge_base(vendor, sub_platform)
    elif action == "--update":
        update_knowledge_base(vendor, sub_platform)
    else:
        print(f"未知操作: {action}")
