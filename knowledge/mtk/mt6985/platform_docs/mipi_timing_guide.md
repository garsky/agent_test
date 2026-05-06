# MTK MIPI CSI Timing 配置指南

## MIPI CSI-2 协议基础

MIPI CSI-2 是 Camera Sensor 和 ISP 之间的标准接口协议，使用差分信号传输数据。

### 信号线
- **Clock Lane**: 1 对差分时钟信号
- **Data Lane**: 1-4 对差分数据信号

### 传输模式
- **LP (Low Power)**: 低功耗模式，用于控制信号
- **HS (High Speed)**: 高速模式，用于数据传输

## 关键 Timing 参数

### HS-SETTLE
- **定义**: HS 接收器建立时间
- **计算方法**: HS_SETTLE = (85 + 6*UI) / (2*UI)
  - UI = 1000 / data_rate_mbps (单位: ns)
- **范围**: 通常 4-100
- **影响**: 配置不当会导致数据采样错误

### HS-TRAIL
- **定义**: HS 传输后的尾随时间
- **范围**: 通常 4-255
- **最小值**: max(n*8*UI, 60+4*UI) ns

### CLK-POST
- **定义**: Clock Lane 在 HS 数据传输后保持 HS 的时间
- **范围**: 通常 4-255

### CLK-PRE
- **定义**: Clock Lane 在 HS 数据传输前的准备时间
- **范围**: 通常 1-255

### LP-11
- **定义**: LP 状态下的停止状态时间
- **最小值**: 100ns

## MTK 平台 Timing 配置

在 MTK 平台上，Timing 参数通常在 Seninf 驱动中配置：

```c
struct mtk_seninf_csi_info {
    u32 hs_settle;
    u32 hs_trail;
    u32 clk_post;
    u32 clk_pre;
    u32 lp11;
};
```

### 常见数据速率对应的 HS-SETTLE 参考值

| 数据速率 (Mbps/lane) | UI (ns) | HS-SETTLE 推荐值 |
|---------------------|---------|-----------------|
| 400                 | 2.5     | 20              |
| 800                 | 1.25    | 37              |
| 1000                | 1.0     | 47              |
| 1500                | 0.67    | 70              |
| 2000                | 0.5     | 95              |

## Timing 调试方法

1. **示波器测量**: 直接测量 MIPI 信号
2. **寄存器读取**: 通过 devmem 读取 Seninf 寄存器
3. **日志分析**: 检查 dmesg 中的 MIPI 错误信息
4. **逐步调整**: 从推荐值开始，逐步微调
