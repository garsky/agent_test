# Changelog

所有重要变更均记录在此文件中，格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

---

## [0.5.1] - 2026-05-07

### Changed
- `kb add` 添加文件后自动增量更新索引，无需再手动 `kb update`
- CLI 启动时自动检测知识库变更，有新文档自动索引
- Web API 创建 session 时自动检测知识库变更

### Added
- Web API 知识库管理接口: `POST /api/v1/kb/{vendor_id}/{sub_platform_id}/update`
- Web API 知识库文件列表接口: `GET /api/v1/kb/{vendor_id}/{sub_platform_id}/list`
- Web 侧边栏增加 `kb update` 提示

---

## [0.5.0] - 2026-05-07

### Added
- `kb update` 命令: 增量知识库更新，基于 MD5 文件哈希清单检测变更
  - 自动检测新增/修改/删除的文档文件
  - 增量更新 ChromaDB 向量索引（仅处理变更部分）
  - 清单文件 `.kb_manifest.json` 记录文件哈希状态
- 隐藏项目选择（默认 project_id="1"）
- CLI 帮助交互增强: WELCOME_BANNER、HELP_TEXT、KB_HELP
- 知识库文档添加规则和指导说明
- `knowledge/builder.py` 支持 `--update` 命令行参数

---

## [0.4.2] - 2026-05-06

### Fixed
- 设置 `HF_HUB_OFFLINE=1` 防止 HuggingFace 连接超时

---

## [0.4.1] - 2026-05-06

### Fixed
- Web UI 添加加载指示器 ("思考中...")
- Web UI 清理 `<think/>` 标签，避免显示原始思考过程
- Web UI 支持 Markdown 渲染 (代码块/加粗)
- Web UI 监听地址从 `0.0.0.0` 改为 `127.0.0.1` (Windows 兼容)

---

## [0.4.0] - 2026-05-06

### Added
- CLI 命令: `help` / `kb` / `config` 交互增强
- Web 聊天界面 (嵌入式 HTML，暗色主题)
- MiniMax Embedding 自定义实现 (GroupId URL 参数 + type=db body 参数)
- 本地 Embedding 支持 (sentence-transformers/shibing624/text2vec-base-chinese)
- Embedding 提供商可切换 (minimax/local)，默认 local

### Fixed
- `langchain_community.vectorstores.Chroma` 迁移到 `langchain_chroma.Chroma`
- Embedding 配置 `from_settings()` 添加 `local` 分支

---

## [0.3.1] - 2026-05-06

### Fixed
- Pydantic v2 兼容性: `class Config` → `model_config = ConfigDict(...)`
- `platform/` 目录重命名为 `platforms/`，避免与 Python 标准库 `platform` 模块冲突
- 日志分析工具增强上下文感知: 错误行附近有 Camera 关键字也会被捕获
- 日志分析工具增加错误提示关键字识别 (failed/NACK/timeout/overflow 等)
- Agent Core 从 `langchain.agents` 迁移到 `langgraph.prebuilt.create_react_agent`

### Added
- 依赖安装成功 (Python 3.14 + 阿里云镜像)
- langgraph 依赖
- 18 个单元测试全部通过

---

## [0.3.0] - 2026-05-06

### Added
- 完整原型实现 (38个文件, 2582行代码)
- 数据模型层 (models/schemas.py)
  - ConfidenceLevel, ErrorCategory, ValidationSeverity 枚举
  - DiagnosisReport, DTSReviewReport, TimingCheckResult 数据结构
  - CameraNode, LogError, Suggestion, ExperienceCase 数据类
- 配置模块 (config/)
  - settings.py: 全局配置，.env 文件加载
  - llm_config.py: LLM 工厂模式，支持 MiniMax/OpenAI/Anthropic/DeepSeek/Ollama
- 平台管理模块 (platform/)
  - context.py: Vendor/SubPlatform/Project/PlatformContext 数据结构
  - registry.py: 平台注册表 (高通/MTK/展锐 + 子平台)
  - manager.py: 平台/项目管理器，知识库路由
- 工具链 (tools/)
  - log_analyzer.py: 内核日志分析，9类错误模式识别
  - dts_parser.py: 设备树解析，8项配置检查
  - knowledge_search.py: 知识库检索 (ChromaDB + 文件回退)
  - timing_checker.py: MIPI CSI Timing 参数校验
  - code_analyzer.py: 代码片段常见问题检查
  - web_searcher.py: 联网搜索 (DuckDuckGo)
- Agent 核心 (agent/)
  - core.py: CameraDriverAgent 主类，ReAct Agent 编排
  - prompts.py: 动态 System Prompt 生成 (平台感知)
  - memory.py: 对话记忆管理
- API 层 (api/server.py)
  - FastAPI 服务，平台管理/对话/LLM配置接口
- CLI 入口 (main.py)
  - 交互式平台选择，对话循环
  - 支持 serve 模式启动 API 服务
- 知识库 (knowledge/)
  - MTK MT6985 平台文档: camera_arch/sensor_bringup/dts_config/common_errors/mipi_timing
  - 知识库构建脚本 (builder.py)
  - 高通/展锐目录预留
- 测试 (tests/)
  - test_log_analyzer.py: 日志分析工具测试
  - test_dts_parser.py: DTS 解析工具测试
  - test_platform_manager.py: 平台管理器测试
- 项目配置
  - pyproject.toml, requirements.txt, .env.example

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
