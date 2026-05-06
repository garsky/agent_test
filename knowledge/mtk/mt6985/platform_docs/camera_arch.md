# MTK MT6985 (24E) Camera 驱动架构

## 概述
MT6985 (代号24E) 是 MediaTek 的高端移动平台，搭载 Imagiq ISP，支持多摄并发。

## ISP 架构
- Imagiq 系列 ISP
- 支持多路并发处理
- RAW/MJPEG/YUV 多格式输入
- 内置 3A 算法 (AE/AF/AWB)

## Camera Pipeline
```
Sensor → MIPI CSI-2 → ISP → 3A → Post-Processing → Output
```

## 关键驱动模块
- `mtk-cam` : Camera 核心驱动
- `mtk-isp` : ISP 驱动
- `mtk-seninf` : Sensor Interface 驱动 (MIPI CSI 接收)
- `mtk-cam-dip` : DIP (Digital Image Processing) 驱动
- `mtk-cam-mdp` : MDP (Media Data Path) 驱动

## V4L2 框架
- 基于 V4L2 sub-device 架构
- Sensor 作为 sub-device 注册
- Seninf 作为 sub-device 注册
- 通过 media controller 统一管理

## HAL3 接口
- Android Camera HAL3 实现
- 支持多流并发
- ZSL (Zero Shutter Lag) 支持
