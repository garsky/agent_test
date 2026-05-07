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
    from knowledge.converter import is_convertible, convert_to_markdown

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


def _cleanup_orphan_md(platform_docs_dir: Path) -> list[str]:
    from knowledge.converter import SUPPORTED_SOURCE_EXTENSIONS

    cleaned = []
    source_stems = set()
    for f in platform_docs_dir.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS:
            source_stems.add(f.stem)

    for md_file in list(platform_docs_dir.glob("*.md")):
        stem = md_file.stem
        if stem in source_stems:
            source_file = None
            for ext in SUPPORTED_SOURCE_EXTENSIONS:
                candidate = platform_docs_dir / (stem + ext)
                if candidate.exists():
                    source_file = candidate
                    break
            if source_file and source_file.exists():
                continue

        if _is_converted_md(md_file, source_stems):
            print(f"  清理孤立文件: {md_file.name} (源文件已删除)")
            try:
                md_file.unlink()
                cleaned.append(md_file.name)
            except Exception as e:
                print(f"  警告: 删除 {md_file.name} 失败: {e}")
    return cleaned


def _is_converted_md(md_file: Path, source_stems: set[str]) -> bool:
    stem = md_file.stem
    return stem in source_stems


def _scan_docs_dir(platform_docs_dir: Path) -> dict[str, str]:
    if not platform_docs_dir.exists():
        return {}
    current_files = {}
    for doc_file in list(platform_docs_dir.glob("*.md")) + list(platform_docs_dir.glob("*.txt")):
        current_files[doc_file.name] = _get_file_hash(doc_file)
    return current_files


def _update_single_kb(
    docs_dir: Path,
    vectorstore_dir: Path,
    collection_name: str,
) -> dict:
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma

    if not docs_dir.exists():
        return {"status": "skip", "message": f"目录不存在: {docs_dir}"}

    converted = _auto_convert_docs(docs_dir)
    if converted:
        print(f"  已自动转换 {len(converted)} 个文档为 Markdown")

    cleaned = _cleanup_orphan_md(docs_dir)
    if cleaned:
        print(f"  已清理 {len(cleaned)} 个孤立文件")

    manifest_path = vectorstore_dir / MANIFEST_FILENAME
    manifest = _load_manifest(manifest_path)
    current_files = _scan_docs_dir(docs_dir)

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
        fpath = docs_dir / fname
        try:
            loader = TextLoader(str(fpath), encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = fname
            documents.extend(docs)
        except Exception as e:
            print(f"  警告: 加载 {fname} 失败: {e}")

    embeddings = _get_embeddings()
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

    return {
        "status": "updated",
        "new": len(new_files),
        "changed": len(changed_files),
        "deleted": len(deleted_files),
    }


def update_knowledge_base(
    vendor_id: str,
    sub_platform_id: str,
) -> dict:
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
    total = {"status": "up_to_date", "new": 0, "changed": 0, "deleted": 0}

    global_docs = kb_dir / "common" / "platform_docs"
    global_vs = kb_dir / "common" / "vectorstore"
    print("  [全局通用知识库]")
    r = _update_single_kb(global_docs, global_vs, "global_common")
    if r["status"] == "updated":
        total["status"] = "updated"
        total["new"] += r["new"]
        total["changed"] += r["changed"]
        total["deleted"] += r["deleted"]
        print(f"  全局知识库更新: +{r['new']} 修改{r['changed']} -{r['deleted']}")

    vendor_docs = kb_dir / vendor_id / "common" / "platform_docs"
    vendor_vs = kb_dir / vendor_id / "common" / "vectorstore"
    print(f"  [{vendor_id} 厂商公共知识库]")
    r = _update_single_kb(vendor_docs, vendor_vs, f"{vendor_id}_common")
    if r["status"] == "updated":
        total["status"] = "updated"
        total["new"] += r["new"]
        total["changed"] += r["changed"]
        total["deleted"] += r["deleted"]
        print(f"  厂商知识库更新: +{r['new']} 修改{r['changed']} -{r['deleted']}")

    platform_docs = kb_dir / vendor_id / sub_platform_id / "platform_docs"
    platform_vs = kb_dir / vendor_id / sub_platform_id / "vectorstore"
    print(f"  [{vendor_id}/{sub_platform_id} 平台知识库]")
    r = _update_single_kb(platform_docs, platform_vs, f"{vendor_id}_{sub_platform_id}_platform")
    if r["status"] == "updated":
        total["status"] = "updated"
        total["new"] += r["new"]
        total["changed"] += r["changed"]
        total["deleted"] += r["deleted"]
        print(f"  平台知识库更新: +{r['new']} 修改{r['changed']} -{r['deleted']}")

    if total["status"] == "up_to_date":
        print("  所有知识库已是最新，无需更新")
    else:
        print(f"  知识库更新完成: +{total['new']} 修改{total['changed']} -{total['deleted']}")

    return total


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
    manifest_path = vectorstore_dir / MANIFEST_FILENAME

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

    current_files = _scan_docs_dir(platform_docs_dir)
    _save_manifest(manifest_path, current_files)

    print(f"知识库构建完成，向量存储在: {vectorstore_dir}")


def init_knowledge_dirs(vendor_id: str, sub_platform_id: str) -> None:
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)

    (kb_dir / "common" / "platform_docs").mkdir(parents=True, exist_ok=True)
    (kb_dir / "common" / "vectorstore").mkdir(parents=True, exist_ok=True)

    (kb_dir / vendor_id / "common" / "platform_docs").mkdir(parents=True, exist_ok=True)
    (kb_dir / vendor_id / "common" / "vectorstore").mkdir(parents=True, exist_ok=True)

    base_dir = kb_dir / vendor_id / sub_platform_id
    (base_dir / "platform_docs").mkdir(parents=True, exist_ok=True)
    (base_dir / "vectorstore").mkdir(parents=True, exist_ok=True)
    (base_dir / "projects").mkdir(parents=True, exist_ok=True)

    print(f"知识库目录已初始化: {kb_dir}")
    print(f"  全局通用: {kb_dir / 'common'}")
    print(f"  厂商公共: {kb_dir / vendor_id / 'common'}")
    print(f"  平台专属: {base_dir}")


def get_all_doc_dirs(vendor_id: str, sub_platform_id: str) -> list[Path]:
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
    dirs = []
    global_dir = kb_dir / "common" / "platform_docs"
    if global_dir.exists():
        dirs.append(global_dir)
    vendor_dir = kb_dir / vendor_id / "common" / "platform_docs"
    if vendor_dir.exists():
        dirs.append(vendor_dir)
    platform_dir = kb_dir / vendor_id / sub_platform_id / "platform_docs"
    if platform_dir.exists():
        dirs.append(platform_dir)
    return dirs


def get_all_vectorstore_dirs(vendor_id: str, sub_platform_id: str) -> list[tuple[Path, str]]:
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
    result = []
    global_vs = kb_dir / "common" / "vectorstore"
    if global_vs.exists():
        result.append((global_vs, "global_common"))
    vendor_vs = kb_dir / vendor_id / "common" / "vectorstore"
    if vendor_vs.exists():
        result.append((vendor_vs, f"{vendor_id}_common"))
    platform_vs = kb_dir / vendor_id / sub_platform_id / "vectorstore"
    if platform_vs.exists():
        result.append((platform_vs, f"{vendor_id}_{sub_platform_id}_platform"))
    return result


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
