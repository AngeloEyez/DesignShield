"""
系統設定播種模組 (System Settings Seed Data)

於系統初始化時注入系統運作預設參數 (System Settings)。
以關聯式資料庫為單一信任來源，並將已儲存之設定即時同步回記憶體 settings 單例。
不捏造任何 DRC 規則假資料，所有規則完全由 patterns 目錄之真實 YAML 單軌驅動。
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.settings import SystemSetting
from backend.app.core.config import settings
from backend.app.core.env_manager import (
    ENV_METADATA_DEFINITIONS,
    extract_setting_value,
    sync_runtime_settings,
)

logger = logging.getLogger("designshield.seeds")

DEFAULT_SETTINGS: List[Dict[str, Any]] = [
    {
        "key": "upload_retention_days",
        "value": {"days": 7},
        "description": "暫存與已完成任務上傳檔案保留天數，逾期自動清理"
    },
    {
        "key": "task_timeout_seconds",
        "value": {"seconds": 3600},
        "description": "DRC 任務執行逾時上限 (秒)"
    },
    {
        "key": "llm_config",
        "value": {
            "api_base": "http://192.168.1.5:8000/v1",
            "model": "local-llm",
            "temperature": 0.1,
            "max_tokens": 1024
        },
        "description": "本地 LLM 推理伺服器連線與生成參數設定"
    },
    {
        "key": "auto_cleanup_schedule",
        "value": {"enabled": True, "interval_hours": 24},
        "description": "定時磁碟暫存清理排程開關與執行頻率"
    }
]


def seed_default_settings(db: Session) -> int:
    """
    注入系統預設組態設定 (System Settings)，並雙向保證資料庫與記憶體單例之同步性。
    
    1. 若資料庫為空，自全域 settings 單例 (來自 .env 初始引導) 播種預設業務設定。
    2. 若資料庫已有值，反向載入並同步更新記憶體 settings 單例，達成資料庫為單一信任來源。
    
    Args:
        db: 資料庫 Session
        
    Returns:
        int: 新增的設定筆數
    """
    added_count = 0

    # 1. 播種歷史既有通用設定項
    for s_data in DEFAULT_SETTINGS:
        existing = db.query(SystemSetting).filter(SystemSetting.key == s_data["key"]).first()
        if not existing:
            new_setting = SystemSetting(**s_data)
            db.add(new_setting)
            added_count += 1

    # 2. 播種與同步 13 項業務動態設定
    runtime_sync_payload: Dict[str, Any] = {}

    for meta in ENV_METADATA_DEFINITIONS:
        key = meta["key"]
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not existing:
            default_val = getattr(settings, key, meta.get("default", ""))
            if meta.get("item_type") == "boolean" and isinstance(default_val, bool):
                val_to_save = str(default_val).lower()
            else:
                val_to_save = str(default_val)
            new_setting = SystemSetting(
                key=key,
                value={"value": val_to_save},
                description=meta.get("label", "")
            )
            db.add(new_setting)
            added_count += 1
        else:
            runtime_sync_payload[key] = extract_setting_value(existing.value)

    db.commit()

    # 3. 將資料庫中既有設定值同步至執行期記憶體
    if runtime_sync_payload:
        sync_runtime_settings(runtime_sync_payload)

    logger.info("Seeded %d default system settings into database.", added_count)
    return added_count
