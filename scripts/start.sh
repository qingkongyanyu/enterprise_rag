#!/usr/bin/env bash
# 一键启动后端服务（Linux/macOS）
# 用法：bash scripts/start.sh
set -e
cd "$(dirname "$0")/../backend"

PY="${PYTHON:-python3}"

echo "============================================================"
echo "  📘 知知 · 企业私有知识库 RAG 智能问答系统"
echo "  一键启动脚本 (Linux/macOS)"
echo "============================================================"
echo

# 1. 检查 Python
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi
echo "[环境] $($PY --version)"

# 2. 检查依赖
if ! $PY -c "import fastapi, uvicorn, faiss, pydantic_settings, openai, jieba, sentence_transformers" >/dev/null 2>&1; then
    echo "[安装] 检测到缺少依赖，正在安装（首次需数分钟）..."
    $PY -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || $PY -m pip install -r requirements.txt
    echo "[完成] 依赖安装完成"
else
    echo "[环境] 依赖已就绪"
fi

# 3. 检查 .env 配置
if [ ! -f ".env" ]; then
    echo
    echo "[配置] 未找到 backend/.env，正在从模板创建..."
    cp ../.env.example .env
    echo "[配置] 已生成 backend/.env，请编辑并填入真实 LLM_API_KEY"
    echo "       （也可直接启动，界面会提示 LLM 未配置）"
    echo
fi

# 4. 初始化知识库索引
if [ ! -f ../data/vector_store/index.faiss ]; then
    echo "[初始化] 首次运行，正在生成示例文档并构建索引（首次需下载嵌入模型）..."
    $PY scripts/init_knowledge.py --generate
fi

# 5. 端口占用检测
PORT="${PORT:-8001}"
if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[警告] 端口 $PORT 已被占用，改用 8002"
    PORT=8002
fi

echo
echo "============================================================"
echo "  🚀 启动服务中..."
echo "  访问地址: http://127.0.0.1:$PORT"
echo "============================================================"
echo

# 6. 启动并自动打开浏览器
(sleep 4 && (xdg-open "http://127.0.0.1:$PORT" || open "http://127.0.0.1:$PORT")) >/dev/null 2>&1 &
exec $PY run.py --port "$PORT" --no-browser
