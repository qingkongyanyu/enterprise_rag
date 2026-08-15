"""知识库管理接口：文档枚举、构建索引、上传、删除。"""
from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile

from app.api.deps import get_services
from app.core.exceptions import ValidationError
from app.models.schemas import ApiResponse, KnowledgeOverview, RebuildResult
from app.services.document_loader import is_supported, list_docs

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/documents", response_model=ApiResponse[KnowledgeOverview], summary="知识库概览")
def get_documents(request: Request):
    """文档列表 + 分类统计 + 索引状态。"""
    services = get_services(request)
    return ApiResponse.success(services.knowledge.overview())


@router.post("/rebuild", response_model=ApiResponse[RebuildResult], summary="构建/重建索引")
def rebuild(request: Request):
    """全量重建向量索引（带嵌入缓存，重复构建很快）。"""
    services = get_services(request)
    result = services.knowledge.rebuild()
    return ApiResponse.success(result, message="索引构建成功")


@router.post("/upload", summary="上传文档")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """上传知识文档（.txt / .md），成功后自动重建索引。"""
    services = get_services(request)
    filename = (file.filename or "").strip()
    if not filename or not is_supported(filename):
        raise ValidationError("仅支持 .txt / .md 格式的文件")
    content = await file.read()
    result = services.knowledge.upload_document(filename, content)
    return ApiResponse.success(result, message="文档上传成功并已重建索引")


@router.delete("/documents/{filename}", summary="删除文档")
def delete_document(filename: str, request: Request):
    """删除文档并同步重建索引。"""
    services = get_services(request)
    services.knowledge.delete_document(filename)
    return ApiResponse.success({"name": filename}, message="文档已删除")
