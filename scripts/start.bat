@echo off
setlocal enabledelayedexpansion
title 知知 RAG 一键启动
cd /d "%~dp0\..\backend"

echo ============================================================
echo   知知 - 企业私有知识库 RAG 智能问答系统
echo   一键启动脚本 (Windows)
echo ============================================================
echo.

REM ---------- 1. 检测 Python ----------
set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+ 并勾选 "Add to PATH"
    pause
    exit /b 1
)
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo [环境] %%v

REM ---------- 2. 检查依赖 ----------
%PY% -c "import fastapi, uvicorn, faiss, pydantic_settings, openai, jieba, sentence_transformers" >nul 2>&1
if errorlevel 1 (
    echo [安装] 检测到缺少依赖，正在安装（首次需数分钟，请耐心等待）...
    %PY% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [重试] 镜像源安装失败，改用官方源重试...
        %PY% -m pip install -r requirements.txt
    )
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络后重试，或手动执行：
        echo        pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo [完成] 依赖安装完成
) else (
    echo [环境] 依赖已就绪
)

REM ---------- 3. 检查 .env 配置 ----------
if not exist ".env" (
    echo.
    echo [配置] 未找到 backend\.env，正在从模板创建...
    copy /y "..\.env.example" ".env" >nul
    echo [配置] 已生成 backend\.env
    echo.
    echo  [提示] 请编辑 backend\.env，将 LLM_API_KEY 改为你的真实密钥
    echo         （阿里云百炼 DashScope 获取：https://bailian.console.aliyun.com/）
    echo         也可以直接启动，界面会提示 LLM 未配置
    echo.
    choice /c YN /m "是否现在打开 .env 编辑（推荐选 Y）？"
    if errorlevel 2 goto skip_env_edit
    notepad ".env"
    :skip_env_edit
    echo.
) else (
    echo [配置] .env 已存在
)

REM ---------- 4. 初始化知识库索引 ----------
if not exist "..\data\vector_store\index.faiss" (
    echo.
    echo [初始化] 首次运行，正在生成示例文档并构建索引（首次需下载嵌入模型，可能较慢）...
    %PY% scripts\init_knowledge.py --generate
    if errorlevel 1 (
        echo [错误] 知识库初始化失败，请查看上方日志
        pause
        exit /b 1
    )
) else (
    echo [初始化] 知识库索引已存在，跳过
)

REM ---------- 5. 端口占用检测 ----------
set "PORT=8001"
set "BUSY="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do set "BUSY=%%p"
if defined BUSY (
    echo.
    echo [警告] 端口 8001 已被进程 PID=%BUSY% 占用
    echo        正在尝试用 8002 端口启动...
    set "PORT=8002"
)

echo.
echo ============================================================
echo   正在启动服务...
echo   访问地址: http://127.0.0.1:!PORT!
echo   关闭本窗口即停止服务
echo ============================================================
echo.

REM ---------- 6. 启动并自动打开浏览器 ----------
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://127.0.0.1:!PORT!"
%PY% run.py --port !PORT! --no-browser

endlocal
