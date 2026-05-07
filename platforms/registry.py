from __future__ import annotations

import re
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

YAML_CONFIG_FILENAME = "platforms.yaml"


def _sanitize_id(name: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', name.lower()).strip('_')


class PlatformRegistry:
    def __init__(self, knowledge_base_dir: Optional[str] = None):
        self._knowledge_base_dir = Path(knowledge_base_dir or settings.KNOWLEDGE_BASE_DIR)
        self._vendors: dict[str, VendorConfig] = dict(BUILTIN_REGISTRY)
        self._projects: dict[str, list[dict]] = {}
        self._removed_vendors: set[str] = set()
        self._removed_sub_platforms: dict[str, set[str]] = {}
        self._load_yaml_config()
        self._discover_from_directory()

    def _get_yaml_path(self) -> Path:
        return self._knowledge_base_dir / YAML_CONFIG_FILENAME

    def _load_yaml_config(self) -> None:
        yaml_path = self._get_yaml_path()
        if not yaml_path.exists():
            return
        try:
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if not config:
                return
            for vid in (config.get("removed_vendors") or []):
                self._removed_vendors.add(vid)
            for vid, spids in (config.get("removed_sub_platforms") or {}).items():
                self._removed_sub_platforms[vid] = set(spids)
            if "vendors" not in config:
                return
            for vid, vdata in config["vendors"].items():
                vendor_dir = self._knowledge_base_dir / vid
                if not vendor_dir.exists():
                    continue
                display_name = vdata.get("display_name", vid)
                if vid in self._vendors:
                    self._vendors[vid].display_name = display_name
                else:
                    self._vendors[vid] = VendorConfig(
                        id=vid, name=vid, display_name=display_name,
                    )
                for spid, spdata in (vdata.get("sub_platforms") or {}).items():
                    sp_dir = vendor_dir / spid
                    if not sp_dir.exists():
                        continue
                    sp_display = spdata.get("display_name", spid) if isinstance(spdata, dict) else spdata
                    self._vendors[vid].sub_platforms[spid] = SubPlatformConfig(
                        id=spid, display_name=sp_display,
                    )
        except Exception as e:
            print(f"  警告: 加载 {yaml_path} 失败: {e}")

    def _save_yaml_config(self) -> None:
        yaml_path = self._get_yaml_path()
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import yaml
            config: dict = {"vendors": {}}
            for vid, vendor in self._vendors.items():
                if vid in BUILTIN_REGISTRY:
                    continue
                vdata: dict = {"display_name": vendor.display_name}
                if vendor.sub_platforms:
                    vdata["sub_platforms"] = {}
                    for spid, sp in vendor.sub_platforms.items():
                        builtin_sp = BUILTIN_REGISTRY.get(vid)
                        if builtin_sp and spid in builtin_sp.sub_platforms:
                            continue
                        vdata["sub_platforms"][spid] = {"display_name": sp.display_name}
                config["vendors"][vid] = vdata
            if self._removed_vendors:
                config["removed_vendors"] = sorted(self._removed_vendors)
            if self._removed_sub_platforms:
                config["removed_sub_platforms"] = {
                    vid: sorted(spids) for vid, spids in self._removed_sub_platforms.items() if spids
                }
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"  警告: 保存 {yaml_path} 失败: {e}")

    def _has_real_content(self, directory: Path) -> bool:
        if not directory.exists():
            return False
        for item in directory.rglob("*"):
            if item.is_file() and item.name != ".gitkeep":
                return True
        return False

    def _discover_from_directory(self) -> None:
        if not self._knowledge_base_dir.exists():
            return
        skip_dirs = {"common", "vectorstore", "__pycache__"}
        skip_subs = {"common", "vectorstore", "projects", "platform_docs", "__pycache__"}
        for item in self._knowledge_base_dir.iterdir():
            if not item.is_dir():
                continue
            vid = item.name
            if vid in skip_dirs or vid.startswith('.') or vid in self._removed_vendors:
                continue
            if vid not in self._vendors:
                self._vendors[vid] = VendorConfig(
                    id=vid, name=vid, display_name=vid,
                )
            removed_sps = self._removed_sub_platforms.get(vid, set())
            for sub_item in item.iterdir():
                if not sub_item.is_dir():
                    continue
                spid = sub_item.name
                if spid in skip_subs or spid.startswith('.') or spid in removed_sps:
                    continue
                if spid not in self._vendors[vid].sub_platforms:
                    self._vendors[vid].sub_platforms[spid] = SubPlatformConfig(
                        id=spid, display_name=spid,
                    )

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

    def add_vendor(self, vendor_id: str, display_name: str) -> dict:
        if vendor_id in self._vendors:
            return {"status": "exists", "message": f"厂商 {vendor_id} 已存在"}
        self._vendors[vendor_id] = VendorConfig(
            id=vendor_id, name=vendor_id, display_name=display_name,
        )
        self._removed_vendors.discard(vendor_id)
        vendor_dir = self._knowledge_base_dir / vendor_id / "common" / "platform_docs"
        vendor_dir.mkdir(parents=True, exist_ok=True)
        self._save_yaml_config()
        return {"status": "ok", "message": f"已添加厂商: {display_name} ({vendor_id})"}

    def add_sub_platform(self, vendor_id: str, sub_platform_id: str, display_name: str) -> dict:
        if vendor_id not in self._vendors:
            return {"status": "error", "message": f"厂商 {vendor_id} 不存在"}
        vendor = self._vendors[vendor_id]
        if sub_platform_id in vendor.sub_platforms:
            return {"status": "exists", "message": f"子平台 {sub_platform_id} 已存在"}
        vendor.sub_platforms[sub_platform_id] = SubPlatformConfig(
            id=sub_platform_id, display_name=display_name,
        )
        if vendor_id in self._removed_sub_platforms:
            self._removed_sub_platforms[vendor_id].discard(sub_platform_id)
        self.ensure_directories(vendor_id, sub_platform_id)
        self._save_yaml_config()
        return {"status": "ok", "message": f"已添加子平台: {display_name} ({sub_platform_id})"}

    def remove_vendor(self, vendor_id: str) -> dict:
        if vendor_id not in self._vendors:
            return {"status": "error", "message": f"厂商 {vendor_id} 不存在"}
        if vendor_id in BUILTIN_REGISTRY:
            return {"status": "error", "message": f"内置厂商 {vendor_id} 不可删除"}
        del self._vendors[vendor_id]
        self._removed_vendors.add(vendor_id)
        self._save_yaml_config()
        return {"status": "ok", "message": f"已移除厂商: {vendor_id}"}

    def remove_sub_platform(self, vendor_id: str, sub_platform_id: str) -> dict:
        if vendor_id not in self._vendors:
            return {"status": "error", "message": f"厂商 {vendor_id} 不存在"}
        vendor = self._vendors[vendor_id]
        if sub_platform_id not in vendor.sub_platforms:
            return {"status": "error", "message": f"子平台 {sub_platform_id} 不存在"}
        builtin = BUILTIN_REGISTRY.get(vendor_id)
        if builtin and sub_platform_id in builtin.sub_platforms:
            return {"status": "error", "message": f"内置子平台 {sub_platform_id} 不可删除"}
        del vendor.sub_platforms[sub_platform_id]
        if vendor_id not in self._removed_sub_platforms:
            self._removed_sub_platforms[vendor_id] = set()
        self._removed_sub_platforms[vendor_id].add(sub_platform_id)
        self._save_yaml_config()
        return {"status": "ok", "message": f"已移除子平台: {sub_platform_id}"}


_registry: Optional[PlatformRegistry] = None


def get_registry() -> PlatformRegistry:
    global _registry
    if _registry is None:
        _registry = PlatformRegistry()
    return _registry
