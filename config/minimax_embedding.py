from __future__ import annotations

from typing import List

import requests
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, ConfigDict


class MiniMaxCustomEmbeddings(BaseModel, Embeddings):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: str = ""
    group_id: str = ""
    model: str = "embo-01"
    base_url: str = "https://api.minimax.chat/v1"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts, embed_type="db")

    def embed_query(self, text: str) -> List[float]:
        result = self._embed([text], embed_type="query")
        return result[0]

    def _embed(self, texts: List[str], embed_type: str = "db") -> List[List[float]]:
        if not texts:
            return []

        url = f"{self.base_url}/embeddings?GroupId={self.group_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "texts": texts,
            "model": self.model,
            "type": embed_type,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        result = resp.json()

        if "data" in result:
            return [item["embedding"] for item in result["data"]]

        if "vectors" in result and result["vectors"]:
            return result["vectors"]

        base_resp = result.get("base_resp", {})
        status_code = base_resp.get("status_code", "unknown")
        status_msg = base_resp.get("status_msg", "unknown error")
        raise ValueError(
            f"MiniMax Embedding API error: status_code={status_code}, "
            f"status_msg={status_msg}"
        )
