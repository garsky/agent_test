from __future__ import annotations

from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field




class KnowledgeSearchInput(BaseModel):
    query: str = Field(description="搜索查询内容")


class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = "检索当前平台知识库中的Camera驱动相关文档"
    args_schema: Type[BaseModel] = KnowledgeSearchInput

    platform_context: object = None
    _retriever = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str) -> str:
        retriever = self._get_retriever()
        if retriever is None:
            return self._fallback_search(query)

        try:
            docs = retriever.invoke(query)
            if not docs:
                return f"知识库中未找到与 '{query}' 相关的内容"
            results = []
            for i, doc in enumerate(docs[:5], 1):
                source = doc.metadata.get("source", "未知来源")
                results.append(f"[{i}] 来源: {source}\n{doc.page_content[:500]}")
            return "\n\n---\n\n".join(results)
        except Exception as e:
            return f"知识库检索出错: {e}\n{self._fallback_search(query)}"

    def _get_retriever(self):
        if self._retriever is not None:
            return self._retriever

        if self.platform_context is None:
            return None

        try:
            import chromadb
            from langchain_chroma import Chroma
            from config.llm_config import LLMFactory, EmbeddingConfig

            embedding_config = EmbeddingConfig.from_settings()
            embeddings = LLMFactory.create_embeddings(embedding_config)

            persist_dir = self.platform_context.sub_platform.knowledge_path + "/vectorstore"
            collection_name = self.platform_context.chroma_collection_platform

            db = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=persist_dir,
            )
            self._retriever = db.as_retriever(search_kwargs={"k": 5})
            return self._retriever
        except Exception:
            return None

    def _fallback_search(self, query: str) -> str:
        if self.platform_context is None:
            return "未设置平台上下文，无法检索知识库"

        from pathlib import Path
        docs_dir = Path(self.platform_context.sub_platform.knowledge_path) / "platform_docs"
        if not docs_dir.exists():
            return f"知识库目录不存在: {docs_dir}，请先构建知识库"

        results = []
        query_lower = query.lower()
        for doc_file in docs_dir.glob("*.md"):
            content = doc_file.read_text(encoding="utf-8", errors="ignore")
            if query_lower in content.lower():
                idx = content.lower().index(query_lower)
                start = max(0, idx - 200)
                end = min(len(content), idx + 300)
                snippet = content[start:end]
                results.append(f"来源: {doc_file.name}\n...{snippet}...")

        if not results:
            return f"在知识库中未找到与 '{query}' 相关的内容"

        return "\n\n---\n\n".join(results[:5])
