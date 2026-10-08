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
