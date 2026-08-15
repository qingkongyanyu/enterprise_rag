# 部署指南

支持两种部署方式：**Docker 一键部署** 与 **手动部署**。环境要求见下表。

## 环境要求

| 依赖 | Docker 方式 | 手动方式 |
| --- | --- | --- |
| Docker | 20.10+（含 docker compose v2） | - |
| Python | - | 3.10 - 3.13 |
| Node.js | - | 18+（仅前端开发/重新构建时需要） |

> 首次运行需要联网下载嵌入模型 `BAAI/bge-small-zh`（约 100MB）。国内网络已默认走 `hf-mirror.com` 镜像。

## 一、Docker 部署

### 1. 准备密钥

```bash
cp .env.example backend/.env
# 编辑 backend/.env，把 LLM_API_KEY 换成真实 Key
```

### 2. 构建并启动

```bash
docker compose up --build
```

- 首次启动会自动：生成示例文档 → 下载嵌入模型 → 构建向量索引（可能耗时几分钟）。
- 数据保存在命名卷 `rag_data`，重启不丢失、不重复构建。
- 访问 http://localhost:8000

### 3. 常用命令

```bash
docker compose down        # 停止
docker compose logs -f     # 查看日志
docker compose up -d       # 后台运行
```

## 二、手动部署

### 1. 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp ../.env.example .env
```

`.env` 关键项：

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_API_KEY` | API Key | `sk-xxx` |
| `LLM_MODEL` | 模型名 | `qwen-turbo` |
| `EMBEDDING_MODEL` | 嵌入模型 | `BAAI/bge-small-zh` |

支持的服务商（仅需改 `LLM_BASE_URL` + `LLM_MODEL`）：

| 服务商 | base_url | 模型示例 |
| --- | --- | --- |
| 阿里云百炼（通义千问） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` |
| 火山方舟（豆包） | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-pro-32k` |

### 3. 初始化知识库

```bash
# 生成 20 篇示例文档并构建索引
python scripts/init_knowledge.py --generate
```

若已有自定义文档，直接放入 `../data/knowledge_docs/`（支持 .txt/.md），再执行：
```bash
python scripts/init_knowledge.py
```

### 4. 启动后端

```bash
python run.py
# 访问 http://localhost:8000
# API 文档 http://localhost:8000/api/docs
```

### 5. （可选）前端开发模式

仓库已提交构建产物 `frontend/dist/`，手动部署后端即可直接用，无需 Node。如需改前端代码热更新：

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173，/api 已自动代理到 8000
```

重新构建生产产物：
```bash
npm run build
# 产物输出到 frontend/dist/，由后端自动托管
```

## 三、生产部署建议

- **反向代理**：用 Nginx / Caddy 给 8000 端口加 HTTPS，SSE 流式请关闭代理缓冲（本服务已返回 `X-Accel-Buffering: no`）。
- **密钥管理**：生产环境建议把密钥放环境变量或密钥管理服务，而不是 `.env` 文件。
- **模型预下载**：可把 `data/embedding_cache` 与向量索引一同备份，避免每次初始化重下载/重计算。
- **后台运行**：用 `systemd` / `pm2` / supervisor 托管 `python run.py`。

## 四、常见问题

**Q：启动时提示「知识库索引未构建」？**
A：执行 `cd backend && python scripts/init_knowledge.py --generate`，或在「知识库」页面点「构建索引」。

**Q：问答返回 503「大模型服务未配置」？**
A：检查 `backend/.env` 是否已填写 `LLM_API_KEY`，且 `LLM_BASE_URL` / `LLM_MODEL` 与所购服务匹配。

**Q：首次下载嵌入模型很慢 / 失败？**
A：国内已默认走 `hf-mirror.com`；也可手动设置 `export HF_ENDPOINT=https://hf-mirror.com`。
