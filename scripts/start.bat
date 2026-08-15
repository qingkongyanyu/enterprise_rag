@echo off
REM 一键启动后端服务（Windows）
cd /d %~dp0\..\backend

if not exist ..\data\vector_store\index.faiss (
  echo [init] 首次运行：初始化知识库索引...
  python scripts\init_knowledge.py --generate
)

echo [start] 启动服务: http://localhost:8000
python run.py
