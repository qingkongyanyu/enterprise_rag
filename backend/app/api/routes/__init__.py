"""API 路由注册入口。"""
from fastapi import APIRouter

from app.api.routes import chat, knowledge, sessions, system

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(sessions.router)
api_router.include_router(knowledge.router)
api_router.include_router(system.router)
