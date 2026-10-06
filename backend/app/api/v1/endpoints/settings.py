"""
系統設定 API 端點 (System Settings Endpoints)
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
)

router = APIRouter()


@router.get("/env", response_model=EnvSettingsResponse)
def get_env_configurations() -> EnvSettingsResponse:
    """取得所有綁定至 .env 檔案之系統設定項目與中文詮釋資料"""
    data = get_all_env_settings()
    return EnvSettingsResponse(**data)


@router.put("/env", response_model=EnvSettingsUpdateResponse)
def update_env_configurations(payload: EnvSettingsUpdateRequest, db: Session = Depends(get_db)) -> EnvSettingsUpdateResponse:
    """
    更新設定項目至 .env 檔案中，並返回受影響之重啟檢查結果
    """
    result = save_env_settings(payload.settings)
    
    # 同步相容既有資料庫 system_settings 表
    try:
        if "RETENTION_DAYS_UNSTARTED" in payload.settings:
            days_val = int(payload.settings["RETENTION_DAYS_UNSTARTED"])
            item = db.query(SystemSetting).filter(SystemSetting.key == "retention_days_unstarted").first()
            if item:
                item.value = {"days": days_val}
            else:
                db.add(SystemSetting(key="retention_days_unstarted", value={"days": days_val}, description="未開始任務保留天數"))
            db.commit()

        if "RETENTION_DAYS_FINISHED" in payload.settings:
            days_val = int(payload.settings["RETENTION_DAYS_FINISHED"])
            item = db.query(SystemSetting).filter(SystemSetting.key == "retention_days_finished").first()
            if item:
                item.value = {"days": days_val}
            else:
                db.add(SystemSetting(key="retention_days_finished", value={"days": days_val}, description="已完成/失敗任務保留天數"))
            db.commit()

        if "UPLOAD_RETENTION_DAYS" in payload.settings:
            days_val = int(payload.settings["UPLOAD_RETENTION_DAYS"])
            item = db.query(SystemSetting).filter(SystemSetting.key == "upload_retention_days").first()
            if item:
                item.value = {"days": days_val}
            else:
                db.add(SystemSetting(key="upload_retention_days", value={"days": days_val}, description="暫存檔案保留天數"))
            db.commit()

        if "LOCAL_LLM_URL" in payload.settings or "LOCAL_LLM_MODEL" in payload.settings:
            item = db.query(SystemSetting).filter(SystemSetting.key == "llm_config").first()
            llm_val = item.value if (item and isinstance(item.value, dict)) else {"temperature": 0.1, "max_tokens": 1024}
            if "LOCAL_LLM_URL" in payload.settings:
                llm_val["api_base"] = str(payload.settings["LOCAL_LLM_URL"])
            if "LOCAL_LLM_MODEL" in payload.settings:
                llm_val["model"] = str(payload.settings["LOCAL_LLM_MODEL"])
            if item:
                item.value = llm_val
            else:
                db.add(SystemSetting(key="llm_config", value=llm_val, description="本地 LLM 推理伺服器連線與生成參數設定"))
            db.commit()
    except Exception as e:
        db.rollback()

    return EnvSettingsUpdateResponse(**result)


@router.post("/restart", response_model=RestartResponse)
def restart_server_service() -> RestartResponse:
    """觸發後端伺服器服務重啟"""
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
