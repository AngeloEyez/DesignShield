"""
Pattern 與 PartDB 規則庫 API 端點 (Pattern & PartDB Endpoints)

支援 File-based YAML 規則樹查詢、GitOps 狀態檢視與即時重載。
"""

from typing import Dict, Any, List
from fastapi import APIRouter
from backend.app.services.pattern_service import PatternService

router = APIRouter()


@router.get("/tree")
def get_pattern_tree() -> Dict[str, Any]:
    """
    取得完整 Pattern 目錄樹與 YAML 內容
    包含 Level 1, Level 2, Level 3 (DRC 規範), PartDB 零件資料與全域 Tags
    """
    svc = PatternService.get_instance()
    return svc.get_pattern_tree()


from fastapi.responses import JSONResponse

@router.post("/reload")
def reload_patterns() -> Any:
    """
    熱重新載入磁碟上的 YAML 規則與 PartDB 資料，並重新編譯快取
    """
    svc = PatternService.get_instance()
    res = svc.reload_with_compilation(strict=True)
    if not res.get("success"):
        return JSONResponse(
            status_code=400,
            content=res
        )
    return res


@router.get("/level2-categories")
def get_level2_categories() -> List[str]:
    """
    取得全域合法 Level 2 網路拓撲分類白名單 (Single Source of Truth)
    """
    svc = PatternService.get_instance()
    return svc.get_level2_categories()


@router.get("/tags")
def get_pattern_tags() -> List[str]:
    """
    取得全域合法 DRC 標籤白名單
    """
    svc = PatternService.get_instance()
    tree = svc.get_pattern_tree()
    return tree.get("tags", [])


@router.get("/partdb")
def get_partdb() -> Dict[str, Any]:
    """
    取得所有 PartDB 晶片特規資料與介面 Schema
    """
    svc = PatternService.get_instance()
    tree = svc.get_pattern_tree()
    return tree.get("partdb", {})


from pydantic import BaseModel, Field
from fastapi import HTTPException

class UpdateRuleEnabledRequest(BaseModel):
    enabled: bool = Field(..., description="規則啟用狀態 (True/False)")

@router.patch("/rules/{rule_name}/enabled")
def update_rule_enabled(rule_name: str, payload: UpdateRuleEnabledRequest) -> Dict[str, Any]:
    """
    即時修改單一規則之啟用/停用狀態:
    1. 寫入資料庫 rule_statuses 資料表
    2. 即時更新 PatternService 記憶體快取與 Engine 執行期狀態
    """
    svc = PatternService.get_instance()
    try:
        updated = svc.update_rule_status(rule_name, payload.enabled)
        if not updated:
            raise HTTPException(status_code=404, detail=f"規則 '{rule_name}' 不存在於規則庫中")
        return {
            "success": True,
            "message": f"規則 '{rule_name}' 狀態已成功更新為 {'啟用' if payload.enabled else '停用'}",
            "data": updated
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新規則狀態失敗: {str(e)}")

