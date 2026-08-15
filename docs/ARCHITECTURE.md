# 系统架构

## 一、整体设计

本系统是典型的两层 Web 架构 + RAG 检索管线：

- **前端**（`frontend/`）：Vue 3 SPA，负责交互与展示。构建产物 `dist/` 由后端直接托管，也可在开发模式独立运行（Vite 热更新 + 代理）。
- **后端**（`backend/`）：FastAPI 单体服务，提供 REST + SSE 接口，内部按「路由层 → 服务层 → 基础设施」分层。

```
┌─────────────┐   HTTP / SSE    ┌───────────────────────────────┐
│  Vue 3 SPA  │ ──────────────▶ │  FastAPI                      │
│  智能问答     │                 │  api/routes/*                 │
│  知识库管理   │ ◀────────────── │  core/ (config/log/exception) │
│  系统状态     │   JSON 流式     │  services/*                   │
└─────────────┘                 └───────────────┬───────────────┘
                                                │
                        ┌───────────────────────┼───────────────────────┐
                        ▼                       ▼                       ▼
                 ┌────────────┐        ┌──────────────┐        ┌──────────────┐
                 │  FAISS     │        │  BM25        │        │  LLM         │
                 │  向量索引   │        │  稀疏索引     │        │  Provider    │
                 │  IndexFlatIP│       │  jieba 分词  │        │  DashScope /  │
                 │  + 磁盘持久化│       │              │        │  OpenAI /     │
                 └────────────┘        └──────────────┘        │  Ollama       │
                                                               └──────────────┘
```

## 二、后端模块职责

### 路由层 `app/api/routes/`

| 路由 | 前缀 | 职责 |
| --- | --- | --- |
| `chat.py` | `/api/v1/chat` | 非流式问答 + SSE 流式问答 |
| `knowledge.py` | `/api/v1/knowledge` | 文档枚举、构建索引、上传、删除 |
| `sessions.py` | `/api/v1/sessions` | 会话列表、历史、删除 |
| `system.py` | `/api/v1/system` | 系统状态、运行指标；`/health` 探针 |

路由层只做「参数绑定 + 调用服务 + 统一响应」，不含业务逻辑。

### 服务层 `app/services/`（RAG 全链路）

```
document_loader → chunking → embeddings → vector_store + bm25
                                     ↓
                                retriever（混合检索 + RRF）
                                     ↓
                          pipeline（编排：检索→上下文→LLM→记忆→缓存）
```

| 模块 | 职责 | 关键点 |
| --- | --- | --- |
| `document_loader` | 读取/枚举/新增/删除文档 | utf-8/gbk 双编码容错；防路径穿越 |
| `chunking` | 文档分块 | 中文句读边界感知 + overlap 窗口 + 空块过滤 |
| `embeddings` | 文本向量化 | bge-small-zh；查询侧指令前缀；**磁盘缓存**避免重复计算 |
| `vector_store` | FAISS 向量库 | IndexFlatIP（余弦）；索引+chunk 元数据落盘；**常驻内存** |
| `bm25` | 稀疏检索 | 自实现经典 BM25（k1=1.5, b=0.75）+ jieba 中文分词 |
| `retriever` | 混合检索 | 稠密 topK + 稀疏 topK → **RRF 融合** → 可选重排 |
| `reranker` | 交叉编码器重排 | bge-reranker，默认关闭（CPU 友好），可按需开启 |
| `llm` | LLM 调用 | OpenAI 兼容抽象，支持流式；异常分类映射 |
| `memory` | 会话记忆 | JSON 持久化；最近 N 轮注入；会话管理 |
| `knowledge` | 知识库门面 | 索引构建/加载/热切换；文档增删联动 |
| `pipeline` | RAG 编排 | 检索 → 上下文组装 → Prompt → LLM → 记忆 → 响应缓存 |

### 核心 `app/core/`

- `config.py`：pydantic-settings 统一配置，支持 `.env` 覆盖，**密钥不落代码**。
- `logging.py`：统一日志格式；Windows 控制台 UTF-8 兜底。
- `exceptions.py`：业务异常体系，由 FastAPI 统一转成 `{code, message, data}`。

## 三、关键设计决策

### 1. 为什么不用 LangChain？

LangChain 功能全但版本断裂频繁、内部实现黑盒、排查成本高。本项目**核心检索与编排全部自实现**：

- 向量库：直接使用原生 `faiss`（`IndexFlatIP` + 归一化向量 = 余弦相似度）
- 稀疏检索：经典 BM25 约 40 行自实现，完全可控
- 编排：`RAGPipeline` 一个类串起全流程，单元测试可完全 mock

收益：代码清晰可读、测试覆盖全面、面试可讲清每个细节；同时规避了 LangChain 1.x 大量 breaking change。

### 2. 单例常驻 + 懒加载

`KnowledgeBase`、`EmbeddingService`、`LLMClient` 都在应用 `lifespan` 中构建一次，常驻内存：

- 向量索引**只加载一次**，后续请求零加载开销
- 嵌入模型懒加载（首次检索才加载），启动秒级
- 旧版每次请求重新 `load_local` FAISS 的性能问题彻底解决

### 3. 线程安全的热切换

重建索引时先构建新 `retriever`，再在锁内原子替换引用——旧检索器在重建期间仍可继续服务，不会中断问答。

### 4. 统一响应与异常

所有接口返回 `{code, message, data}`。业务异常通过 `AppError` 体系 + 统一 `exception_handler` 映射，前端拿到 `code` 即可友好提示，服务端异常不会裸奔。

### 5. SSE 流式

`/api/v1/chat/stream` 按 SSE 协议逐 token 输出 `{type: delta, text}` 事件，结束时输出 `sources` 与 `done`。Starlette 将同步生成器放入线程池迭代，不阻塞事件循环。
