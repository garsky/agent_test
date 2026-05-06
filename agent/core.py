from __future__ import annotations

from typing import Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel

from agent.prompts import build_system_prompt
from agent.memory import AgentMemory
from config.llm_config import LLMConfig, LLMFactory
from platform.context import PlatformContext
from platform.manager import PlatformManager


REACT_PROMPT_TEMPLATE = """{system_prompt}

**IMPORTANT: When you need to use a tool, you MUST format your response as:**
```
Action: tool_name
Action Input: {{"param": "value"}}
```

**After receiving the tool result, provide your final answer with:**
```
Final Answer: your detailed answer here
```

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""


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
        self._agent_executor: Optional[AgentExecutor] = None

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

    def _build_agent(self) -> AgentExecutor:
        if self._agent_executor is not None:
            return self._agent_executor

        llm = self._get_llm()
        tools = self._get_tools()

        system_prompt = build_system_prompt(self._platform_context)

        prompt = ChatPromptTemplate.from_messages([
            ("system", REACT_PROMPT_TEMPLATE.format(system_prompt=system_prompt, tools="{tools}", tool_names="{tool_names}", input="{input}", agent_scratchpad="{agent_scratchpad}")),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}"),
        ])

        agent = create_react_agent(llm, tools, prompt)
        self._agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=self._max_iterations,
            verbose=True,
            handle_parsing_errors=True,
        )
        return self._agent_executor

    async def chat(self, message: str) -> str:
        self._memory.add_user_message(message)
        agent_executor = self._build_agent()

        chat_history = self._memory.get_messages()

        result = await agent_executor.ainvoke({
            "input": message,
            "chat_history": chat_history,
        })

        response = result.get("output", "抱歉，无法生成回复")
        self._memory.add_ai_message(response)
        return response

    def chat_sync(self, message: str) -> str:
        self._memory.add_user_message(message)
        agent_executor = self._build_agent()

        chat_history = self._memory.get_messages()

        result = agent_executor.invoke({
            "input": message,
            "chat_history": chat_history,
        })

        response = result.get("output", "抱歉，无法生成回复")
        self._memory.add_ai_message(response)
        return response

    def set_platform_context(self, context: PlatformContext) -> None:
        self._platform_context = context
        self._memory = AgentMemory(context)
        self._agent_executor = None
        self._llm = None

    def reset_conversation(self) -> None:
        self._memory.clear()
        self._agent_executor = None

    @property
    def platform_context(self) -> PlatformContext:
        return self._platform_context
