"""
API v1 路由總匯模組 (API v1 Router Aggregator)
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import tasks, rules, settings

api_router = APIRouter()

api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
