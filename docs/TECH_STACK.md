# 🧰 技术栈详解

> 版本：v2.0 · 更新日期：2026-08-17
> 逐项说明本项目用到的每一门技术：版本、在系统中的角色、选型理由与备选方案。
> 建议配合 [ARCHITECTURE.md](./ARCHITECTURE.md)（系统怎么拼）与 [RAG_OPTIMIZATION.md](./RAG_OPTIMIZATION.md)（检索怎么调）阅读。

---

## 1. 技术栈总览

| 分层 | 技术 | 版本 | 职责 |
|------|------|------|------|
| 语言 | Python | 3.10 - 3.13 | 后端全栈 |
| Web 框架 | FastAPI + Uvicorn | 0.136.3 / 0.48.0 | HTTP 服务、异步、SSE |
| 配置 | pydantic v2 + pydantic-settings | 2.13.4 / 2.14.2 | 类型安全的配置中心 |
| 大模型 | openai SDK + DashScope | 2.44.0 | LLM 对话 / 流式 / 异常映射 |
| 嵌入 | sentence-transformers | 5.7.0 | bge-small-zh 中文语义向量 |
| 向量检索 | FAISS（faiss-cpu） | 1.15.0 | IndexFlatIP 精确余弦检索 |
| 稀疏检索 | 自研 BM25（jieba + numpy） | jieba 0.42.1 / numpy 2.x | 字面关键词召回 |
| 重排 | bge-reranker（可选） | - | 交叉编码器精排，默认关闭 |
| 持久化 | 文件型（FAISS 索引 + JSON） | 标准库 | 索引 / 会话记忆 / 嵌入缓存 |
| 前端框架 | Vue 3 + Vite + TypeScript | 3.5.13 / 6.0.7 / 5.7 | SPA + 构建 + 类型安全 |
| 状态/路由 | Pinia / Vue Router | 2.3 / 4.5 | 全局状态 / 路由 |
| 渲染 | marked + highlight.js | 15.x / 11.x | Markdown + 代码高亮 |

---

## 2. 后端技术

### 2.1 Web 框架：FastAPI + Uvicorn

- **选型**：异步、Pydantic 原生校验、自动生成 OpenAPI/Swagger、SSE 流式支持好。
- **SSE**：`/api/v1/chat/stream` 用同步生成器 + `StreamingResponse` 逐 token 输出，
  Starlette 自动放入线程池迭代，不阻塞事件循环。
- **备选**：Flask（异步与文档能力弱）；Django（过重，与项目规模不匹配）。

### 2.2 配置中心：pydantic-settings + .env

- 全部可调参数集中在 `app/core/config.py`，通过 `backend/.env` / 环境变量注入；
- 密钥（`LLM_API_KEY`）仅存 `.env`（已 gitignore），**绝不硬编码**。

### 2.3 大模型：openai 官方 SDK + OpenAI 兼容抽象

- `services/llm.py` 用 `openai.OpenAI(base_url=...)` 统一调用，**改 base_url 一行切换**服务商：
  DashScope（默认） / OpenAI / Ollama / 火山方舟；
- SDK 内置流式增量、超时、自动重试；业务层只保留**异常分类映射**（鉴权/超时/断连/业务状态码）；
- **为什么不手写 HTTP/SSE**：SDK 更稳、少一套 `requests` + SSE 解析的维护成本。

### 2.4 嵌入模型：sentence-transformers + bge-small-zh

- 中文检索专用双塔模型，**512 维**，约 100MB，CPU 可跑；
- 查询侧加 BGE 指令前缀；**磁盘缓存**（md5 为 key）：重建索引从 52s 降到 <1s；
- 模型下载走国内镜像 `hf-mirror.com`（`HF_ENDPOINT` 可覆盖）。

### 2.5 向量检索：FAISS（IndexFlatIP）

- 向量 L2 归一化后内积 = 余弦相似度，`IndexFlatIP` 精确索引一次搞定；
- **索引常驻内存**（lifespan 单例 + 懒加载），检索零加载开销；
- 索引 + chunk 元数据**落盘**，重启即恢复；
- 热切换：重建时先构建新 retriever，锁内原子替换，不中断问答。

### 2.6 稀疏检索：自研 BM25（jieba + numpy）

- 经典 BM25 公式（`k1=1.5, b=0.75`），jieba 精确模式分词；
- 约 40 行自实现，numpy 向量化打分；
- **为什么自研**：零额外依赖、完全可控、可单测、可讲清公式。

### 2.7 重排：bge-reranker（可选）

- 交叉编码器，对 (query, doc) 联合编码打分，精度更高；
- 默认关闭（CPU 友好），`ENABLE_RERANK=true` 开启；失败自动降级不阻塞主链路。

### 2.8 持久化：文件型存储

| 数据 | 存储 | 说明 |
|------|------|------|
| 向量索引 | FAISS `.index` + chunk 元数据 JSON | `data/vector_store/` |
| 会话记忆 | JSON（每会话一文件） | `data/chat_memory/` |
| 嵌入缓存 | pickle 缓存 | `data/embedding_cache/`（md5 key） |

零运维、备份简单；规模上来后可平滑迁移 Milvus / PostgreSQL。

---

## 3. 前端技术

### 3.1 Vue 3 + TypeScript + Vite

- Composition API + `<script setup>` + **TypeScript** 类型安全；
- Vite 6 开发热更新，构建产物 `dist/` 由后端 FastAPI 托管（SPA 回退），单端口部署。

### 3.2 Pinia + Vue Router

- Pinia：聊天 / 知识库 / 系统状态三个 store；
- Router：智能问答 / 知识库管理 / 系统状态三个视图。

### 3.3 网络层：Axios + fetch(SSE)

- Axios 统一 `{code, message, data}` 响应包裹与错误拦截；
- 流式走 fetch + ReadableStream 手写 SSE 解析，支持「停止生成」。

### 3.4 渲染：marked + highlight.js

- 回答以 Markdown 渲染，代码块用 highlight.js 高亮；
- 关闭 HTML 渲染防 XSS。

### 3.5 设计系统

- CSS 变量令牌驱动深色科技风：玻璃拟态面板、渐变光效、来源引用卡片、流式打字动画。

---

## 4. 一次问答背后的技术流

```
浏览器提问
  └─ Vue3 组件 → Pinia store
       └─ fetch SSE POST /api/v1/chat/stream
            └─ FastAPI 路由（Pydantic 校验）
                 └─ RAGPipeline 编排
                      ├─ 读会话记忆（JSON）
                      ├─ 混合检索
                      │    ├─ bge 嵌入 → FAISS 余弦召回（Dense）
                      │    └─ jieba + BM25 关键词召回（Sparse）
                      ├─ RRF 融合 →（可选）bge-reranker 重排
                      ├─ 组装 Prompt（系统提示 + 历史 + 编号知识）
                      └─ openai SDK 流式生成 → StreamingResponse SSE
                           └─ Vue 打字机效果 + marked 渲染 + 来源卡片
```

---

## 5. 工程与质量设施

| 设施 | 技术 | 说明 |
|------|------|------|
| 单元测试 | pytest | 27 个用例：分块 / BM25 / 混合检索 / API（离线可跑） |
| 日志 | logging | 统一格式 + Windows 控制台 UTF-8 兜底 |
| 一键启动 | `scripts/start.bat` / `run.py` | 装依赖 / 建索引 / 启动 / 开浏览器 |
| 部署 | Docker + docker-compose | 见 [DEPLOYMENT.md](./DEPLOYMENT.md) |
| 开发 | `requirements-dev.txt` | 见 [DEVELOPMENT.md](./DEVELOPMENT.md) |

---

## 6. 关键选型对比（面试高频）

| 场景 | 本方案 | 常见备选 | 取舍 |
|------|--------|----------|------|
| 检索框架 | 全自研 | LangChain / LlamaIndex | 可讲清细节、无版本断裂；牺牲生态便利 |
| 向量库 | FAISS | Milvus / PGVector | 零运维、够快；规模大了再换 |
| 融合 | RRF | 加权求和 | 对分数尺度不敏感、无需调权 |
| 嵌入模型 | bge-small-zh | text2vec / m3e / OpenAI ada | 中文效果好、体积小、本地免调用费 |
| LLM 调用 | openai SDK | langchain_openai / 手写 HTTP | SDK 内置重试流式；不用 LangChain 保可控 |
| 前端 | Vue3 + TS + Vite | React + Webpack | 类型安全、构建快、与 FastAPI 同栈 |
