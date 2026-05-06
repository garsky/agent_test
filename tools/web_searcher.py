from __future__ import annotations

from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from platform.context import PlatformContext


class WebSearchInput(BaseModel):
    query: str = Field(description="搜索关键词")


class WebSearcherTool(BaseTool):
    name: str = "web_search"
    description: str = "联网搜索Camera驱动问题的最新解决方案"
    args_schema: Type[BaseModel] = WebSearchInput

    platform_context: Optional[PlatformContext] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, query: str) -> str:
        try:
            from langchain_community.tools import DuckDuckGoSearchResults

            search = DuckDuckGoSearchResults(max_results=5)
            results = search.invoke(query)
            if not results:
                return f"未找到与 '{query}' 相关的搜索结果"
            return f"搜索结果:\n{results}"
        except ImportError:
            return f"联网搜索功能需要安装 langchain-community 依赖。搜索关键词: '{query}'"
        except Exception as e:
            return f"搜索出错: {e}"
