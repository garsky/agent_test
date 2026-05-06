import pytest
from tools.dts_parser import DTSParserTool
from models.schemas import ValidationSeverity


class TestDTSParser:
    def setup_method(self):
        self.tool = DTSParserTool()

    def test_empty_dts(self):
        result = self.tool._run("")
        assert "未找到" in result or "0" in result

    def test_camera_node_found(self):
        dts = """sensor@10 {
    compatible = "mediatek,camera-sensor";
    reg = <0x10>;
    avdd-supply = <&mt6357_vcamaf>;
    dvdd-supply = <&mt6357_vcamd>;
    reset-gpios = <&pio 15 GPIO_ACTIVE_LOW>;
    clocks = <&topckgen CLK_TOP_CAMTG>;
    status = "okay";
};"""
        result = self.tool._run(dts)
        assert "sensor@10" in result or "1" in result

    def test_missing_regulators(self):
        dts = """sensor@10 {
    compatible = "mediatek,camera-sensor";
    reg = <0x10>;
    status = "okay";
};"""
        result = self.tool._run(dts)
        assert "regulator" in result.lower()

    def test_invalid_i2c_address(self):
        dts = """sensor@78 {
    compatible = "mediatek,camera-sensor";
    reg = <0x78>;
    status = "okay";
};"""
        result = self.tool._run(dts)
        assert "0x78" in result or "超出" in result

    def test_status_not_okay(self):
        dts = """sensor@10 {
    compatible = "mediatek,camera-sensor";
    reg = <0x10>;
    status = "disabled";
};"""
        result = self.tool._run(dts)
        assert "disabled" in result or "okay" in result
