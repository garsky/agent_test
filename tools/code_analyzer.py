from __future__ import annotations

from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from platform.context import PlatformContext


COMMON_CODE_ISSUES = [
    {
        "pattern": r"msleep\s*\(\s*1\s*\)",
        "message": "使用 msleep(1) 可能导致实际延迟远大于1ms，建议使用 usleep_range()",
        "severity": "warning",
    },
    {
        "pattern": r"mdelay\s*\(",
        "message": "使用 mdelay() 会忙等待，建议使用 msleep() 或 usleep_range()",
        "severity": "warning",
    },
    {
        "pattern": r"printk\s*\(",
        "message": "建议使用 dev_info/dev_err/dev_dbg 替代 printk",
        "severity": "info",
    },
    {
        "pattern": r"i2c_transfer\s*\(",
        "message": "i2c_transfer 调用，注意检查返回值是否为负数",
        "severity": "info",
    },
    {
        "pattern": r"regulator_enable\s*\(",
        "message": "regulator_enable 调用，注意检查返回值",
        "severity": "info",
    },
    {
        "pattern": r"clk_prepare_enable\s*\(",
        "message": "clk_prepare_enable 调用，注意检查返回值",
        "severity": "info",
    },
    {
        "pattern": r"gpio_request\s*\(",
        "message": "gpio_request 已废弃，建议使用 devm_gpio_request",
        "severity": "warning",
    },
    {
        "pattern": r"devm_kzalloc\s*\([^,]+,\s*GFP_KERNEL\s*\)",
        "message": "devm_kzalloc 使用正确，自动释放",
        "severity": "info",
    },
]


class CodeAnalyzerInput(BaseModel):
    code_content: str = Field(description="代码片段内容")
    file_type: str = Field(default="c", description="文件类型: c/h")


class CodeAnalyzerTool(BaseTool):
    name: str = "code_analyzer"
    description: str = "分析Camera驱动代码片段，检查常见问题"
    args_schema: Type[BaseModel] = CodeAnalyzerInput

    platform_context: Optional[PlatformContext] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, code_content: str, file_type: str = "c") -> str:
        issues = self._analyze(code_content, file_type)
        return self._format_issues(issues)

    def _analyze(self, code_content: str, file_type: str) -> list[dict]:
        import re

        issues = []

        for issue_def in COMMON_CODE_ISSUES:
            matches = list(re.finditer(issue_def["pattern"], code_content))
            for match in matches:
                line_num = code_content[:match.start()].count("\n") + 1
                issues.append({
                    "line": line_num,
                    "severity": issue_def["severity"],
                    "message": issue_def["message"],
                    "matched": match.group(0),
                })

        return sorted(issues, key=lambda x: x["line"])

    def _format_issues(self, issues: list[dict]) -> str:
        if not issues:
            return "代码分析完成，未发现常见问题"

        lines = [f"代码分析发现 {len(issues)} 个关注点:", ""]
        for issue in issues:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue["severity"], "•")
            lines.append(f"  {icon} L{issue['line']}: {issue['message']}")
            lines.append(f"     匹配: {issue['matched']}")

        return "\n".join(lines)
