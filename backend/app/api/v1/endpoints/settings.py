"""
系統設定 API 端點 (System Settings Endpoints)

提供系統業務組態查詢與更新 (以資料庫 system_settings 為單一信任來源，即時熱更新)、
磁碟儲存統計與垃圾回收、無特權伺服器重啟及 LLM 可用模型查詢端點。
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.settings import SystemSetting
from backend.app.schemas.settings import (
    SettingResponse,
    SettingUpdate,
    EnvSettingsResponse,
    EnvSettingsUpdateRequest,
    EnvSettingsUpdateResponse,
    RestartResponse,
    LlmModelsResponse,
)
from backend.app.core.env_manager import (
    get_all_env_settings,
    save_env_settings,
    trigger_server_restart,
    fetch_available_llm_models,
    sync_runtime_settings,
    extract_setting_value,
)

router = APIRouter()


@router.get("", response_model=EnvSettingsResponse)
def get_system_settings(db: Session = Depends(get_db)) -> EnvSettingsResponse:
    """取得所有系統業務設定項目與中文詮釋資料 (以資料庫為單一信任來源)"""
    data = get_all_env_settings(db)
    return EnvSettingsResponse(**data)


@router.put("", response_model=EnvSettingsUpdateResponse)
def update_system_settings(
    payload: EnvSettingsUpdateRequest,
    db: Session = Depends(get_db)
) -> EnvSettingsUpdateResponse:
    """
    更新系統設定項目至資料庫中，並即時熱同步至執行期記憶體 (100% 免重啟)
    """
    result = save_env_settings(payload.settings, db)
    return EnvSettingsUpdateResponse(**result)


# 保留 /env 作為別名相容路由，內部導向資料庫讀寫
@router.get("/env", response_model=EnvSettingsResponse)
def get_env_configurations(db: Session = Depends(get_db)) -> EnvSettingsResponse:
    """取得所有系統設定項目與中文詮釋資料 (相容別名端點)"""
    return get_system_settings(db)


@router.put("/env", response_model=EnvSettingsUpdateResponse)
def update_env_configurations(
    payload: EnvSettingsUpdateRequest,
    db: Session = Depends(get_db)
) -> EnvSettingsUpdateResponse:
    """更新設定項目至資料庫中 (相容別名端點)"""
    return update_system_settings(payload, db)


@router.post("/restart", response_model=RestartResponse)
def restart_server_service() -> RestartResponse:
    """觸發後端伺服器服務重啟 (無特權優雅退出)"""
    result = trigger_server_restart()
    return RestartResponse(**result)


@router.get("/llm/models", response_model=LlmModelsResponse)
def get_available_llm_models(
    provider: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None
) -> LlmModelsResponse:
    """即時向指定的 LLM 伺服器端點或 Provider 查詢可用模型清單"""
    result = fetch_available_llm_models(provider=provider, api_base=api_base, api_key=api_key)
    return LlmModelsResponse(**result)


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
    手動觸發儲存空間垃圾回收清理 (清理過期任務與孤兒檔案)
    """
    from backend.app.engine.cleaner import cleanup_expired_tasks_and_orphan_files, cleanup_expired_files

    if retention_days is not None:
        return cleanup_expired_files(
            retention_days=retention_days,
            dry_run=dry_run,
            include_reports=include_reports
        )

    return cleanup_expired_tasks_and_orphan_files(db, dry_run=dry_run)


@router.get("/{key}", response_model=SettingResponse)
def get_setting(key: str, db: Session = Depends(get_db)) -> SettingResponse:
    """取得特定設定項目"""
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
    """更新或建立特定系統設定項目，並即時同步快取"""
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

    # 同步快取與環境變數
    extracted = extract_setting_value(payload.value)
    sync_runtime_settings({key: extracted})
    return item
