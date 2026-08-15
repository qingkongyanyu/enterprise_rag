"""会话管理接口。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request

from app.api.deps import get_services
from app.models.schemas import ApiResponse, HistoryData

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", summary="会话列表")
def list_sessions(request: Request):
    """按最后活跃时间倒序返回所有会话摘要。"""
    services = get_services(request)
    return ApiResponse.success(services.memory.list_sessions())


@router.get("/{session_id}/history", response_model=ApiResponse[HistoryData], summary="会话历史")
def get_history(session_id: str, request: Request):
    services = get_services(request)
    history = services.memory.get_history(session_id)
    return ApiResponse.success(HistoryData(session_id=session_id, history=history))


@router.delete("/{session_id}", summary="删除会话")
def delete_session(session_id: str, request: Request):
    services = get_services(request)
    ok = services.memory.delete_session(session_id)
    return ApiResponse.success(
        {"deleted": ok, "session_id": session_id},
        message="会话已删除" if ok else "会话不存在",
    )


@router.delete("", summary="清空全部会话")
def clear_all_sessions(request: Request):
    services = get_services(request)
    n = services.memory.clear_all()
    return ApiResponse.success({"deleted": n}, message=f"已清空 {n} 个会话")
