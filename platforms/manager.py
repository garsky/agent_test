from __future__ import annotations

from datetime import datetime
from typing import Optional

from platforms.context import Vendor, SubPlatform, Project, PlatformContext
from platforms.registry import PlatformRegistry, get_registry
from config.settings import settings


class PlatformManager:
    def __init__(self, registry: Optional[PlatformRegistry] = None):
        self._registry = registry or get_registry()
        self._current_context: Optional[PlatformContext] = None

    def get_vendors(self) -> list[dict]:
        return self._registry.get_vendors()

    def get_sub_platforms(self, vendor_id: str) -> list[dict]:
        return self._registry.get_sub_platforms(vendor_id)

    def get_projects(self, vendor_id: str, sub_platform_id: str) -> list[dict]:
        return self._registry.get_projects(vendor_id, sub_platform_id)

    def create_project(self, vendor_id: str, sub_platform_id: str, project_name: str) -> dict:
        return self._registry.create_project(vendor_id, sub_platform_id, project_name)

    def set_context(self, vendor_id: str, sub_platform_id: str, project_id: str) -> PlatformContext:
        vendor_cfg = self._registry.get_vendor_config(vendor_id)
        if not vendor_cfg:
            raise ValueError(f"Unknown vendor: {vendor_id}")

        sp_cfg = self._registry.get_sub_platform_config(vendor_id, sub_platform_id)
        if not sp_cfg:
            raise ValueError(f"Unknown sub-platform: {sub_platform_id} for vendor {vendor_id}")

        self._registry.ensure_directories(vendor_id, sub_platform_id)

        vendor = Vendor(id=vendor_cfg.id, name=vendor_cfg.name, display_name=vendor_cfg.display_name)
        sp_path = str(self._registry.get_sub_platform_knowledge_path(vendor_id, sub_platform_id))
        sub_platform = SubPlatform(
            id=sp_cfg.id, vendor_id=vendor_id, name=sp_cfg.id,
            display_name=sp_cfg.display_name, knowledge_path=sp_path,
        )

        projects = self._registry.get_projects(vendor_id, sub_platform_id)
        project_data = next((p for p in projects if p["id"] == project_id), None)
        if not project_data:
            project_data = self._registry.create_project(vendor_id, sub_platform_id, project_id)

        project = Project(
            id=project_data["id"],
            sub_platform_id=sub_platform_id,
            name=project_data["name"],
            knowledge_path=project_data["knowledge_path"],
            created_at=datetime.now(),
        )

        self._current_context = PlatformContext(vendor=vendor, sub_platform=sub_platform, project=project)
        return self._current_context

    @property
    def current_context(self) -> Optional[PlatformContext]:
        return self._current_context

    def get_platform_prompt_context(self, context: PlatformContext) -> str:
        vendor_id = context.vendor.id
        platform_knowledge = {
            "mtk": (
                "MTK 平台 Camera 驱动特性:\n"
                "- ISP: Imagiq 系列\n"
                "- Sensor 驱动基于 V4L2 框架\n"
                "- DTS 中需配置 SMI (Smart Multimedia Interface)\n"
                "- 电源域 (power domain) 配置需注意 SCP/SPM\n"
                "- IOMMU 映射需正确配置\n"
                "- 常见调试路径: /sys/kernel/debug/camera/\n"
            ),
            "qualcomm": (
                "高通平台 Camera 驱动特性:\n"
                "- ISP: CAMSS 架构\n"
                "- Sensor 驱动基于 V4L2 框架\n"
                "- DTS 中需配置 CPAS (Camera Port Aggregator Service)\n"
                "- 电源管理通过 RPMH\n"
                "- 常见调试路径: /sys/kernel/debug/camera/\n"
            ),
            "unisoc": (
                "展锐平台 Camera 驱动特性:\n"
                "- ISP: 展锐自研 ISP\n"
                "- Sensor 驱动基于 V4L2 框架\n"
                "- 电源管理通过 SCMI\n"
                "- 常见调试路径: /sys/kernel/debug/camera/\n"
            ),
        }
        return platform_knowledge.get(vendor_id, "")
