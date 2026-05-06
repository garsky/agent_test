# 技术设计文档 (Technical Design Document)

## 版本: v0.1.0
## 最后更新: 2026-05-06
## 状态: 设计阶段

---

## 1. 系统架构

### 1.1 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                      API Layer                            │
│              (FastAPI / CLI Interface)                     │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                   Agent Core                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              LangChain ReAct Agent                   │ │
│  │  ┌───────────┐ ┌──────────┐ ┌────────────────────┐ │ │
│  │  │   LLM     │ │  Memory  │ │  Agent Executor    │ │ │
│  │  │  Engine   │ │  Module  │ │  (ReAct Loop)      │ │ │
│  │  └───────────┘ └──────────┘ └────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────┬──────────┬──────────┬──────────┬─────────────┘
           │          │          │          │
     ┌─────▼────┐ ┌──▼────┐ ┌──▼────┐ ┌───▼──────┐
     │Knowledge │ │Tools  │ │Exp    │ │Web       │
     │Base      │ │Layer  │ │Store  │ │Search    │
     └──────────┘ └───────┘ └───────┘ └──────────┘
```

### 1.2 数据流

```
用户输入 → API Layer → Agent Core
                         │
                    ┌────▼────┐
                    │ LLM 推理 │
                    └────┬────┘
                         │
              ┌──────────▼──────────┐
              │  需要调用工具？       │
              └────┬─────────┬──────┘
                   │ Yes     │ No
            ┌──────▼──┐     │
            │执行工具  │     │
            └──────┬──┘     │
                   │        │
              ┌────▼────────▼────┐
              │  LLM 继续推理     │
              └────────┬─────────┘
                       │
                  ┌────▼────┐
                  │  输出结果 │
                  └─────────┘
```

---

## 2. 模块详细设计

### 2.1 Agent Core (agent/core.py)

**职责**: Agent 的核心编排逻辑，管理 LLM 推理和工具调用的循环

**接口定义**:

```python
class CameraDriverAgent:
    def __init__(self, config: AgentConfig):
        """初始化 Agent"""

    async def chat(self, message: str, files: list[UploadedFile] = None) -> AgentResponse:
        """处理用户消息，返回 Agent 响应"""

    async def diagnose_log(self, log_content: str) -> DiagnosisReport:
        """分析内核日志"""

    async def review_dts(self, dts_content: str) -> DTSReviewReport:
        """审查设备树配置"""

    def reset_conversation(self):
        """重置对话上下文"""
```

**数据结构**:

```python
@dataclass
class AgentConfig:
    llm_model: str = "gpt-4"
    temperature: float = 0.1
    max_iterations: int = 10
    knowledge_base_path: str = "./knowledge"
    vector_db_path: str = "./vectorstore"

@dataclass
class AgentResponse:
    message: str
    diagnosis: Optional[DiagnosisReport]
    suggestions: list[Suggestion]
    tools_used: list[str]
    confidence: ConfidenceLevel

@dataclass
class DiagnosisReport:
    summary: str
    root_cause: str
    evidence: list[str]
    fix_suggestions: list[Suggestion]
    references: list[str]
    confidence: ConfidenceLevel

enum ConfidenceLevel:
    HIGH
    MEDIUM
    LOW
```

### 2.2 Prompts (agent/prompts.py)

**职责**: 管理 Agent 的 System Prompt 和各类模板

**System Prompt 核心结构**:

```
你是一位资深的 MTK Camera 驱动工程师，专注于 MTK 24E 平台。

## 你的专业领域
- Camera Sensor 驱动点亮 (Bring-up)
- Camera 功能 Bug 诊断
- MIPI CSI Timing 参数调优

## 你的工作方式
1. 先理解问题：仔细阅读用户描述和提供的日志/代码
2. 收集信息：使用工具分析日志、检索知识库
3. 推理诊断：基于证据推理问题根因
4. 给出方案：提供具体的修复建议和代码示例

## 你可以使用的工具
- log_analyzer: 分析内核日志，提取 Camera 相关错误
- dts_parser: 解析和审查设备树配置
- knowledge_search: 检索知识库中的相关文档
- timing_checker: 校验 MIPI Timing 参数
- code_analyzer: 分析代码片段
- web_search: 联网搜索解决方案

## 输出规范
- 诊断结果必须包含：问题摘要、根因分析、修复建议、置信度
- 修复建议必须具体到代码级别
- 如果不确定，明确说明并给出排查方向
```

### 2.3 Memory (agent/memory.py)

**职责**: 管理对话上下文和长期记忆

**设计**:
- **短期记忆**: LangChain ConversationBufferWindowMemory，保留最近 10 轮对话
- **长期记忆**: 向量化存储历史诊断案例，相似问题可检索
- **经验库**: SQLite 存储结构化的成功案例

```python
class AgentMemory:
    def __init__(self, config: MemoryConfig):
        """初始化记忆模块"""

    def add_message(self, role: str, content: str):
        """添加对话消息"""

    def get_context(self, query: str, k: int = 5) -> list[Document]:
        """检索相关上下文"""

    def save_experience(self, case: ExperienceCase):
        """保存成功案例到经验库"""

    def search_experience(self, query: str) -> list[ExperienceCase]:
        """搜索相似案例"""
```

### 2.4 Tools — 日志分析工具 (tools/log_analyzer.py)

**职责**: 解析内核日志，提取 Camera 相关错误信息

**功能**:
- 识别 Camera 相关的关键字: `cam`, `isp`, `sensor`, `mipi`, `csi`, `i2c.*cam`
- 提取错误级别: ERROR / WARN / CRITICAL
- 解析常见错误模式:
  - I2C 传输失败: `i2c.*transfer.*failed|NACK|timeout`
  - MIPI 错误: `mipi.*err|csi.*overflow|epf`
  - 电源错误: `regulator.*enable.*failed|voltage.*not.*set`
  - 时钟错误: `clk.*prepare.*failed|clk.*enable.*failed`
  - DMA 错误: `dma.*alloc.*failed|dma.*timeout`
- 关联错误上下文（前后各 5 行）

```python
class LogAnalyzerTool(BaseTool):
    name: str = "log_analyzer"
    description: str = "分析内核日志，提取Camera相关错误信息"

    def _run(self, log_content: str) -> LogAnalysisResult:
        """分析日志内容"""

    def _extract_camera_errors(self, log: str) -> list[LogError]:
        """提取 Camera 相关错误"""

    def _classify_error(self, error: LogError) -> ErrorCategory:
        """分类错误类型"""

    def _generate_summary(self, errors: list[LogError]) -> str:
        """生成错误摘要"""
```

### 2.5 Tools — DTS 解析工具 (tools/dts_parser.py)

**职责**: 解析设备树文件，检查 Camera 节点配置

**检查项**:
- compatible 字符串是否匹配已知 Sensor
- reg (I2C 地址) 是否在有效范围
- regulator 配置是否完整 (avdd/dvdd/dovdd)
- GPIO 配置 (reset/pwdn) 是否存在
- clock 配置 (mclk) 是否存在
- MIPI CSI 配置 (data-lanes / clock-lanes) 是否合理
- status 是否设为 "okay"

```python
class DTSParserTool(BaseTool):
    name: str = "dts_parser"
    description: str = "解析设备树文件，检查Camera节点配置的完整性和正确性"

    def _run(self, dts_content: str) -> DTSReviewReport:
        """审查 DTS 配置"""

    def _parse_camera_nodes(self, dts: str) -> list[CameraNode]:
        """解析 Camera 相关节点"""

    def _validate_node(self, node: CameraNode) -> list[ValidationIssue]:
        """校验节点配置"""

    def _check_compatibility(self, node: CameraNode) -> Optional[str]:
        """检查 compatible 是否匹配已知 Sensor"""
```

### 2.6 Tools — 知识库检索工具 (tools/knowledge_search.py)

**职责**: 从预置知识库中检索相关文档

```python
class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = "检索知识库中的Camera驱动相关文档"

    def _run(self, query: str) -> list[Document]:
        """检索相关文档"""

    def _hybrid_search(self, query: str, k: int = 5) -> list[Document]:
        """混合检索: 向量相似度 + 关键词匹配"""
```

### 2.7 Tools — Timing 校验工具 (tools/timing_checker.py)

**职责**: 校验 MIPI CSI Timing 参数

```python
class TimingCheckerTool(BaseTool):
    name: str = "timing_checker"
    description: str = "校验MIPI CSI Timing参数是否符合规范"

    def _run(self, timing_params: dict, sensor_spec: str = None) -> TimingCheckResult:
        """校验 Timing 参数"""

    def _calculate_hs_settle(self, clk_rate: int, data_rate: int) -> int:
        """计算 HS-SETTLE 推荐值"""

    def _validate_lp_time(self, lp_param: str, value: int) -> Optional[str]:
        """校验 LP 时间参数"""
```

### 2.8 Tools — 联网搜索工具 (tools/web_searcher.py)

**职责**: 联网搜索最新解决方案

```python
class WebSearcherTool(BaseTool):
    name: str = "web_search"
    description: str = "联网搜索Camera驱动问题的最新解决方案"

    def _run(self, query: str) -> list[SearchResult]:
        """搜索并返回结果摘要"""
```

### 2.9 Knowledge Base (knowledge/)

**职责**: 预置知识库的构建和管理

**知识库构建流程**:
1. 收集原始文档 (MD/PDF/TXT)
2. 使用 LangChain Document Loaders 加载
3. 文本分块 (RecursiveCharacterTextSplitter, chunk_size=1000, overlap=200)
4. 生成 Embedding (OpenAIEmbeddings / 本地模型)
5. 存入 ChromaDB

**知识库内容规划**:

| 文档 | 内容概要 | 优先级 |
|------|---------|--------|
| mtk_camera_arch.md | MTK Camera 驱动架构概述 | P0 |
| sensor_bringup_guide.md | Sensor 点亮步骤指南 | P0 |
| dts_config_reference.md | DTS 配置参考手册 | P0 |
| common_errors.md | 常见错误码及解决方案 | P0 |
| mipi_timing_guide.md | MIPI Timing 配置指南 | P1 |
| i2c_debug_guide.md | I2C 通信调试指南 | P1 |
| isp_pipeline_guide.md | ISP Pipeline 配置指南 | P2 |

### 2.10 API Layer (api/server.py)

**职责**: 提供 HTTP API 接口

```python
# FastAPI 接口定义

POST /api/v1/chat
  - Body: { "message": str, "files": list[File], "session_id": str }
  - Response: AgentResponse

POST /api/v1/diagnose/log
  - Body: { "log_content": str, "platform": str }
  - Response: DiagnosisReport

POST /api/v1/review/dts
  - Body: { "dts_content": str, "platform": str }
  - Response: DTSReviewReport

GET /api/v1/sessions/{session_id}
  - Response: ConversationHistory

DELETE /api/v1/sessions/{session_id}
  - Response: Success
```

---

## 3. 技术选型

| 组件 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 语言 | Python | 3.11+ | AI 生态最完善 |
| Agent 框架 | LangChain | 0.3+ | 灵活编排，工具生态丰富 |
| LLM | GPT-4 / Claude | - | 代码理解能力强，待评估 |
| 向量数据库 | ChromaDB | 0.4+ | 轻量级，本地运行，无需额外服务 |
| Embedding | OpenAIEmbeddings | - | 质量稳定，API 简单 |
| Web 框架 | FastAPI | 0.100+ | 异步支持好，自动生成文档 |
| 包管理 | uv / pip | - | 快速依赖管理 |

---

## 4. 项目结构

```
camera_driver_agent/
├── agent/
│   ├── __init__.py
│   ├── core.py              # CameraDriverAgent 主类
│   ├── prompts.py           # System Prompt & 模板
│   └── memory.py            # 对话记忆 + 经验积累
├── tools/
│   ├── __init__.py
│   ├── log_analyzer.py      # 日志分析工具
│   ├── dts_parser.py        # DTS 解析工具
│   ├── knowledge_search.py  # 知识库检索工具
│   ├── timing_checker.py    # Timing 校验工具
│   ├── code_analyzer.py     # 代码分析工具
│   └── web_searcher.py      # 联网搜索工具
├── knowledge/
│   ├── docs/                # 预置知识文档
│   │   ├── mtk_camera_arch.md
│   │   ├── sensor_bringup_guide.md
│   │   ├── dts_config_reference.md
│   │   ├── common_errors.md
│   │   └── mipi_timing_guide.md
│   ├── vectorstore/         # ChromaDB 数据目录
│   └── builder.py           # 知识库构建脚本
├── models/
│   ├── __init__.py
│   └── schemas.py           # 数据模型定义
├── api/
│   ├── __init__.py
│   └── server.py            # FastAPI 服务
├── config/
│   ├── __init__.py
│   └── settings.py          # 全局配置
├── tests/
│   ├── test_agent.py
│   ├── test_log_analyzer.py
│   ├── test_dts_parser.py
│   └── test_timing_checker.py
├── main.py                  # CLI 入口
├── pyproject.toml           # 项目配置
├── requirements.txt         # 依赖列表
├── .env.example             # 环境变量模板
└── docs/
    ├── product_definition.md
    ├── technical_design.md
    └── changelog.md
```

---

## 5. 关键流程

### 5.1 问题诊断流程

```
用户提问
    │
    ▼
Agent 接收消息
    │
    ▼
LLM 推理: 理解问题意图
    │
    ├── 需要日志分析? ──→ 调用 log_analyzer
    ├── 需要DTS审查?  ──→ 调用 dts_parser
    ├── 需要知识检索?  ──→ 调用 knowledge_search
    ├── 需要Timing校验? ─→ 调用 timing_checker
    ├── 需要代码分析?  ──→ 调用 code_analyzer
    └── 需要联网搜索?  ──→ 调用 web_searcher
    │
    ▼
LLM 综合推理: 基于工具返回结果
    │
    ▼
生成诊断报告
    │
    ▼
输出响应 + 保存经验(如果成功)
```

### 5.2 知识库构建流程

```
原始文档 (MD/PDF)
    │
    ▼
Document Loader 加载
    │
    ▼
Text Splitter 分块
(chunk_size=1000, overlap=200)
    │
    ▼
Embedding 生成
    │
    ▼
存入 ChromaDB
```

---

## 6. 依赖清单

```
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0
chromadb>=0.4.0
fastapi>=0.100.0
uvicorn>=0.24.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```
