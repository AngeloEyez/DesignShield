"""
系統設定 API 端點 (System Settings Endpoints)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.settings import SystemSetting
from backend.app.schemas.settings import SettingResponse, SettingUpdate

router = APIRouter()


@router.get("", response_model=List[SettingResponse])
def get_all_settings(db: Session = Depends(get_db)) -> List[SettingResponse]:
    """取得所有系統設定"""
    return db.query(SystemSetting).all()


@router.get("/storage-stats")
def get_storage_stats():
    """取得目前磁碟暫存空間佔用指標"""
    from backend.app.engine.cleaner import get_all_storage_stats
    return get_all_storage_stats()


@router.post("/cleanup")
def trigger_storage_cleanup(
    retention_days: int = None,
    dry_run: bool = False,
    include_reports: bool = False,
    db: Session = Depends(get_db)
):
    """
    手動觸發儲存空間垃圾回收清理
    
    若未指定 retention_days，則自動依據系統設定 upload_retention_days 中的天數進行清理。
    """
    from backend.app.engine.cleaner import cleanup_expired_files
    if retention_days is None:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "upload_retention_days").first()
        if setting and isinstance(setting.value, dict) and "days" in setting.value:
            retention_days = int(setting.value["days"])
        else:
            retention_days = 7
            
    result = cleanup_expired_files(
        retention_days=retention_days,
        dry_run=dry_run,
        include_reports=include_reports
    )
    return result


@router.get("/{key}", response_model=SettingResponse)
def get_setting(key: str, db: Session = Depends(get_db)) -> SettingResponse:
    """取得特定設定"""
    item = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not item:
        raise HTTPException(status_code=404, detail="Setting not found")
    return item


@router.put("/{key}", response_model=SettingResponse)
def update_setting(
    key: str,
    payload: SettingUpdate,
    db: Session = Depends(get_db)
) -> SettingResponse:
    """更新或建立系統設定"""
    item = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not item:
        item = SystemSetting(key=key, value=payload.value, description=payload.description)
        db.add(item)
    else:
        item.value = payload.value
        if payload.description is not None:
            item.description = payload.description
            
    db.commit()
    db.refresh(item)
    return item
