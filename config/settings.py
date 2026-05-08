from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    LLM_PROVIDER: str = "minimax"
    AGENT_MAX_ITERATIONS: int = 10
    AGENT_TEMPERATURE: float = 0.1

    MINIMAX_API_KEY: str = ""
    MINIMAX_GROUP_ID: str = ""
    MINIMAX_MODEL: str = "MiniMax-M2"
    MINIMAX_BASE_URL: str = "https://api.minimax.chat/v1"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "llama3"

    EMBEDDING_PROVIDER: str = "minimax"
    MINIMAX_EMBEDDING_MODEL: str = "embo-01"

    CHROMA_PERSIST_DIR: str = str(Path(__file__).parent.parent / "knowledge" / "vectorstore")

    KNOWLEDGE_BASE_DIR: str = str(Path(__file__).parent.parent / "knowledge")

    PDF_DEFAULT_PASSWORD: str = "1916691965"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
