# 手机驱动工程师 Agent — 调研发现

## 领域知识

### 高通平台 (Qualcomm)
- 芯片系列: Snapdragon (8系旗舰/7系中高端/6系中端/4系入门)
- 驱动架构: Linux Kernel + Qualcomm proprietary drivers
- 关键子系统:
  - Display (MDSS/DPU)
  - Camera (CAMSS/ISP)
  - Audio (ALSA/Q6)
  - Modem (RPMSG/GLINK)
  - USB (DWC3/QUSB)
  - GPU (Adreno/MSM DRM)
  - Power (PMIC/SPM)
- 常见驱动问题:
  - 设备树(dts)配置错误
  - 时钟/电源域配置缺失
  - 中断配置不当
  - DMA 通道冲突
  - 固件加载失败
  - GPIO/MUX 配置冲突

### MTK平台 (MediaTek)
- 芯片系列: Dimensity (9系旗舰/8系中高端/7系中端/6系入门)
- 驱动架构: Linux Kernel + MTK proprietary drivers
- 关键子系统:
  - Display (DSI/DPI)
  - Camera (ISP/Sensor)
  - Audio (ALSA/MTK AFE)
  - Modem (CCCI)
  - USB (MU3D)
  - GPU (Mali)
  - Power (SCP/SPM)
- 常见驱动问题:
  - DTS 节点配置错误
  - SMI (Smart Multimedia Interface) 总线配置
  - 电源域(power domain)配置
  - IOMMU 映射问题
  - CLK 配置缺失
  - 中断类型选择错误

### 通用驱动知识
- Linux Kernel 驱动模型: platform_driver, i2c_driver, spi_driver
- 设备树(Device Tree)语法和调试
- Kernel Log 分析 (dmesg, logcat, kernel panic)
- 驱动调试方法: debugfs, ftrace, devmem
- Android HAL 层与驱动的交互

## 技术栈调研
(待补充)
