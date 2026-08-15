"""对话相关接口：非流式问答 + SSE 流式问答。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_services
from app.models.schemas import ApiResponse, ChatData, ChatRequest

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# SSE 响应头：禁止缓存、禁用缓冲
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


@router.post("", response_model=ApiResponse[ChatData], summary="非流式问答")
def chat(req: ChatRequest, request: Request):
    """单次问答，返回答案 + 来源引用。首次提问可不传 session_id，服务端自动生成。"""
    services = get_services(request)
    data = services.pipeline.answer(req.question, req.session_id)
    return ApiResponse.success(data)


@router.post("/stream", summary="SSE 流式问答")
def chat_stream(req: ChatRequest, request: Request):
    """流式问答（SSE）。事件格式（每行一条 JSON）：

        data: {"type":"meta","session_id":"..."}
        data: {"type":"delta","text":"..."}
        data: {"type":"sources","sources":[...]}
        data: {"type":"done","elapsed_ms":123}
    """
    services = get_services(request)

    def event_source():
        for event in services.pipeline.stream_answer(req.question, req.session_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
