from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


@dataclass
class Vendor:
    id: str
    name: str
    display_name: str


@dataclass
class SubPlatform:
    id: str
    vendor_id: str
    name: str
    display_name: str
    knowledge_path: str


@dataclass
class Project:
    id: str
    sub_platform_id: str
    name: str
    knowledge_path: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PlatformContext:
    vendor: Vendor
    sub_platform: SubPlatform
    project: Project
    _embeddings: Optional["Embeddings"] = field(default=None, repr=False)

    @property
    def platform_knowledge_path(self) -> str:
        return self.sub_platform.knowledge_path

    @property
    def project_knowledge_path(self) -> str:
        return self.project.knowledge_path

    @property
    def chroma_collection_platform(self) -> str:
        return f"{self.vendor.id}_{self.sub_platform.id}_platform"

    @property
    def chroma_collection_project(self) -> str:
        return f"{self.vendor.id}_{self.sub_platform.id}_{self.project.id}"

    @property
    def display_string(self) -> str:
        return f"{self.vendor.display_name} / {self.sub_platform.display_name} / {self.project.name}"
