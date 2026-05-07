from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import settings


@dataclass
class SubPlatformConfig:
    id: str
    display_name: str


@dataclass
class VendorConfig:
    id: str
    name: str
    display_name: str
    sub_platforms: dict[str, SubPlatformConfig] = field(default_factory=dict)


BUILTIN_REGISTRY: dict[str, VendorConfig] = {
    "qualcomm": VendorConfig(
        id="qualcomm",
        name="qualcomm",
        display_name="高通 (Qualcomm)",
        sub_platforms={
            "sm8550": SubPlatformConfig(id="sm8550", display_name="SM8550"),
            "sm8650": SubPlatformConfig(id="sm8650", display_name="SM8650"),
            "qcm4490": SubPlatformConfig(id="qcm4490", display_name="QCM4490"),
        },
    ),
    "mtk": VendorConfig(
        id="mtk",
        name="mtk",
        display_name="MTK (MediaTek)",
        sub_platforms={
            "mt6985": SubPlatformConfig(id="mt6985", display_name="MT6985 (24E)"),
            "mt6989": SubPlatformConfig(id="mt6989", display_name="MT6989"),
            "mt6897": SubPlatformConfig(id="mt6897", display_name="MT6897"),
        },
    ),
    "unisoc": VendorConfig(
        id="unisoc",
        name="unisoc",
        display_name="展锐 (UNISOC)",
        sub_platforms={
            "t820": SubPlatformConfig(id="t820", display_name="T820"),
            "t770": SubPlatformConfig(id="t770", display_name="T770"),
            "t750": SubPlatformConfig(id="t750", display_name="T750"),
        },
    ),
}


class PlatformRegistry:
    def __init__(self, knowledge_base_dir: Optional[str] = None):
        self._knowledge_base_dir = Path(knowledge_base_dir or settings.KNOWLEDGE_BASE_DIR)
        self._vendors: dict[str, VendorConfig] = dict(BUILTIN_REGISTRY)
        self._projects: dict[str, list[dict]] = {}

    def get_vendors(self) -> list[dict]:
        return [
            {"id": v.id, "name": v.name, "display_name": v.display_name}
            for v in self._vendors.values()
        ]

    def get_vendor_config(self, vendor_id: str) -> Optional[VendorConfig]:
        return self._vendors.get(vendor_id)

    def get_sub_platforms(self, vendor_id: str) -> list[dict]:
        vendor = self._vendors.get(vendor_id)
        if not vendor:
            return []
        return [
            {"id": sp.id, "display_name": sp.display_name, "vendor_id": vendor_id}
            for sp in vendor.sub_platforms.values()
        ]

    def get_sub_platform_config(self, vendor_id: str, sub_platform_id: str) -> Optional[SubPlatformConfig]:
        vendor = self._vendors.get(vendor_id)
        if not vendor:
            return None
        return vendor.sub_platforms.get(sub_platform_id)

    def get_sub_platform_knowledge_path(self, vendor_id: str, sub_platform_id: str) -> Path:
        return self._knowledge_base_dir / vendor_id / sub_platform_id

    def get_projects(self, vendor_id: str, sub_platform_id: str) -> list[dict]:
        key = f"{vendor_id}_{sub_platform_id}"
        return self._projects.get(key, [])

    def create_project(self, vendor_id: str, sub_platform_id: str, project_name: str) -> dict:
        key = f"{vendor_id}_{sub_platform_id}"
        project_id = project_name.lower().replace(" ", "_")
        project = {
            "id": project_id,
            "name": project_name,
            "sub_platform_id": sub_platform_id,
            "knowledge_path": str(self._knowledge_base_dir / vendor_id / sub_platform_id / "projects" / project_id),
        }
        if key not in self._projects:
            self._projects[key] = []
        self._projects[key].append(project)

        project_dir = self._knowledge_base_dir / vendor_id / sub_platform_id / "projects" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        return project

    def ensure_directories(self, vendor_id: str, sub_platform_id: str) -> None:
        base = self.get_sub_platform_knowledge_path(vendor_id, sub_platform_id)
        (base / "platform_docs").mkdir(parents=True, exist_ok=True)
        (base / "vectorstore").mkdir(parents=True, exist_ok=True)
        (base / "projects").mkdir(parents=True, exist_ok=True)


_registry: Optional[PlatformRegistry] = None


def get_registry() -> PlatformRegistry:
    global _registry
    if _registry is None:
        _registry = PlatformRegistry()
    return _registry
