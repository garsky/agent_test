# Changelog

所有重要变更均记录在此文件中，格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

---

## [1.0.3] - 2026-05-07

### Added
- CLI Tab 补全: 输入命令时按 Tab 自动补全
  - 支持所有内置命令补全 (quit/reset/switch/help/config/kb/platform)
  - `kb add` 后按 Tab 补全文件名和路径 (支持 .md/.txt/.pdf/.docx/.pptx/.xlsx)
  - `kb` / `platform` 后按 Tab 补全子命令
  - 依赖 `pyreadline3` (Windows) / `readline` (Linux/Mac)
- 知识库无匹配时的回答策略优化:
  - 搜索无匹配时返回知识库文档清单，便于 Agent 引用已有文档
  - System Prompt 增加"无匹配回答规范": 禁止猜测、说明知识范畴、引用已有文档、指出缺失文档、给出排查方向

### Fixed
- `LangChainPendingDeprecationWarning` 警告抑制: 显式导入 `LangChainPendingDeprecationWarning` 并过滤

---

## [1.0.2] - 2026-05-07

### Fixed
- 删除子平台/厂商后重启 CLI 仍显示已删除项: 目录自动发现会重新注册磁盘上存在的目录
  - 新增黑名单机制: `removed_vendors` / `removed_sub_platforms` 持久化到 `platforms.yaml`
  - `_discover_from_directory()` 跳过黑名单中的厂商和子平台
  - 重新添加时自动从黑名单中移除 (`discard`)
- YAML 配置加载时检查目录存在性: 本地目录已删除的厂商/子平台不再从 `platforms.yaml` 加载
- 内置注册表加载时检查目录存在性: `_load_builtin_registry()` 只注册磁盘上实际存在的子平台
  - 修复 MTK 显示3个子平台但磁盘只有 mt6985 的问题
- `.gitignore` 更新: 排除 knowledge 下的数据文件(PDF/DOCX/vectorstore/platforms.yaml)，保留手写MD和目录结构(.gitkeep)

---

## [1.0.1] - 2026-05-07

### Added
- 加密 PDF 自动解密: 转换前自动检测加密并尝试解密
  - 优先尝试空密码 (大多数 MTK/高通 PDF 仅限制权限，用户密码为空)
  - 其次尝试 `.env` 中 `PDF_DEFAULT_PASSWORD` 配置的密码
  - 解密后生成临时 PDF，转换完成后自动清理
- `PDF_DEFAULT_PASSWORD` 配置项: 默认值 `1916691965`，可在 `.env` 中覆盖
- `pypdf` 依赖: 用于 PDF 解密和重写
- `_decrypt_pdf()`: 解密加密 PDF 并输出无加密临时文件
- `_get_pdf_passwords()`: 获取密码列表 (空密码 + 配置密码)

### Changed
- `convert_to_markdown()` 增加 PDF 加密检测和解密步骤
- 解密日志区分"空密码(仅权限限制)"和实际密码

---

## [1.0.0] - 2026-05-07

### Added
- 平台动态管理 (CLI + Web UI + YAML 配置 + 目录自动发现):
  - CLI: `platform add vendor <id> <显示名>` 添加厂商
  - CLI: `platform add sub <厂商> <id> <显示名>` 添加子平台
  - CLI: `platform remove vendor <id>` 移除厂商 (内置不可删)
  - CLI: `platform remove sub <厂商> <id>` 移除子平台 (内置不可删)
  - CLI: `platform list` 列出所有已注册平台
  - Web UI: 侧边栏添加"添加平台"区域 (厂商/子平台)
  - Web API: `POST /api/v1/platforms/vendors` 添加厂商
  - Web API: `POST /api/v1/platforms/sub-platforms` 添加子平台
  - Web API: `DELETE /api/v1/platforms/vendors/{id}` 移除厂商
  - Web API: `DELETE /api/v1/platforms/vendors/{vid}/sub-platforms/{spid}` 移除子平台
- YAML 配置持久化: `knowledge/platforms.yaml` 存储自定义平台
- 目录自动发现: 扫描 `knowledge/` 下已有目录自动注册平台
- `_sanitize_id()`: 自动将输入转为合法 ID (小写+下划线)
- 内置厂商 (高通/MTK/展锐) 保护: 不可删除内置平台

### Changed
- `PlatformRegistry.__init__()` 启动时加载 YAML + 自动发现
- `_discover_from_directory()` 排除 `__pycache__`、`.` 开头目录
- 帮助文本增加 `platform` 命令说明

---

## [0.7.1] - 2026-05-07

### Fixed
- Web UI 下拉菜单无选项: JS 正则表达式中 `\n` 被 Python 解释为换行符导致 JS 语法错误
  - `cleanResponse()` 中所有正则表达式转义修正 (`\\s`, `\\S`, `\\w`, `\\n`, `\\*`)
- Web UI `loadVendors()` / `loadSubPlatforms()` 添加 try-catch 错误处理
- Web UI 添加 fallback 内置数据: API 请求失败时使用内置厂商/子平台列表
- 添加 CORS 中间件支持跨域请求

---

## [0.7.0] - 2026-05-07

### Added
- 知识库三级层级架构:
  - `knowledge/common/` — 全局通用知识，所有平台共享
  - `knowledge/<厂商>/common/` — 厂商公共知识，同一厂商多平台共享 (如 MTK 公共架构)
  - `knowledge/<厂商>/<子平台>/` — 平台专属知识，仅当前子平台可见
- `kb add` 支持指定目标层级:
  - `kb add <文件>` — 默认添加到平台专属目录
  - `kb add <文件> --global` — 添加到全局通用目录
  - `kb add <文件> --vendor` — 添加到厂商公共目录
- `kb list` 显示所有层级的知识库文件，标注来源层级和源文件
- `kb update` 自动检测并更新三层知识库
- `update_knowledge_base()` 重构: 依次更新全局→厂商→平台三层知识库
- `_update_single_kb()` 独立的单层知识库更新函数
- `_cleanup_orphan_md()` 自动清理孤立 MD 文件 (源文件删除后对应的转换 MD)
- `get_all_doc_dirs()` / `get_all_vectorstore_dirs()` 获取三层知识库路径
- `init_knowledge_dirs()` 初始化三层知识库目录结构
- 知识检索合并三层结果，标注层级来源 (全局/厂商公共/平台)

### Changed
- `knowledge_search.py` 重构: `_multi_level_search()` 搜索三层向量库
- `_fallback_search()` 搜索三层文档目录
- 搜索结果标注层级标签: [全局] / [mtk公共] / [平台]
- 帮助文本更新: 增加知识库层级说明

---

## [0.6.0] - 2026-05-07

### Added
- 文档格式自动转换: 支持 PDF / DOCX / PPTX / XLSX 自动转换为 Markdown
  - 使用微软 MarkItDown 库 (GitHub 85k+ Stars)
  - `kb add` 支持 PDF/DOCX/PPTX/XLSX 文件，自动转换后添加到知识库
  - `kb update` 自动检测目录中的 PDF/DOCX/PPTX/XLSX，转换后增量索引
  - `kb build` 全量构建时也自动转换
  - 原始文件保留，转换后的 .md 文件与源文件同名
- 新增 `knowledge/converter.py` 文档转换模块
- 新增 `knowledge/builder.py` 中 `_auto_convert_docs()` 自动转换函数
  - 基于文件修改时间判断是否需要重新转换
  - 转换结果为空时跳过并提示

### Changed
- `kb add` 格式支持从 .md/.txt 扩展到 .pdf/.docx/.pptx/.xlsx
- 帮助文本更新: 列出所有支持的文件格式
- Web UI 侧边栏更新: 显示支持的文件格式

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
