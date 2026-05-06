# 技术设计文档 (Technical Design Document)

## 版本: v0.2.0
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
│              Platform & Project Manager                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Platform Registry / Project Context / KB Router    │ │
│  └─────────────────────────────────────────────────────┘ │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                   Agent Core                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              LangChain ReAct Agent                   │ │
│  │  ┌───────────┐ ┌──────────┐ ┌────────────────────┐ │ │
│  │  │   LLM     │ │  Memory  │ │  Agent Executor    │ │ │
│  │  │  Engine   │ │  Module  │ │  (ReAct Loop)      │ │ │
│  │  │(可配置)   │ │          │ │                    │ │ │
│  │  └───────────┘ └──────────┘ └────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────┬──────────┬──────────┬──────────┬─────────────┘
           │          │          │          │
     ┌─────▼────┐ ┌──▼────┐ ┌──▼────┐ ┌───▼──────┐
     │Knowledge │ │Tools  │ │Exp    │ │Web       │
     │Base      │ │Layer  │ │Store  │ │Search    │
     │(按子平台 │ │       │ │       │ │          │
     │ 隔离)    │ │       │ │       │ │          │
     └──────────┘ └───────┘ └───────┘ └──────────┘
```

### 1.2 数据流

```
用户输入 + 平台/项目上下文
    │
    ▼
API Layer → Platform Manager (加载对应知识库)
    │
    ▼
Agent Core
    │
    ├── LLM 推理 (使用用户配置的 LLM)
    │
    ├── 需要调用工具？
    │   ├── log_analyzer (日志分析)
    │   ├── dts_parser (DTS审查)
    │   ├── knowledge_search (知识库检索, 按子平台路由)
    │   ├── timing_checker (Timing校验)
    │   ├── code_analyzer (代码分析)
    │   └── web_search (联网搜索)
    │
    ▼
LLM 综合推理 → 输出结果
```

---

## 2. 模块详细设计

### 2.1 Platform & Project Manager (platform/manager.py)

**职责**: 管理平台/子平台/项目的三级选择，路由知识库

**接口定义**:

```python
class PlatformManager:
    def __init__(self, config: PlatformConfig):
        """初始化平台管理器"""

    def get_vendors(self) -> list[Vendor]:
        """获取所有平台厂商"""

    def get_sub_platforms(self, vendor_id: str) -> list[SubPlatform]:
        """获取指定厂商下的子平台"""

    def get_projects(self, vendor_id: str, sub_platform_id: str) -> list[Project]:
        """获取指定子平台下的项目"""

    def create_project(self, vendor_id: str, sub_platform_id: str, project_name: str) -> Project:
        """在指定子平台下创建新项目"""

    def set_context(self, vendor_id: str, sub_platform_id: str, project_id: str) -> PlatformContext:
        """设置当前平台/项目上下文"""

    def get_knowledge_base(self, context: PlatformContext) -> KnowledgeBase:
        """根据上下文获取对应的知识库 (平台共享 + 项目私有)"""

    def get_platform_prompt_context(self, context: PlatformContext) -> str:
        """获取平台相关的 Prompt 上下文信息"""
```

**数据结构**:

```python
@dataclass
class Vendor:
    id: str
    name: str
    display_name: str

@dataclass
class SubPlatform:
    id: str
    vendor_id: str
    name: str
    display_name: str
    knowledge_path: str

@dataclass
class Project:
    id: str
    sub_platform_id: str
    name: str
    knowledge_path: str
    created_at: datetime

@dataclass
class PlatformContext:
    vendor: Vendor
    sub_platform: SubPlatform
    project: Project
    knowledge_base: KnowledgeBase
```

**平台注册表** (platform/registry.py):

```python
PLATFORM_REGISTRY = {
    "qualcomm": VendorConfig(
        id="qualcomm",
        name="qualcomm",
        display_name="高通 (Qualcomm)",
        sub_platforms={
            "sm8550": SubPlatformConfig(id="sm8550", display_name="SM8550"),
            "sm8650": SubPlatformConfig(id="sm8650", display_name="SM8650"),
            "qcm4490": SubPlatformConfig(id="qcm4490", display_name="QCM4490"),
        }
    ),
    "mtk": VendorConfig(
        id="mtk",
        name="mtk",
        display_name="MTK (MediaTek)",
        sub_platforms={
            "mt6985": SubPlatformConfig(id="mt6985", display_name="MT6985 (24E)"),
            "mt6989": SubPlatformConfig(id="mt6989", display_name="MT6989"),
            "mt6897": SubPlatformConfig(id="mt6897", display_name="MT6897"),
        }
    ),
    "unisoc": VendorConfig(
        id="unisoc",
        name="unisoc",
        display_name="展锐 (UNISOC)",
        sub_platforms={
            "t820": SubPlatformConfig(id="t820", display_name="T820"),
            "t770": SubPlatformConfig(id="t770", display_name="T770"),
            "t750": SubPlatformConfig(id="t750", display_name="T750"),
        }
    ),
}
```

### 2.2 LLM Configuration (config/llm_config.py)

**职责**: 管理可配置的 LLM 提供商，支持用户自定义

**设计**:
- 默认使用 MiniMax
- 通过 `.env` 文件配置 API Key 和模型参数
- 支持多种 LLM 提供商热切换

**.env 配置模板**:

```env
# LLM Configuration
# 当前使用的 LLM 提供商: minimax / openai / anthropic / deepseek / local
LLM_PROVIDER=minimax

# MiniMax (默认)
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_MODEL=MiniMax-Text-01
MINIMAX_BASE_URL=https://api.minimax.chat/v1

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Local LLM (Ollama)
LOCAL_LLM_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3

# Embedding Configuration
EMBEDDING_PROVIDER=minimax
MINIMAX_EMBEDDING_MODEL=embo-01

# ChromaDB
CHROMA_PERSIST_DIR=./knowledge/vectorstore
```

**接口定义**:

```python
class LLMFactory:
    @staticmethod
    def create_llm(config: LLMConfig) -> BaseChatModel:
        """根据配置创建 LLM 实例"""

    @staticmethod
    def create_embeddings(config: EmbeddingConfig) -> Embeddings:
        """根据配置创建 Embedding 实例"""

@dataclass
class LLMConfig:
    provider: str = "minimax"
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
```

**LLM 适配器**:

```python
class LLMAAdapter:
    PROVIDERS = {
        "minimax": lambda cfg: ChatOpenAI(
            api_key=cfg.api_key,
            model=cfg.model or "MiniMax-Text-01",
            base_url=cfg.base_url or "https://api.minimax.chat/v1",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        ),
        "openai": lambda cfg: ChatOpenAI(
            api_key=cfg.api_key,
            model=cfg.model or "gpt-4",
            base_url=cfg.base_url or "https://api.openai.com/v1",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        ),
        "anthropic": lambda cfg: ChatAnthropic(
            api_key=cfg.api_key,
            model=cfg.model or "claude-3-sonnet-20240229",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        ),
        "deepseek": lambda cfg: ChatOpenAI(
            api_key=cfg.api_key,
            model=cfg.model or "deepseek-chat",
            base_url=cfg.base_url or "https://api.deepseek.com/v1",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        ),
        "local": lambda cfg: ChatOllama(
            base_url=cfg.base_url or "http://localhost:11434",
            model=cfg.model or "llama3",
            temperature=cfg.temperature,
        ),
    }
```

### 2.3 Agent Core (agent/core.py)

**职责**: Agent 的核心编排逻辑，管理 LLM 推理和工具调用的循环

**接口定义**:

```python
class CameraDriverAgent:
    def __init__(self, config: AgentConfig, platform_context: PlatformContext):
        """初始化 Agent，绑定平台上下文"""

    async def chat(self, message: str, files: list[UploadedFile] = None) -> AgentResponse:
        """处理用户消息，返回 Agent 响应"""

    async def diagnose_log(self, log_content: str) -> DiagnosisReport:
        """分析内核日志"""

    async def review_dts(self, dts_content: str) -> DTSReviewReport:
        """审查设备树配置"""

    def set_platform_context(self, context: PlatformContext):
        """切换平台/项目上下文"""

    def reset_conversation(self):
        """重置对话上下文"""
```

**数据结构**:

```python
@dataclass
class AgentConfig:
    llm_config: LLMConfig
    max_iterations: int = 10

@dataclass
class AgentResponse:
    message: str
    platform_context: PlatformContext
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

class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

### 2.4 Prompts (agent/prompts.py)

**职责**: 管理 Agent 的 System Prompt，根据平台上下文动态生成

**System Prompt 核心结构**:

```
你是一位资深的 {vendor_display_name} Camera 驱动工程师，专注于 {sub_platform_display_name} 平台。

## 当前上下文
- 平台: {vendor_display_name}
- 子平台: {sub_platform_display_name}
- 项目: {project_name}

## 你的专业领域
- Camera Sensor 驱动点亮 (Bring-up)
- Camera 功能 Bug 诊断
- MIPI CSI Timing 参数调优

## 平台特性
{platform_specific_knowledge}

## 你的工作方式
1. 先理解问题：仔细阅读用户描述和提供的日志/代码
2. 收集信息：使用工具分析日志、检索知识库
3. 推理诊断：基于证据推理问题根因
4. 给出方案：提供具体的修复建议和代码示例

## 你可以使用的工具
- log_analyzer: 分析内核日志，提取 Camera 相关错误
- dts_parser: 解析和审查设备树配置
- knowledge_search: 检索当前平台知识库中的相关文档
- timing_checker: 校验 MIPI Timing 参数
- code_analyzer: 分析代码片段
- web_search: 联网搜索解决方案

## 输出规范
- 诊断结果必须包含：问题摘要、根因分析、修复建议、置信度
- 修复建议必须具体到代码级别
- 如果不确定，明确说明并给出排查方向
- 所有建议需基于当前平台 ({sub_platform_display_name}) 的特性
```

### 2.5 Memory (agent/memory.py)

**职责**: 管理对话上下文和长期记忆

**设计**:
- **短期记忆**: LangChain ConversationBufferWindowMemory，保留最近 10 轮对话
- **长期记忆**: 向量化存储历史诊断案例，按子平台隔离
- **经验库**: SQLite 存储结构化的成功案例，按项目隔离

```python
class AgentMemory:
    def __init__(self, config: MemoryConfig, platform_context: PlatformContext):
        """初始化记忆模块，绑定平台上下文"""

    def add_message(self, role: str, content: str):
        """添加对话消息"""

    def get_context(self, query: str, k: int = 5) -> list[Document]:
        """检索相关上下文 (平台共享 + 项目私有)"""

    def save_experience(self, case: ExperienceCase):
        """保存成功案例到经验库 (项目级)"""

    def search_experience(self, query: str) -> list[ExperienceCase]:
        """搜索相似案例 (平台共享 + 项目私有)"""
```

### 2.6 Tools — 日志分析工具 (tools/log_analyzer.py)

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
- 根据平台上下文调整关键字匹配策略

```python
class LogAnalyzerTool(BaseTool):
    name: str = "log_analyzer"
    description: str = "分析内核日志，提取Camera相关错误信息"

    def __init__(self, platform_context: PlatformContext):
        """初始化，绑定平台上下文"""

    def _run(self, log_content: str) -> LogAnalysisResult:
        """分析日志内容"""

    def _extract_camera_errors(self, log: str) -> list[LogError]:
        """提取 Camera 相关错误"""

    def _classify_error(self, error: LogError) -> ErrorCategory:
        """分类错误类型"""

    def _generate_summary(self, errors: list[LogError]) -> str:
        """生成错误摘要"""
```

### 2.7 Tools — DTS 解析工具 (tools/dts_parser.py)

**职责**: 解析设备树文件，检查 Camera 节点配置

**检查项** (根据平台上下文调整):
- compatible 字符串是否匹配已知 Sensor
- reg (I2C 地址) 是否在有效范围
- regulator 配置是否完整 (avdd/dvdd/dovdd)
- GPIO 配置 (reset/pwdn) 是否存在
- clock 配置 (mclk) 是否存在
- MIPI CSI 配置 (data-lanes / clock-lanes) 是否合理
- status 是否设为 "okay"
- 平台特有检查项 (如 MTK 的 SMI 配置、高通的 CPAS 配置)

```python
class DTSParserTool(BaseTool):
    name: str = "dts_parser"
    description: str = "解析设备树文件，检查Camera节点配置的完整性和正确性"

    def __init__(self, platform_context: PlatformContext):
        """初始化，绑定平台上下文"""

    def _run(self, dts_content: str) -> DTSReviewReport:
        """审查 DTS 配置"""

    def _parse_camera_nodes(self, dts: str) -> list[CameraNode]:
        """解析 Camera 相关节点"""

    def _validate_node(self, node: CameraNode) -> list[ValidationIssue]:
        """校验节点配置 (平台相关)"""
```

### 2.8 Tools — 知识库检索工具 (tools/knowledge_search.py)

**职责**: 从预置知识库中检索相关文档，按子平台路由

**关键设计**: 知识库检索自动路由到当前子平台的知识库

```python
class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = "检索当前平台知识库中的Camera驱动相关文档"

    def __init__(self, platform_context: PlatformContext):
        """初始化，绑定平台上下文，自动路由到对应知识库"""

    def _run(self, query: str) -> list[Document]:
        """检索相关文档 (平台共享 + 项目私有)"""

    def _hybrid_search(self, query: str, k: int = 5) -> list[Document]:
        """混合检索: 向量相似度 + 关键词匹配"""
```

### 2.9 Tools — Timing 校验工具 (tools/timing_checker.py)

**职责**: 校验 MIPI CSI Timing 参数

```python
class TimingCheckerTool(BaseTool):
    name: str = "timing_checker"
    description: str = "校验MIPI CSI Timing参数是否符合规范"

    def __init__(self, platform_context: PlatformContext):
        """初始化，绑定平台上下文"""

    def _run(self, timing_params: dict, sensor_spec: str = None) -> TimingCheckResult:
        """校验 Timing 参数"""

    def _calculate_hs_settle(self, clk_rate: int, data_rate: int) -> int:
        """计算 HS-SETTLE 推荐值 (平台相关计算方法)"""
```

### 2.10 Tools — 联网搜索工具 (tools/web_searcher.py)

**职责**: 联网搜索最新解决方案

```python
class WebSearcherTool(BaseTool):
    name: str = "web_search"
    description: str = "联网搜索Camera驱动问题的最新解决方案"

    def _run(self, query: str) -> list[SearchResult]:
        """搜索并返回结果摘要"""
```

### 2.11 Knowledge Base (knowledge/)

**职责**: 预置知识库的构建和管理，按子平台隔离

**知识库构建流程**:
1. 收集原始文档 (MD/PDF/TXT)
2. 使用 LangChain Document Loaders 加载
3. 文本分块 (RecursiveCharacterTextSplitter, chunk_size=1000, overlap=200)
4. 生成 Embedding (MiniMax Embedding / OpenAI Embeddings)
5. 存入对应子平台的 ChromaDB

**知识库目录结构**:

```
knowledge/
├── qualcomm/
│   ├── sm8550/
│   │   ├── platform_docs/
│   │   │   ├── camera_arch.md
│   │   │   ├── dts_reference.md
│   │   │   └── common_issues.md
│   │   ├── vectorstore/
│   │   └── projects/
│   │       ├── project_x/
│   │       └── project_y/
│   └── sm8650/
│       └── ...
├── mtk/
│   ├── mt6985/
│   │   ├── platform_docs/
│   │   │   ├── camera_arch.md
│   │   │   ├── sensor_bringup_guide.md
│   │   │   ├── dts_config_reference.md
│   │   │   ├── common_errors.md
│   │   │   └── mipi_timing_guide.md
│   │   ├── vectorstore/
│   │   └── projects/
│   │       ├── project_a/
│   │       ├── project_b/
│   │       └── project_c/
│   └── mt6989/
│       └── ...
└── unisoc/
    ├── t820/
    └── ...
```

### 2.12 API Layer (api/server.py)

**职责**: 提供 HTTP API 接口

```python
# FastAPI 接口定义

# 平台管理接口
GET  /api/v1/platforms/vendors
  - Response: list[Vendor]

GET  /api/v1/platforms/vendors/{vendor_id}/sub-platforms
  - Response: list[SubPlatform]

GET  /api/v1/platforms/sub-platforms/{sub_platform_id}/projects
  - Response: list[Project]

POST /api/v1/platforms/sub-platforms/{sub_platform_id}/projects
  - Body: { "name": str }
  - Response: Project

# 对话接口 (需先设置平台上下文)
POST /api/v1/sessions
  - Body: { "vendor_id": str, "sub_platform_id": str, "project_id": str }
  - Response: { "session_id": str }

POST /api/v1/sessions/{session_id}/chat
  - Body: { "message": str, "files": list[File] }
  - Response: AgentResponse

POST /api/v1/sessions/{session_id}/diagnose/log
  - Body: { "log_content": str }
  - Response: DiagnosisReport

POST /api/v1/sessions/{session_id}/review/dts
  - Body: { "dts_content": str }
  - Response: DTSReviewReport

GET  /api/v1/sessions/{session_id}
  - Response: ConversationHistory

DELETE /api/v1/sessions/{session_id}
  - Response: Success

# LLM 配置接口
GET  /api/v1/config/llm
  - Response: LLMConfig (隐藏 API Key)

PUT  /api/v1/config/llm
  - Body: LLMConfig
  - Response: Success
```

---

## 3. 技术选型

| 组件 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 语言 | Python | 3.11+ | AI 生态最完善 |
| Agent 框架 | LangChain | 0.3+ | 灵活编排，工具生态丰富 |
| LLM (默认) | MiniMax | MiniMax-Text-01 | 用户指定默认，中文能力强 |
| LLM (备选) | OpenAI / Anthropic / DeepSeek / Ollama | - | 可配置切换 |
| 向量数据库 | ChromaDB | 0.4+ | 轻量级，本地运行，支持多集合 |
| Embedding (默认) | MiniMax | embo-01 | 与默认 LLM 配套 |
| Web 框架 | FastAPI | 0.100+ | 异步支持好，自动生成文档 |
| 包管理 | uv / pip | - | 快速依赖管理 |

---

## 4. 项目结构

```
camera_driver_agent/
├── agent/
│   ├── __init__.py
│   ├── core.py              # CameraDriverAgent 主类
│   ├── prompts.py           # System Prompt & 模板 (平台感知)
│   └── memory.py            # 对话记忆 + 经验积累 (平台隔离)
├── platform/
│   ├── __init__.py
│   ├── manager.py           # 平台/项目管理器
│   ├── registry.py          # 平台注册表
│   └── context.py           # 平台上下文数据结构
├── tools/
│   ├── __init__.py
│   ├── log_analyzer.py      # 日志分析工具 (平台感知)
│   ├── dts_parser.py        # DTS 解析工具 (平台感知)
│   ├── knowledge_search.py  # 知识库检索工具 (平台路由)
│   ├── timing_checker.py    # Timing 校验工具 (平台感知)
│   ├── code_analyzer.py     # 代码分析工具
│   └── web_searcher.py      # 联网搜索工具
├── knowledge/
│   ├── qualcomm/            # 高通平台知识库
│   │   └── sm8550/
│   │       ├── platform_docs/
│   │       ├── vectorstore/
│   │       └── projects/
│   ├── mtk/                 # MTK平台知识库
│   │   └── mt6985/
│   │       ├── platform_docs/
│   │       ├── vectorstore/
│   │       └── projects/
│   ├── unisoc/              # 展锐平台知识库
│   │   └── t820/
│   └── builder.py           # 知识库构建脚本
├── models/
│   ├── __init__.py
│   └── schemas.py           # 数据模型定义
├── api/
│   ├── __init__.py
│   └── server.py            # FastAPI 服务
├── config/
│   ├── __init__.py
│   ├── settings.py          # 全局配置
│   └── llm_config.py        # LLM 配置与工厂
├── tests/
│   ├── test_agent.py
│   ├── test_platform_manager.py
│   ├── test_log_analyzer.py
│   ├── test_dts_parser.py
│   └── test_timing_checker.py
├── main.py                  # CLI 入口 (含平台选择)
├── pyproject.toml           # 项目配置
├── requirements.txt         # 依赖列表
├── .env.example             # 环境变量模板
├── .env                     # 环境变量 (git忽略)
└── docs/
    ├── product_definition.md
    ├── technical_design.md
    └── changelog.md
```

---

## 5. 关键流程

### 5.1 启动与平台选择流程

```
用户启动 Agent
    │
    ▼
加载 .env 配置 (LLM提供商等)
    │
    ▼
显示平台选择界面
    │
    ├── 选择一级平台 (高通/MTK/展锐)
    ├── 选择二级子平台 (如 MT6985)
    └── 选择/创建三级项目
    │
    ▼
PlatformManager.set_context()
    │
    ├── 加载子平台共享知识库
    ├── 加载项目私有知识库
    └── 生成平台相关的 System Prompt
    │
    ▼
Agent 就绪，开始对话
```

### 5.2 问题诊断流程

```
用户提问
    │
    ▼
Agent 接收消息 (携带平台上下文)
    │
    ▼
LLM 推理: 理解问题意图
    │
    ├── 需要日志分析? ──→ 调用 log_analyzer (平台感知)
    ├── 需要DTS审查?  ──→ 调用 dts_parser (平台感知)
    ├── 需要知识检索?  ──→ 调用 knowledge_search (路由到当前子平台知识库)
    ├── 需要Timing校验? ─→ 调用 timing_checker (平台感知)
    ├── 需要代码分析?  ──→ 调用 code_analyzer
    └── 需要联网搜索?  ──→ 调用 web_searcher
    │
    ▼
LLM 综合推理: 基于工具返回结果 + 平台上下文
    │
    ▼
生成诊断报告 (包含平台信息)
    │
    ▼
输出响应 + 保存经验到项目经验库
```

### 5.3 知识库构建流程

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
Embedding 生成 (MiniMax / OpenAI)
    │
    ▼
存入对应子平台的 ChromaDB Collection
(collection命名: {vendor}_{sub_platform}_platform / {vendor}_{sub_platform}_{project})
```

---

## 6. 依赖清单

```
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-anthropic>=0.2.0
langchain-community>=0.3.0
chromadb>=0.4.0
fastapi>=0.100.0
uvicorn>=0.24.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```
