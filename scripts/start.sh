#!/usr/bin/env bash
# 一键启动后端服务（Linux/macOS）
set -e
cd "$(dirname "$0")/../backend"

# 若索引未构建，自动初始化
if [ ! -f ../data/vector_store/index.faiss ]; then
  echo "🔧 首次运行：初始化知识库索引..."
  python scripts/init_knowledge.py --generate
fi

echo "🚀 启动服务: http://localhost:8000"
python run.py
