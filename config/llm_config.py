from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from config.settings import settings


@dataclass
class LLMConfig:
    provider: str = ""
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096

    @classmethod
    def from_settings(cls) -> "LLMConfig":
        provider = settings.LLM_PROVIDER
        key_map = {
            "minimax": ("MINIMAX_API_KEY", "MINIMAX_MODEL", "MINIMAX_BASE_URL"),
            "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"),
            "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", ""),
            "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_BASE_URL"),
            "local": ("", "LOCAL_LLM_MODEL", "LOCAL_LLM_BASE_URL"),
        }
        key_attr, model_attr, url_attr = key_map.get(provider, key_map["minimax"])
        return cls(
            provider=provider,
            api_key=getattr(settings, key_attr, "") if key_attr else "",
            model=getattr(settings, model_attr, ""),
            base_url=getattr(settings, url_attr, "") if url_attr else "",
            temperature=settings.AGENT_TEMPERATURE,
        )


@dataclass
class EmbeddingConfig:
    provider: str = ""
    api_key: str = ""
    model: str = ""
    base_url: str = ""

    @classmethod
    def from_settings(cls) -> "EmbeddingConfig":
        provider = settings.EMBEDDING_PROVIDER
        if provider == "minimax":
            return cls(
                provider="minimax",
                api_key=settings.MINIMAX_API_KEY,
                model=settings.MINIMAX_EMBEDDING_MODEL,
                base_url=settings.MINIMAX_BASE_URL,
            )
        elif provider == "openai":
            return cls(
                provider="openai",
                api_key=settings.OPENAI_API_KEY,
                model="text-embedding-3-small",
                base_url=settings.OPENAI_BASE_URL,
            )
        return cls(provider="minimax", api_key=settings.MINIMAX_API_KEY, model=settings.MINIMAX_EMBEDDING_MODEL, base_url=settings.MINIMAX_BASE_URL)


class LLMFactory:
    @staticmethod
    def create_llm(config: Optional[LLMConfig] = None) -> BaseChatModel:
        if config is None:
            config = LLMConfig.from_settings()

        provider = config.provider

        if provider in ("minimax", "openai", "deepseek"):
            from langchain_openai import ChatOpenAI

            default_models = {
                "minimax": "MiniMax-M2",
                "openai": "gpt-4",
                "deepseek": "deepseek-chat",
            }
            default_urls = {
                "minimax": "https://api.minimax.chat/v1",
                "openai": "https://api.openai.com/v1",
                "deepseek": "https://api.deepseek.com/v1",
            }
            return ChatOpenAI(
                api_key=config.api_key,
                model=config.model or default_models[provider],
                base_url=config.base_url or default_urls[provider],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                api_key=config.api_key,
                model=config.model or "claude-3-sonnet-20240229",
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        elif provider == "local":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                base_url=config.base_url or "http://localhost:11434",
                model=config.model or "llama3",
                temperature=config.temperature,
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def create_embeddings(config: Optional[EmbeddingConfig] = None) -> Embeddings:
        if config is None:
            config = EmbeddingConfig.from_settings()

        provider = config.provider

        if provider == "minimax":
            from langchain_community.embeddings import MiniMaxEmbeddings

            return MiniMaxEmbeddings(
                minimax_api_key=config.api_key,
                minimax_group_id=settings.MINIMAX_GROUP_ID or None,
                model=config.model or "embo-01",
            )

        elif provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                api_key=config.api_key,
                model=config.model or "text-embedding-3-small",
                base_url=config.base_url or "https://api.openai.com/v1",
            )

        elif provider == "local":
            from langchain_huggingface import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(
                model_name=config.model or "shibing624/text2vec-base-chinese",
            )

        else:
            from langchain_community.embeddings import FakeEmbeddings

            return FakeEmbeddings(size=768)
