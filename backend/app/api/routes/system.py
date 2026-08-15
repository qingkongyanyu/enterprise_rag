"""系统状态与指标接口。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app import __version__
from app.api.deps import get_services
from app.core.config import VECTOR_STORE_DIR, KNOWLEDGE_DOCS_DIR
from app.models.schemas import ApiResponse, SystemStats

router = APIRouter(tags=["system"])


@router.get("/health", summary="健康检查")
def health():
    """存活探针。"""
    return {"status": "healthy", "service": "enterprise_rag", "version": __version__}


@router.get("/api/v1/system/stats", response_model=ApiResponse[SystemStats], summary="系统状态")
def system_stats(request: Request):
    """运行状态：索引、模型、配置摘要（脱敏，不含密钥）。"""
    services = get_services(request)
    s = services.settings
    overview = services.knowledge.overview()
    return ApiResponse.success(
        SystemStats(
            app_version=__version__,
            index_ready=overview.ready,
            doc_count=overview.total_docs,
            chunk_count=overview.total_chunks,
            embedding_model=s.embedding_model,
            llm_configured=s.llm_configured,
            llm_base_url=s.llm_base_url,
            llm_model=s.llm_model,
            final_top_k=s.final_top_k,
            enable_rerank=s.enable_rerank,
            vector_store_dir=str(VECTOR_STORE_DIR),
            knowledge_docs_dir=str(KNOWLEDGE_DOCS_DIR),
        )
    )


@router.get("/api/v1/system/metrics", summary="运行指标")
def system_metrics(request: Request):
    """服务侧性能指标（对话次数、平均耗时、缓存命中）。"""
    services = get_services(request)
    return ApiResponse.success(services.pipeline.get_metrics())
