import pytest
from platform.manager import PlatformManager


class TestPlatformManager:
    def setup_method(self):
        self.manager = PlatformManager()

    def test_get_vendors(self):
        vendors = self.manager.get_vendors()
        assert len(vendors) == 3
        vendor_ids = [v["id"] for v in vendors]
        assert "qualcomm" in vendor_ids
        assert "mtk" in vendor_ids
        assert "unisoc" in vendor_ids

    def test_get_sub_platforms_mtk(self):
        sub_platforms = self.manager.get_sub_platforms("mtk")
        assert len(sub_platforms) >= 1
        sp_ids = [sp["id"] for sp in sub_platforms]
        assert "mt6985" in sp_ids

    def test_set_context(self):
        context = self.manager.set_context("mtk", "mt6985", "test_project")
        assert context.vendor.id == "mtk"
        assert context.sub_platform.id == "mt6985"
        assert context.project.name == "test_project"

    def test_set_context_invalid_vendor(self):
        with pytest.raises(ValueError):
            self.manager.set_context("invalid", "mt6985", "test")

    def test_platform_display_string(self):
        context = self.manager.set_context("mtk", "mt6985", "test_project")
        assert "MTK" in context.display_string
        assert "MT6985" in context.display_string

    def test_chroma_collection_names(self):
        context = self.manager.set_context("mtk", "mt6985", "proj_a")
        assert context.chroma_collection_platform == "mtk_mt6985_platform"
        assert context.chroma_collection_project == "mtk_mt6985_proj_a"
