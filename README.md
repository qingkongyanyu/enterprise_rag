<div align="center">

# 📚 知知 · 企业私有知识库 RAG 智能问答系统

**基于混合检索（向量 + BM25）+ 大语言模型的企业私有知识库问答平台**

`FastAPI` · `Vue 3` · `FAISS` · `sentence-transformers` · `OpenAI 兼容 LLM`

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![RAG](https://img.shields.io/badge/RAG-Hybrid%20Retrieval-818cf8)

</div>

> 把企业制度、流程、产品文档「喂」给 AI，员工用自然语言提问，秒得带引用来源的精准答案。
> 支持私有化部署，数据不出内网，完全可控。

---

## ✨ 功能亮点

| 能力 | 说明 |
| --- | --- |
| 🔍 **混合检索** | 稠密向量（FAISS 余弦）+ 稀疏检索（BM25）倒数排名融合（RRF），兼顾语义与精确词匹配 |
| 🧩 **智能分块** | 中文句读边界感知的递归分块 + 重叠窗口，避免语义切碎 |
| 💬 **流式问答** | SSE 逐字输出，打字机效果，可中途停止 |
| 📎 **引用溯源** | 每条回答都带来源文件与匹配度，支持点击查看命中片段 |
| 🧠 **多轮对话** | 会话级记忆注入，支持上下文追问 |
| 📂 **知识库管理** | 可视化上传 / 删除文档、一键构建索引、分类统计 |
| ⚡ **性能优化** | 索引常驻内存、嵌入磁盘缓存、响应命中缓存，平均请求耗时显著降低 |
| 🔒 **密钥安全** | LLM 密钥仅存于 `.env`，绝不入库，换服务商只需改一行配置 |
| 🐳 **一键部署** | `docker compose up` 即可运行；也支持纯 Python 手动部署 |

## 🧰 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI · Uvicorn · pydantic v2 · **openai SDK**（兼容接口） |
| 嵌入/检索 | sentence-transformers（bge-small-zh）· FAISS · 自研 BM25（jieba+numpy）· bge-reranker（可选） |
| 持久化 | 文件型（FAISS 索引 + JSON 会话记忆） |
| 前端 | Vue 3 · TypeScript · Vite · Pinia · Vue Router · marked + highlight.js |
| LLM | OpenAI 兼容抽象（openai 官方 SDK），默认通义千问，可切换 OpenAI / Ollama / 火山方舟 |

> 每项技术的**版本、职责、选型理由与备选对比**详见 [docs/TECH_STACK.md](docs/TECH_STACK.md)。

## 🏗️ 系统架构

```
┌───────────────────────────────────────────────────────────┐
│                        浏览器（Vue 3 SPA）                 │
│   智能问答 · 知识库管理 · 系统状态                           │
└───────────────────────────┬───────────────────────────────┘
                            │  REST / SSE
┌───────────────────────────▼───────────────────────────────┐
│                      FastAPI 服务层                        │
│  /api/v1/chat · /chat/stream · /knowledge · /sessions ...  │
└──────────┬──────────────────────────┬──────────────────────┘
           │                          │
   ┌───────▼────────┐        ┌────────▼───────┐
   │   检索流水线     │        │   RAG 编排      │
   │                 │        │                 │
   │ 文档 → 分块      │        │ 检索 → 组装上下文 │
   │ → 嵌入（带缓存）  │        │ → LLM → 引用溯源  │
   │ → FAISS + BM25  │        │ → 会话记忆/缓存   │
   │ → RRF 融合      │        │                 │
   └─────────────────┘        └────────┬────────┘
                                       │
                            ┌──────────▼──────────┐
                            │  LLM  Provider 抽象   │
                            │  DashScope / OpenAI  │
                            │  / Ollama / Volcengine│
                            └─────────────────────┘
```

## 🚀 快速开始

### 方式零：Windows 一键启动（推荐）

```bash
# 1. 准备环境变量
cp .env.example backend/.env
#    编辑 backend/.env，填入真实的 LLM_API_KEY（获取：https://bailian.console.aliyun.com/）

# 2. 双击运行（自动装依赖 / 初始化索引 / 启动服务 / 打开浏览器）
scripts\start.bat
```

脚本会自动完成：检测 Python → 安装缺失依赖 → 引导配置 `.env` → 生成示例文档并构建索引 → 端口占用检测 → 启动服务并自动打开 `http://127.0.0.1:8001`。

### 方式一：Docker（零门槛）

```bash
# 1. 准备环境变量
cp .env.example backend/.env
#    编辑 backend/.env，填入真实的 LLM_API_KEY

# 2. 一键启动（首次需下载嵌入模型，耗时较长）
docker compose up --build
```

访问 http://localhost:8001

### 方式二：纯 Python + Node（本地开发）

```bash
# 1. 后端
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp ../.env.example .env                          # 填写 LLM_API_KEY
python scripts/init_knowledge.py --generate      # 生成示例文档 + 构建索引
python run.py                                    # http://localhost:8001

# 2. 前端（可选，开发模式热更新）
cd frontend
npm install
npm run dev                                      # http://localhost:5173
```

### 方式三：仅 Python（使用已构建的前端）

```bash
cd backend
pip install -r requirements.txt
python scripts/init_knowledge.py --generate
python run.py
# 前端 dist 已随仓库提交，FastAPI 直接托管，无需安装 Node
```

> ⚠️ 运行后请访问 **http://127.0.0.1:8001**（脚本会自动打开）。不要用 `0.0.0.0` 访问——那是监听地址，浏览器打不开。
> ⚠️ 若端口 8001 被占用，`start.bat` 会自动改用 8002；也可手动 `python run.py --port 9000` 指定端口。

## 📸 界面预览

> 深色科技风 UI：玻璃拟态面板 · 渐变光效 · 流式打字动画 · 来源引用卡片

```
┌─────────────┬────────────────────────────────────────┐
│   知知       │  ◉ 知知 · 企业知识库智能问答      [+新对话]│
│  Enterprise │                                        │
│  RAG        │  你好，我是 知知                        │
│             │  企业私有知识库智能助手                    │
│  ▸ 智能问答  │  ┌──────────────────────────────────┐  │
│  ▸ 知识库    │  │员工请假流程是什么？                 │  │
│  ▸ 系统状态  │  └──────────────────────────────────┘  │
│             │  员工请假流程如下：[1]                    │
│  系统状态    │  ① 填写《请假申请单》...                 │
│  ● 索引就绪  │  ② 直属领导审批...                      │
│  ● LLM 已配  │  ── 引用来源 ──  #1 人事_04.txt 100%   │
└─────────────┴────────────────────────────────────────┘
```

## 📁 项目结构

```
enterprise_rag/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由层（chat / knowledge / sessions / system）
│   │   ├── core/            # 配置 / 日志 / 异常
│   │   ├── services/        # RAG 全链路（嵌入 / 分块 / 检索 / 记忆 / 编排）
│   │   └── utils/           # 文本 / 缓存工具
│   ├── scripts/             # init_knowledge / generate_sample_docs
│   └── tests/               # pytest 单元测试
├── frontend/                # Vue 3 前端（含已构建的 dist/）
│   └── src/
│       ├── views/           # 智能问答 / 知识库 / 系统状态
│       ├── components/      # 布局与聊天组件
│       ├── stores/          # Pinia 状态管理
│       └── api/             # 请求封装 + SSE 流式解析
├── data/                    # 运行期数据（文档 / 索引 / 会话）
├── docs/                    # 项目文档（架构 / API / 部署 / RAG 调优）
├── Dockerfile / docker-compose.yml
└── .env.example
```

## 📚 文档导航

| 文档 | 内容 |
| --- | --- |
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | 技术栈详解：每项技术的版本、职责、选型理由与备选对比 |
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | 项目介绍、难点与解决方案（面试用） |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构与模块职责 |
| [docs/RAG_OPTIMIZATION.md](docs/RAG_OPTIMIZATION.md) | RAG 调优实践与原理 |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | 全部接口文档（含 curl 示例） |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Docker / 手动部署指南 |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 本地开发与测试指南 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南（开发 / 规范 / PR 流程） |
| [SECURITY.md](SECURITY.md) | 安全策略与漏洞报告 |

## 🧪 测试

```bash
cd backend
python -m pytest tests/ -v    # 27 个用例：分块 / BM25 / 混合检索 / API
```

## ❓ 常见问题

**Q：启动后浏览器打不开 / 白屏？**
A：① 访问地址用 `http://127.0.0.1:8001`，不要用 `http://0.0.0.0:8001`（监听地址，浏览器无法访问）；② 检查端口是否被其他程序占用（`start.bat` 会自动检测并切换 8002）；③ 确认启动日志出现 `Uvicorn running on`，且控制台输出 `访问地址`。

**Q：提示「大模型服务未配置 / 503」？**
A：编辑 `backend/.env`，确认 `LLM_API_KEY` 已填入真实密钥且 `LLM_BASE_URL` / `LLM_MODEL` 与服务商匹配。

**Q：首次启动下载嵌入模型很慢？**
A：国内已默认走 `hf-mirror.com` 镜像；也可在 `.env` 中设置 `HF_ENDPOINT`。

**Q：想用自己的文档？**
A：把 .txt/.md 文件放入 `data/knowledge_docs/`，然后在「知识库」页面点击「构建索引」，或运行 `python scripts/init_knowledge.py`。

## ⚖️ License

[MIT](LICENSE) © 2026
