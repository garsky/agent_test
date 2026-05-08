from __future__ import annotations

from typing import Optional, Generator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, ToolMessage
from langgraph.prebuilt import create_react_agent

from agent.prompts import build_system_prompt
from agent.memory import AgentMemory
from config.llm_config import LLMConfig, LLMFactory
from platforms.context import PlatformContext


class CameraDriverAgent:
    def __init__(
        self,
        platform_context: PlatformContext,
        llm_config: Optional[LLMConfig] = None,
        max_iterations: int = 10,
    ):
        self._platform_context = platform_context
        self._llm_config = llm_config or LLMConfig.from_settings()
        self._max_iterations = max_iterations
        self._llm: Optional[BaseChatModel] = None
        self._memory = AgentMemory(platform_context)
        self._graph = None

    def _get_llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = LLMFactory.create_llm(self._llm_config)
        return self._llm

    def _get_tools(self):
        from tools.log_analyzer import LogAnalyzerTool
        from tools.dts_parser import DTSParserTool
        from tools.knowledge_search import KnowledgeSearchTool
        from tools.timing_checker import TimingCheckerTool
        from tools.code_analyzer import CodeAnalyzerTool
        from tools.web_searcher import WebSearcherTool

        return [
            LogAnalyzerTool(platform_context=self._platform_context),
            DTSParserTool(platform_context=self._platform_context),
            KnowledgeSearchTool(platform_context=self._platform_context),
            TimingCheckerTool(platform_context=self._platform_context),
            CodeAnalyzerTool(platform_context=self._platform_context),
            WebSearcherTool(platform_context=self._platform_context),
        ]

    def _build_agent(self):
        if self._graph is not None:
            return self._graph

        llm = self._get_llm()
        tools = self._get_tools()
        system_prompt = build_system_prompt(self._platform_context)

        self._graph = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
        )
        return self._graph

    async def chat(self, message: str) -> str:
        self._memory.add_user_message(message)
        graph = self._build_agent()

        result = await graph.ainvoke(
            {"messages": [("user", message)]},
        )

        messages = result.get("messages", [])
        if messages:
            response = messages[-1].content
        else:
            response = "抱歉，无法生成回复"

        self._memory.add_ai_message(response)
        return response

    def chat_sync(self, message: str) -> str:
        self._memory.add_user_message(message)
        graph = self._build_agent()

        result = graph.invoke(
            {"messages": [("user", message)]},
        )

        messages = result.get("messages", [])
        if messages:
            response = messages[-1].content
        else:
            response = "抱歉，无法生成回复"

        self._memory.add_ai_message(response)
        return response

    def chat_stream(self, message: str) -> Generator[str, None, None]:
        self._memory.add_user_message(message)
        graph = self._build_agent()

        full_response = ""
        in_tool_call = False

        for event in graph.stream(
            {"messages": [("user", message)]},
            stream_mode=["messages", "updates"],
        ):
            if isinstance(event, tuple) and len(event) == 2:
                mode, payload = event
            else:
                continue

            if mode == "messages":
                msg, metadata = payload
                if isinstance(msg, AIMessageChunk):
                    if msg.content:
                        full_response += msg.content
                        yield msg.content
                    if msg.tool_call_chunks:
                        for chunk in msg.tool_call_chunks:
                            if chunk.get("name") and not in_tool_call:
                                in_tool_call = True
                                tool_name = chunk.get("name", "")
                                yield f"\n  [调用工具: {tool_name}]\n"
                            if chunk.get("args"):
                                pass
                elif isinstance(msg, ToolMessage):
                    in_tool_call = False
                    tool_name = metadata.get("langgraph_node", "tools")
                    yield f"  [工具结果: {tool_name}]\n"

            elif mode == "updates":
                if isinstance(payload, dict):
                    for node_name, update in payload.items():
                        if node_name == "tools":
                            msgs = update.get("messages", [])
                            for m in msgs:
                                if isinstance(m, ToolMessage):
                                    yield f"  [工具执行完成]\n"

        if not full_response:
            full_response = "抱歉，无法生成回复"

        self._memory.add_ai_message(full_response)

    def set_platform_context(self, context: PlatformContext) -> None:
        self._platform_context = context
        self._memory = AgentMemory(context)
        self._graph = None
        self._llm = None

    def reset_conversation(self) -> None:
        self._memory.clear()
        self._graph = None

    @property
    def platform_context(self) -> PlatformContext:
        return self._platform_context
