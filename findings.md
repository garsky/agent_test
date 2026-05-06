# 手机驱动工程师 Agent — 调研发现

## 领域知识

### MTK 24E 平台 Camera 驱动架构
- ISP: MTK Imagiq 系列
- Sensor 驱动: 基于 V4L2 框架
- Pipeline: Sensor → ISP → 3A → Output
- 关键组件:
  - Sensor Driver (i2c/spi 通信)
  - ISP Pipeline Driver
  - 3A Library (AE/AF/AWB)
  - Tuning 参数
  - HAL3 实现

### Camera 驱动常见问题分类

#### 1. 点亮问题 (Bring-up)
- Sensor 无法识别 (I2C 通信失败)
  - I2C 地址错误
  - 上电时序不正确 (AVDD/DVDD/DOVDD)
  - Reset/PWDN GPIO 配置错误
  - MCLK 时钟未使能
- DTS 配置问题
  - compatible 字符串不匹配
  - regulator 配置缺失
  - pinmux 配置错误
  - clk 配置缺失
- Kernel 启动阶段 Camera 初始化失败
  - 模组电源域未正确关联
  - 依赖的子系统未就绪

#### 2. 功能 Bug
- Preview 黑屏/花屏
  - MIPI CSI 配置错误 (lane数/速率)
  - Sensor 输出格式与 ISP 不匹配
  - Buffer 分配/管理问题
- 拍照失败
  - ZSL 流程异常
  - Capture stream 配置问题
  - Post-processing 管线错误
- 对焦问题
  - AF VCM 驱动加载失败
  - AF 校准数据缺失
  - 3A 算法参数异常
- 闪屏/帧率不稳
  - Frame drop
  - Buffer 耗尽
  - 帧率控制逻辑错误

#### 3. Timing 问题
- MIPI Timing 参数配置
  - HS-SETTLE / HS-TRAIL
  - LP-11 / LP-01
  - THS-ZERO / THS-PREPARE
- Sensor 曝光时序
  - Frame Rate / Exposure Time 冲突
  - HDR 时序不匹配
  - Long Exposure 模式配置
- 帧同步问题
  - 多摄同步 (VSYNC 对齐)
  - Sensor Mode 切换时序

### 通用驱动知识
- Linux Kernel 驱动模型: platform_driver, i2c_driver, spi_driver
- 设备树(Device Tree)语法和调试
- Kernel Log 分析 (dmesg, logcat, kernel panic)
- 驱动调试方法: debugfs, ftrace, devmem
- Android HAL3 与 Camera 驱动的交互

## 技术栈调研

### LangChain Agent 架构
- Agent 类型: ReAct Agent (Reasoning + Acting)
- 核心组件:
  - LLM: 大语言模型作为推理引擎
  - Tools: 自定义工具集
  - Memory: 对话记忆 + 知识检索
  - Chains: 预定义的工作流链

### 知识库方案
- 向量数据库: ChromaDB / FAISS
- 文档加载: LangChain Document Loaders
- Embedding: OpenAI / 本地模型
- 检索策略: 相似度搜索 + 关键词过滤

### 工具链方案
- 日志分析工具: 解析 dmesg/kernel log
- DTS 解析工具: 解析设备树文件
- 代码搜索工具: 在驱动源码中搜索
- 联网搜索工具: 搜索最新解决方案
