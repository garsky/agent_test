from __future__ import annotations

import re
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from models.schemas import CameraNode, ValidationIssue, DTSReviewReport, ValidationSeverity



KNOWN_SENSORS: dict[str, list[str]] = {
    "mtk": [
        "s5k3l6", "s5kgn9", "s5khm2", "s5kjn1", "s5k2ld",
        "imx586", "imx582", "imx766", "imx890", "imx882", "imx363",
        "ov64b40", "ov13b10", "ov08a10", "gc13a0", "hi846",
    ],
    "qualcomm": [
        "imx586", "imx577", "imx476", "imx363",
        "ov64b40", "ov13b10", "s5k3l6", "s5khm2",
    ],
    "unisoc": [
        "ov64b40", "ov13b10", "gc13a0", "hi846",
        "imx586", "s5k3l6",
    ],
}

VALID_REGULATORS = {"avdd", "dvdd", "dovdd", "vdd", "vdda", "vddio", "afvdd"}
VALID_GPIOS = {"reset", "pwdn", "powerdown", "enable", "standby"}


class DTSParserInput(BaseModel):
    dts_content: str = Field(description="设备树文件内容")


class DTSParserTool(BaseTool):
    name: str = "dts_parser"
    description: str = "解析设备树文件，检查Camera节点配置的完整性和正确性"
    args_schema: Type[BaseModel] = DTSParserInput

    platform_context: object = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, dts_content: str) -> str:
        result = self._analyze(dts_content)
        return self._format_result(result)

    def _analyze(self, dts_content: str) -> DTSReviewReport:
        nodes = self._parse_camera_nodes(dts_content)
        issues: list[ValidationIssue] = []

        for node in nodes:
            issues.extend(self._validate_node(node))

        if not nodes:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="camera_nodes",
                message="未找到 Camera 相关节点，请检查 DTS 内容",
            ))

        summary = self._generate_summary(nodes, issues)
        return DTSReviewReport(nodes_found=nodes, issues=issues, summary=summary)

    def _parse_camera_nodes(self, dts_content: str) -> list[CameraNode]:
        nodes: list[CameraNode] = []
        node_pattern = re.compile(r"(\w+@\w+)\s*\{", re.MULTILINE)
        camera_hint = re.compile(r"camera|cam|sensor|csi|mipi", re.IGNORECASE)

        for match in node_pattern.finditer(dts_content):
            node_name = match.group(1)
            start = match.end()
            brace_count = 1
            pos = start
            while pos < len(dts_content) and brace_count > 0:
                if dts_content[pos] == "{":
                    brace_count += 1
                elif dts_content[pos] == "}":
                    brace_count -= 1
                pos += 1

            block = dts_content[start:pos - 1]

            if not camera_hint.search(block) and not camera_hint.search(node_name):
                compatible_match = re.search(r'compatible\s*=\s*"([^"]+)"', block)
                if compatible_match and not camera_hint.search(compatible_match.group(1)):
                    continue

            node = self._extract_node_fields(node_name, block, match.start())
            nodes.append(node)

        return nodes

    def _extract_node_fields(self, name: str, block: str, line_offset: int) -> CameraNode:
        compatible = self._extract_string(block, "compatible")
        i2c_address = self._extract_string(block, "reg")
        status = self._extract_string(block, "status")

        regulators: dict[str, str] = {}
        for reg_name in VALID_REGULATORS:
            val = self._extract_string(block, f"{reg_name}-supply") or self._extract_string(block, reg_name)
            if val:
                regulators[reg_name] = val

        gpios: dict[str, str] = {}
        for gpio_name in VALID_GPIOS:
            val = self._extract_string(block, f"{gpio_name}-gpios") or self._extract_string(block, f"{gpio_name}-gpio")
            if val:
                gpios[gpio_name] = val

        clocks = re.findall(r'clocks\s*=\s*[<&]([^&>]+)[>&]', block)

        data_lanes_match = re.search(r'data-lanes\s*=\s*<([^>]+)>', block)
        data_lanes = None
        if data_lanes_match:
            data_lanes = len(data_lanes_match.group(1).split())

        clock_lanes_match = re.search(r'clock-lanes\s*=\s*<(\d+)>', block)
        clock_lanes = None
        if clock_lanes_match:
            clock_lanes = int(clock_lanes_match.group(1))

        line_number = block[:0].count("\n") + 1

        return CameraNode(
            name=name,
            compatible=compatible,
            i2c_address=i2c_address,
            regulators=regulators,
            gpios=gpios,
            clocks=clocks,
            data_lanes=data_lanes,
            clock_lanes=clock_lanes,
            status=status,
            raw_content=block,
            line_number=line_number,
        )

    def _extract_string(self, block: str, field_name: str) -> Optional[str]:
        match = re.search(rf'{field_name}\s*=\s*"([^"]+)"', block)
        if match:
            return match.group(1)
        match = re.search(rf'{field_name}\s*=\s*<([^>]+)>', block)
        if match:
            return match.group(1).strip()
        return None

    def _validate_node(self, node: CameraNode) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        vendor_id = self.platform_context.vendor.id if self.platform_context else "mtk"

        if not node.compatible:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field="compatible",
                message=f"节点 {node.name} 缺少 compatible 属性",
            ))
        else:
            known = KNOWN_SENSORS.get(vendor_id, [])
            compatible_lower = node.compatible.lower()
            if not any(s in compatible_lower for s in known):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="compatible",
                    message=f"compatible '{node.compatible}' 不在已知 Sensor 列表中",
                    current_value=node.compatible,
                ))

        if node.i2c_address:
            try:
                addr = int(node.i2c_address.replace("0x", ""), 16)
                if addr < 0x08 or addr > 0x77:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field="reg",
                        message=f"I2C 地址 {node.i2c_address} 超出有效范围 (0x08-0x77)",
                        current_value=node.i2c_address,
                    ))
            except ValueError:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="reg",
                    message=f"无法解析 I2C 地址: {node.i2c_address}",
                    current_value=node.i2c_address,
                ))

        if not node.regulators:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="regulators",
                message=f"节点 {node.name} 未配置 regulator (avdd/dvdd/dovdd)",
            ))
        else:
            for required in ["avdd", "dvdd"]:
                if required not in node.regulators:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        field=f"{required}-supply",
                        message=f"节点 {node.name} 未配置 {required} regulator",
                    ))

        if not node.gpios:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="gpios",
                message=f"节点 {node.name} 未配置 GPIO (reset/pwdn)",
            ))

        if not node.clocks:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="clocks",
                message=f"节点 {node.name} 未配置 clock (mclk)",
            ))

        if node.status and node.status != "okay":
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                field="status",
                message=f"节点 {node.name} status 为 '{node.status}'，非 'okay'",
                current_value=node.status,
                expected_value="okay",
            ))

        if node.data_lanes is not None and node.data_lanes > 4:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field="data-lanes",
                message=f"data-lanes 数量 {node.data_lanes} 超过最大值 4",
                current_value=str(node.data_lanes),
            ))

        return issues

    def _generate_summary(self, nodes: list[CameraNode], issues: list[ValidationIssue]) -> str:
        parts = [f"发现 {len(nodes)} 个 Camera 相关节点"]
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warn_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        info_count = sum(1 for i in issues if i.severity == ValidationSeverity.INFO)
        parts.append(f"检查结果: {error_count} 错误 / {warn_count} 警告 / {info_count} 提示")
        return "\n".join(parts)

    def _format_result(self, result: DTSReviewReport) -> str:
        lines = [result.summary, ""]

        for node in result.nodes_found:
            lines.append(f"节点: {node.name}")
            if node.compatible:
                lines.append(f"  compatible: {node.compatible}")
            if node.i2c_address:
                lines.append(f"  I2C地址: {node.i2c_address}")
            if node.status:
                lines.append(f"  status: {node.status}")
            lines.append("")

        if result.issues:
            lines.append("检查问题:")
            for issue in result.issues:
                icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity.value, "•")
                lines.append(f"  {icon} [{issue.severity.value}] {issue.field}: {issue.message}")
                if issue.current_value:
                    lines.append(f"     当前值: {issue.current_value}")
                if issue.expected_value:
                    lines.append(f"     期望值: {issue.expected_value}")

        return "\n".join(lines)
