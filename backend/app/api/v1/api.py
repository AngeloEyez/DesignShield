"""
API v1 路由總匯模組 (API v1 Router Aggregator)
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import tasks, rules, settings

api_router = APIRouter()

api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])


@api_router.get("/health", tags=["system"])
def health_check_v1():
    """
    API v1 系統健康度檢查端點 (System Health Check Endpoint)

    供前端透過 Nginx /api/ 反向代理通道或外部監控進行服務健康狀態偵測。
    
    Returns:
        dict: 包含 healthy 狀態碼、服務名稱與版本號之字典
    """
    from backend.app.core.health import get_system_health_details
    return get_system_health_details()

