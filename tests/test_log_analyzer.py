import pytest
from tools.log_analyzer import LogAnalyzerTool
from models.schemas import ErrorCategory


class TestLogAnalyzer:
    def setup_method(self):
        self.tool = LogAnalyzerTool()

    def test_no_errors(self):
        result = self.tool._run("some normal log line\nanother normal line")
        assert "未发现" in result or "0" in result

    def test_i2c_error(self):
        log = """[    2.123] camera_sensor: probe started
[    2.124] i2c-0: i2c transfer failed, addr=0x10, NACK
[    2.125] camera_sensor: probe failed"""
        result = self.tool._run(log)
        assert "i2c" in result.lower() or "I2C" in result

    def test_mipi_error(self):
        log = """[    3.456] seninf: csi overflow detected
[    3.457] mipi: crc error detected"""
        result = self.tool._run(log)
        assert "mipi" in result.lower() or "MIPI" in result

    def test_power_error(self):
        log = """[    1.789] regulator_enable: failed to enable avdd
[    1.790] camera: power on failed"""
        result = self.tool._run(log)
        assert "power" in result.lower() or "regulator" in result.lower()

    def test_classify_i2c(self):
        line = "i2c-0: i2c transfer failed"
        category = self.tool._classify_line(line)
        assert category == ErrorCategory.I2C

    def test_classify_mipi(self):
        line = "mipi crc error detected"
        category = self.tool._classify_line(line)
        assert category == ErrorCategory.MIPI

    def test_classify_unknown(self):
        line = "some random camera message"
        category = self.tool._classify_line(line)
        assert category == ErrorCategory.UNKNOWN
