from __future__ import annotations

from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

from platforms.context import PlatformContext


class AgentMemory:
    def __init__(self, platform_context: PlatformContext, max_window: int = 10):
        self._platform_context = platform_context
        self._max_window = max_window
        self._history = ChatMessageHistory()

    def add_user_message(self, content: str) -> None:
        self._history.add_user_message(content)

    def add_ai_message(self, content: str) -> None:
        self._history.add_ai_message(content)

    def get_messages(self) -> list[BaseMessage]:
        messages = self._history.messages
        if len(messages) > self._max_window * 2:
            messages = messages[-(self._max_window * 2):]
        return messages

    def clear(self) -> None:
        self._history.clear()

    @property
    def platform_context(self) -> PlatformContext:
        return self._platform_context
