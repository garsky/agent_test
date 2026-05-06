# Changelog

所有重要变更均记录在此文件中，格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

---

## [0.2.0] - 2026-05-06

### Changed
- 产品定位从 "MTK 24E 专用" 扩展为 "多平台支持 (高通/MTK/展锐)"
- 产品名称从 "MTK Camera 驱动工程师智能助手" 改为 "手机 Camera 驱动工程师智能助手"
- LLM 默认从 GPT-4 改为 MiniMax

### Added
- 三级平台/项目选择体系
  - 一级: 平台厂商 (高通/MTK/展锐)
  - 二级: 子平台 (如 MT6985/SM8550/T820)
  - 三级: 项目 (如 项目A/项目B)
- 知识库隔离机制
  - 不同子平台知识库完全隔离，不共享
  - 相同子平台不同项目共享平台知识库
  - 项目级知识项目私有
- 平台/项目管理模块 (PlatformManager)
  - 平台注册表 (PlatformRegistry)
  - 平台上下文 (PlatformContext)
  - 知识库路由 (按子平台自动路由)
- LLM 可配置机制
  - 支持 MiniMax / OpenAI / Anthropic / DeepSeek / Ollama
  - 通过 .env 文件配置 API Key 和模型参数
  - LLMFactory 工厂模式创建 LLM 实例
- 平台感知的工具设计
  - 所有工具绑定 PlatformContext
  - 日志分析/DTS解析/Timing校验 根据平台调整策略
  - 知识库检索自动路由到当前子平台
- 动态 System Prompt
  - 根据平台上下文动态生成 System Prompt
  - 包含平台特性知识注入
- F8: 平台/项目管理功能 (P0)
- 平台管理 API 接口
- LLM 配置 API 接口
- .env.example 环境变量模板

---

## [0.1.0] - 2026-05-06

### Added
- 产品定义文档 v0.1.0
  - 定义产品定位: MTK 24E Camera 驱动工程师智能助手
  - 定义 7 项核心功能 (F1-F7)
  - 定义目标用户和交互方式
  - 定义知识域和知识更新机制
  - 定义非功能需求和版本规划

- 技术设计文档 v0.1.0
  - 系统架构设计: Agent Core + Tools + Knowledge + Memory
  - 模块详细设计: 10 个核心模块的接口定义
  - 工具链设计: 6 个专业工具 (日志分析/DTS解析/知识检索/Timing校验/代码分析/联网搜索)
  - 知识库设计: ChromaDB + 7 类预置文档
  - API 设计: FastAPI + 5 个核心接口
  - 项目结构定义

- 项目初始化
  - Git 版本管理初始化
  - 任务规划文件 (task_plan.md)
  - 调研发现文件 (findings.md)
  - 进度日志文件 (progress.md)
