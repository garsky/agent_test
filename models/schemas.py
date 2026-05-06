from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ErrorCategory(str, Enum):
    I2C = "i2c"
    MIPI = "mipi"
    POWER = "power"
    CLOCK = "clock"
    DMA = "dma"
    GPIO = "gpio"
    DTS = "dts"
    ISP = "isp"
    SENSOR = "sensor"
    UNKNOWN = "unknown"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Suggestion:
    title: str
    description: str
    code_snippet: Optional[str] = None
    file_path: Optional[str] = None


@dataclass
class LogError:
    line_number: int
    content: str
    level: str
    category: ErrorCategory
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    timestamp: Optional[str] = None


@dataclass
class LogAnalysisResult:
    errors: list[LogError]
    summary: str
    error_count_by_category: dict[str, int] = field(default_factory=dict)


@dataclass
class DiagnosisReport:
    summary: str
    root_cause: str
    evidence: list[str]
    fix_suggestions: list[Suggestion]
    references: list[str]
    confidence: ConfidenceLevel


@dataclass
class CameraNode:
    name: str
    compatible: Optional[str] = None
    i2c_address: Optional[str] = None
    regulators: dict[str, str] = field(default_factory=dict)
    gpios: dict[str, str] = field(default_factory=dict)
    clocks: list[str] = field(default_factory=list)
    data_lanes: Optional[int] = None
    clock_lanes: Optional[int] = None
    status: Optional[str] = None
    raw_content: str = ""
    line_number: int = 0


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    field: str
    message: str
    current_value: Optional[str] = None
    expected_value: Optional[str] = None


@dataclass
class DTSReviewReport:
    nodes_found: list[CameraNode]
    issues: list[ValidationIssue]
    summary: str


@dataclass
class TimingCheckResult:
    parameter: str
    current_value: Optional[str]
    recommended_value: Optional[str]
    is_valid: bool
    message: str


@dataclass
class ExperienceCase:
    id: str
    platform: str
    sub_platform: str
    project: str
    problem: str
    root_cause: str
    solution: str
    created_at: datetime = field(default_factory=datetime.now)
