"""FastAPI 应用入口（工厂模式）。

- lifespan：启动时构建服务容器并尝试加载已持久化索引；关闭时清理缓存。
- 统一异常处理：业务异常 / 参数校验 / 未知异常 → {code, message, data}。
- 静态托管：直接托管 frontend/dist 构建产物（SPA），仅 Python 即可完整运行。
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.deps import ServiceRegistry, build_services
from app.api.routes import api_router
from app.core.config import FRONTEND_DIST_DIR
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


def create_app(services: Optional[ServiceRegistry] = None) -> FastAPI:
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动：构建服务容器（注入测试替身时可覆盖）
        app.state.services = services or build_services()
        if getattr(app.state.services, "knowledge", None) is not None:
            ready = app.state.services.knowledge.is_ready
            logger.info("🚀 服务启动完成 | 知识库索引就绪: %s", ready)
        else:
            logger.info("🚀 服务启动完成")
        yield
        # 关闭：清空进程内缓存
        if getattr(app.state.services, "pipeline", None) is not None:
            app.state.services.pipeline._cache.clear()
        logger.info("🛑 服务已关闭")

    app = FastAPI(
        title="企业私有知识库 RAG 智能问答系统",
        description="基于 混合检索（向量 + BM25）+ 大语言模型的私有知识库问答服务。",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    # ---------- CORS（开发模式允许跨域直连） ----------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- 统一异常处理 ----------
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        detail = exc.errors()
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": "参数校验失败", "data": detail},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        logger.exception("未捕获异常: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误，请查看日志", "data": None},
        )

    # ---------- 业务路由 ----------
    app.include_router(api_router)

    # ---------- 前端静态托管（SPA） ----------
    _mount_frontend(app)

    return app


def _mount_frontend(app: FastAPI) -> None:
    """挂载 frontend/dist：/assets 静态资源 + 其余路径回退 index.html。"""
    dist: Path = FRONTEND_DIST_DIR
    if not dist.exists() or not (dist / "index.html").exists():
        logger.warning("未找到前端构建产物 %s，将仅提供 API 服务", dist)
        return

    assets_dir = dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # API 路径不允许被 SPA 吞掉
        if full_path.startswith("api/"):
            return JSONResponse(
                status_code=404,
                content={"code": 404, "message": "接口不存在", "data": None},
            )
        target = dist / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(dist / "index.html")
