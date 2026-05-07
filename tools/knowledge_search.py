from __future__ import annotations

from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field


class KnowledgeSearchInput(BaseModel):
    query: str = Field(description="搜索查询内容")


class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = "检索当前平台知识库中的Camera驱动相关文档（含全局通用、厂商公共、平台专属三层）"
    args_schema: Type[BaseModel] = KnowledgeSearchInput

    platform_context: object = None
    _retriever = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str) -> str:
        results = self._multi_level_search(query)
        if results:
            return results
        return self._fallback_search(query)

    def _multi_level_search(self, query: str) -> str:
        from knowledge.builder import get_all_vectorstore_dirs
        from config.llm_config import LLMFactory, EmbeddingConfig

        if self.platform_context is None:
            return ""

        try:
            embedding_config = EmbeddingConfig.from_settings()
            embeddings = LLMFactory.create_embeddings(embedding_config)
        except Exception:
            return ""

        vendor_id = self.platform_context.vendor.id
        sub_platform_id = self.platform_context.sub_platform.id
        vs_dirs = get_all_vectorstore_dirs(vendor_id, sub_platform_id)

        all_results = []
        for vs_dir, collection_name in vs_dirs:
            try:
                from langchain_chroma import Chroma
                db = Chroma(
                    collection_name=collection_name,
                    embedding_function=embeddings,
                    persist_directory=str(vs_dir),
                )
                docs = db.similarity_search(query, k=3)
                for doc in docs:
                    source = doc.metadata.get("source", "未知来源")
                    level = self._get_level_label(vs_dir, vendor_id, sub_platform_id)
                    all_results.append((doc, source, level))
            except Exception:
                continue

        if not all_results:
            return ""

        all_results.sort(key=lambda x: len(x[0].page_content), reverse=True)
        seen = set()
        output_parts = []
        for doc, source, level in all_results[:8]:
            content_key = doc.page_content[:200]
            if content_key in seen:
                continue
            seen.add(content_key)
            output_parts.append(f"[{level}] 来源: {source}\n{doc.page_content[:500]}")

        return "\n\n---\n\n".join(output_parts)

    def _get_level_label(self, vs_dir, vendor_id: str, sub_platform_id: str) -> str:
        path_str = str(vs_dir).replace("\\", "/")
        if "/common/vectorstore" in path_str and f"/{vendor_id}/" not in path_str:
            return "全局"
        elif f"/{vendor_id}/common/" in path_str:
            return f"{vendor_id}公共"
        else:
            return "平台"

    def _fallback_search(self, query: str) -> str:
        if self.platform_context is None:
            return "未设置平台上下文，无法检索知识库"

        from pathlib import Path
        from knowledge.builder import get_all_doc_dirs

        vendor_id = self.platform_context.vendor.id
        sub_platform_id = self.platform_context.sub_platform.id
        doc_dirs = get_all_doc_dirs(vendor_id, sub_platform_id)

        results = []
        query_lower = query.lower()
        for docs_dir in doc_dirs:
            level = self._get_dir_level(docs_dir, vendor_id)
            for doc_file in docs_dir.glob("*.md"):
                try:
                    content = doc_file.read_text(encoding="utf-8", errors="ignore")
                    if query_lower in content.lower():
                        idx = content.lower().index(query_lower)
                        start = max(0, idx - 200)
                        end = min(len(content), idx + 300)
                        snippet = content[start:end]
                        results.append(f"[{level}] 来源: {doc_file.name}\n...{snippet}...")
                except Exception:
                    continue

        if not results:
            return f"在知识库中未找到与 '{query}' 相关的内容"

        return "\n\n---\n\n".join(results[:5])

    def _get_dir_level(self, docs_dir, vendor_id: str) -> str:
        path_str = str(docs_dir).replace("\\", "/")
        if "/common/platform_docs" in path_str and f"/{vendor_id}/" not in path_str:
            return "全局"
        elif f"/{vendor_id}/common/" in path_str:
            return f"{vendor_id}公共"
        else:
            return "平台"
