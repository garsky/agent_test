from __future__ import annotations

import re
from collections import Counter
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from models.schemas import LogError, LogAnalysisResult, ErrorCategory


CAMERA_KEYWORDS = re.compile(
    r"cam|isp|sensor|mipi|csi|i2c.*cam|v4l2|vfe|actuator|eeprom|flash|ois",
    re.IGNORECASE,
)

ERROR_PATTERNS: dict[ErrorCategory, list[re.Pattern]] = {
    ErrorCategory.I2C: [
        re.compile(r"i2c.*transfer.*failed", re.IGNORECASE),
        re.compile(r"i2c.*NACK", re.IGNORECASE),
        re.compile(r"i2c.*timeout", re.IGNORECASE),
        re.compile(r"i2c.*error", re.IGNORECASE),
    ],
    ErrorCategory.MIPI: [
        re.compile(r"mipi.*err", re.IGNORECASE),
        re.compile(r"csi.*overflow", re.IGNORECASE),
        re.compile(r"csi.*epf", re.IGNORECASE),
        re.compile(r"mipi.*crc", re.IGNORECASE),
        re.compile(r"mipi.*fifo", re.IGNORECASE),
    ],
    ErrorCategory.POWER: [
        re.compile(r"regulator.*enable.*failed", re.IGNORECASE),
        re.compile(r"regulator.*disable.*failed", re.IGNORECASE),
        re.compile(r"voltage.*not.*set", re.IGNORECASE),
        re.compile(r"power.*domain.*failed", re.IGNORECASE),
    ],
    ErrorCategory.CLOCK: [
        re.compile(r"clk.*prepare.*failed", re.IGNORECASE),
        re.compile(r"clk.*enable.*failed", re.IGNORECASE),
        re.compile(r"clk.*get.*failed", re.IGNORECASE),
        re.compile(r"clock.*not.*found", re.IGNORECASE),
    ],
    ErrorCategory.DMA: [
        re.compile(r"dma.*alloc.*failed", re.IGNORECASE),
        re.compile(r"dma.*timeout", re.IGNORECASE),
        re.compile(r"dma.*error", re.IGNORECASE),
    ],
    ErrorCategory.GPIO: [
        re.compile(r"gpio.*request.*failed", re.IGNORECASE),
        re.compile(r"gpio.*direction.*failed", re.IGNORECASE),
        re.compile(r"pinctrl.*failed", re.IGNORECASE),
    ],
    ErrorCategory.DTS: [
        re.compile(r"of.*parse.*failed", re.IGNORECASE),
        re.compile(r"of.*get.*failed", re.IGNORECASE),
        re.compile(r"dts.*error", re.IGNORECASE),
        re.compile(r"device_node.*not.*found", re.IGNORECASE),
    ],
    ErrorCategory.ISP: [
        re.compile(r"isp.*error", re.IGNORECASE),
        re.compile(r"isp.*timeout", re.IGNORECASE),
        re.compile(r"isp.*fail", re.IGNORECASE),
    ],
    ErrorCategory.SENSOR: [
        re.compile(r"sensor.*not.*found", re.IGNORECASE),
        re.compile(r"sensor.*probe.*fail", re.IGNORECASE),
        re.compile(r"sensor.*init.*fail", re.IGNORECASE),
    ],
}

LEVEL_PATTERN = re.compile(r"<(\d)>|\b(ERROR|ERR|WARN|WARNING|CRITICAL|EMERG|INFO|DEBUG)\b", re.IGNORECASE)
ERROR_HINT_PATTERN = re.compile(r"\b(failed|failure|error|timeout|overflow|NACK|abort|fatal)\b", re.IGNORECASE)

CONTEXT_LINES = 5


class LogAnalyzerInput(BaseModel):
    log_content: str = Field(description="内核日志内容")


class LogAnalyzerTool(BaseTool):
    name: str = "log_analyzer"
    description: str = "分析内核日志，提取Camera相关错误信息"
    args_schema: Type[BaseModel] = LogAnalyzerInput
    model_config = ConfigDict(arbitrary_types_allowed=True)

    platform_context: object = None

    def _run(self, log_content: str) -> str:
        result = self._analyze(log_content)
        return self._format_result(result)

    def _analyze(self, log_content: str) -> LogAnalysisResult:
        lines = log_content.splitlines()
        errors: list[LogError] = []
        camera_line_indices: set[int] = set()

        for i, line in enumerate(lines):
            if CAMERA_KEYWORDS.search(line):
                camera_line_indices.add(i)

        for i, line in enumerate(lines):
            level = self._extract_level(line)
            is_error_hint = ERROR_HINT_PATTERN.search(line) is not None

            if level not in ("ERROR", "ERR", "WARN", "WARNING", "CRITICAL", "EMERG", "2", "3"):
                if not is_error_hint:
                    continue
                level = "ERROR"

            is_camera_line = CAMERA_KEYWORDS.search(line)
            near_camera = any(
                j in camera_line_indices
                for j in range(max(0, i - CONTEXT_LINES), min(len(lines), i + CONTEXT_LINES + 1))
            )
            if not is_camera_line and not near_camera:
                continue

            category = self._classify_line(line)

            start = max(0, i - CONTEXT_LINES)
            end = min(len(lines), i + CONTEXT_LINES + 1)
            context_before = lines[start:i]
            context_after = lines[i + 1:end]

            errors.append(LogError(
                line_number=i + 1,
                content=line.strip(),
                level=level,
                category=category,
                context_before=[l.strip() for l in context_before],
                context_after=[l.strip() for l in context_after],
            ))

        counter = Counter(e.category.value for e in errors)
        summary = self._generate_summary(errors, counter)

        return LogAnalysisResult(
            errors=errors,
            summary=summary,
            error_count_by_category=dict(counter),
        )

    def _extract_level(self, line: str) -> str:
        match = LEVEL_PATTERN.search(line)
        if match:
            num_level = match.group(1)
            text_level = match.group(2)
            if num_level:
                level_map = {"0": "EMERG", "1": "CRITICAL", "2": "CRITICAL", "3": "ERROR", "4": "WARN", "5": "INFO", "6": "DEBUG"}
                return level_map.get(num_level, num_level)
            if text_level:
                return text_level.upper()
        return "UNKNOWN"

    def _classify_line(self, line: str) -> ErrorCategory:
        for category, patterns in ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(line):
                    return category
        return ErrorCategory.UNKNOWN

    def _generate_summary(self, errors: list[LogError], counter: Counter) -> str:
        if not errors:
            return "未发现 Camera 相关错误"
        parts = [f"共发现 {len(errors)} 条 Camera 相关错误/警告"]
        for cat, count in counter.most_common():
            parts.append(f"  - {cat}: {count} 条")
        return "\n".join(parts)

    def _format_result(self, result: LogAnalysisResult) -> str:
        if not result.errors:
            return result.summary

        lines = [result.summary, ""]
        for err in result.errors[:20]:
            lines.append(f"[{err.level}][{err.category.value}] L{err.line_number}: {err.content}")
            if err.context_before:
                lines.append(f"  上下文前: {' | '.join(err.context_before[-2:])}")
            if err.context_after:
                lines.append(f"  上下文后: {' | '.join(err.context_after[:2])}")
            lines.append("")

        if len(result.errors) > 20:
            lines.append(f"... 还有 {len(result.errors) - 20} 条错误未显示")

        return "\n".join(lines)
