from __future__ import annotations

from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from models.schemas import TimingCheckResult



MIPI_TIMING_DEFAULTS: dict[str, dict] = {
    "mtk": {
        "hs_settle_min": 4,
        "hs_settle_max": 100,
        "hs_trail_min": 4,
        "hs_trail_max": 255,
        "clk_post_min": 4,
        "clk_post_max": 255,
        "clk_pre_min": 1,
        "clk_pre_max": 255,
        "lp11_min_ns": 100,
    },
    "qualcomm": {
        "hs_settle_min": 4,
        "hs_settle_max": 100,
        "hs_trail_min": 4,
        "hs_trail_max": 255,
        "clk_post_min": 4,
        "clk_post_max": 255,
        "clk_pre_min": 1,
        "clk_pre_max": 255,
        "lp11_min_ns": 100,
    },
    "unisoc": {
        "hs_settle_min": 4,
        "hs_settle_max": 100,
        "hs_trail_min": 4,
        "hs_trail_max": 255,
        "clk_post_min": 4,
        "clk_post_max": 255,
        "clk_pre_min": 1,
        "clk_pre_max": 255,
        "lp11_min_ns": 100,
    },
}


class TimingCheckInput(BaseModel):
    hs_settle: Optional[int] = Field(default=None, description="HS-SETTLE 参数值")
    hs_trail: Optional[int] = Field(default=None, description="HS-TRAIL 参数值")
    clk_post: Optional[int] = Field(default=None, description="CLK-POST 参数值")
    clk_pre: Optional[int] = Field(default=None, description="CLK-PRE 参数值")
    data_rate_mbps: Optional[float] = Field(default=None, description="MIPI 数据速率 (Mbps/lane)")
    sensor_model: Optional[str] = Field(default=None, description="Sensor 型号")


class TimingCheckerTool(BaseTool):
    name: str = "timing_checker"
    description: str = "校验MIPI CSI Timing参数是否符合规范"
    args_schema: Type[BaseModel] = TimingCheckInput

    platform_context: object = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(
        self,
        hs_settle: Optional[int] = None,
        hs_trail: Optional[int] = None,
        clk_post: Optional[int] = None,
        clk_pre: Optional[int] = None,
        data_rate_mbps: Optional[float] = None,
        sensor_model: Optional[str] = None,
    ) -> str:
        results = self._check(hs_settle, hs_trail, clk_post, clk_pre, data_rate_mbps, sensor_model)
        return self._format_results(results)

    def _check(
        self,
        hs_settle: Optional[int],
        hs_trail: Optional[int],
        clk_post: Optional[int],
        clk_pre: Optional[int],
        data_rate_mbps: Optional[float],
        sensor_model: Optional[str],
    ) -> list[TimingCheckResult]:
        vendor_id = self.platform_context.vendor.id if self.platform_context else "mtk"
        defaults = MIPI_TIMING_DEFAULTS.get(vendor_id, MIPI_TIMING_DEFAULTS["mtk"])
        results: list[TimingCheckResult] = []

        if hs_settle is not None:
            recommended = self._calculate_hs_settle(data_rate_mbps) if data_rate_mbps else None
            min_val = defaults["hs_settle_min"]
            max_val = defaults["hs_settle_max"]
            is_valid = min_val <= hs_settle <= max_val
            msg = f"HS-SETTLE={hs_settle}, 有效范围 [{min_val}, {max_val}]"
            if recommended is not None:
                msg += f", 推荐值≈{recommended}"
            results.append(TimingCheckResult(
                parameter="hs_settle",
                current_value=str(hs_settle),
                recommended_value=str(recommended) if recommended else None,
                is_valid=is_valid,
                message=msg,
            ))

        if hs_trail is not None:
            min_val = defaults["hs_trail_min"]
            max_val = defaults["hs_trail_max"]
            is_valid = min_val <= hs_trail <= max_val
            results.append(TimingCheckResult(
                parameter="hs_trail",
                current_value=str(hs_trail),
                recommended_value=None,
                is_valid=is_valid,
                message=f"HS-TRAIL={hs_trail}, 有效范围 [{min_val}, {max_val}]",
            ))

        if clk_post is not None:
            min_val = defaults["clk_post_min"]
            max_val = defaults["clk_post_max"]
            is_valid = min_val <= clk_post <= max_val
            results.append(TimingCheckResult(
                parameter="clk_post",
                current_value=str(clk_post),
                recommended_value=None,
                is_valid=is_valid,
                message=f"CLK-POST={clk_post}, 有效范围 [{min_val}, {max_val}]",
            ))

        if clk_pre is not None:
            min_val = defaults["clk_pre_min"]
            max_val = defaults["clk_pre_max"]
            is_valid = min_val <= clk_pre <= max_val
            results.append(TimingCheckResult(
                parameter="clk_pre",
                current_value=str(clk_pre),
                recommended_value=None,
                is_valid=is_valid,
                message=f"CLK-PRE={clk_pre}, 有效范围 [{min_val}, {max_val}]",
            ))

        if not results:
            results.append(TimingCheckResult(
                parameter="none",
                current_value=None,
                recommended_value=None,
                is_valid=True,
                message="未提供任何 Timing 参数进行校验",
            ))

        return results

    def _calculate_hs_settle(self, data_rate_mbps: float) -> int:
        if data_rate_mbps <= 0:
            return 8
        ui_ns = 1000.0 / data_rate_mbps
        settle_ns = 85.0 + 6.0 * ui_ns
        settle_val = int(settle_ns / (2.0 * ui_ns))
        return max(4, min(settle_val, 100))

    def _format_results(self, results: list[TimingCheckResult]) -> str:
        lines = ["MIPI CSI Timing 参数校验结果:", ""]
        for r in results:
            icon = "✅" if r.is_valid else "❌"
            lines.append(f"  {icon} {r.message}")
            if r.recommended_value:
                lines.append(f"     推荐值: {r.recommended_value}")
        return "\n".join(lines)
