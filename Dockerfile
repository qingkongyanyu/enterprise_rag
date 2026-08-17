# ============================================================
# enterprise_rag 一键镜像（多阶段构建）
#   Stage 1: Node 构建前端 → dist
#   Stage 2: Python 运行后端，托管 dist
# 构建：docker build -t enterprise-rag .
# 运行：docker compose up
# ============================================================

# ---------- Stage 1: 前端构建 ----------
FROM node:20-alpine AS frontend-build
WORKDIR /app
# 国内可换 npmmirror 源加速
ARG NPM_REGISTRY=https://registry.npmjs.org
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --registry=$NPM_REGISTRY
COPY frontend/ .
RUN npm run build

# ---------- Stage 2: 后端运行 ----------
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_ENDPOINT=https://hf-mirror.com

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 系统依赖（faiss/模型运行所需最小集）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 后端依赖
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --index-url $PIP_INDEX_URL -r backend/requirements.txt

# 后端源码 + 前端构建产物
COPY backend/ ./backend/
COPY --from=frontend-build /app/dist ./frontend/dist

# 运行期数据目录
RUN mkdir -p /app/data

WORKDIR /app/backend

EXPOSE 8001

# 启动：首次运行自动生成示例文档并构建索引（模型下载较慢），随后启动服务
CMD ["sh", "-c", "python scripts/init_knowledge.py --generate; exec python run.py --port 8001"]
