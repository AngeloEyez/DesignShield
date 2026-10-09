"""
系統設定播種模組 (System Settings Seed Data)

於系統初始化時注入系統運作預設參數 (System Settings)。
不捏造任何 DRC 規則假資料，所有規則完全由 patterns 目錄之真實 YAML 單軌驅動。
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.settings import SystemSetting

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
    注入系統預設組態設定 (System Settings)
    
    Args:
        db: 資料庫 Session
        
    Returns:
        int: 新增的設定筆數
    """
    added_count = 0
    for s_data in DEFAULT_SETTINGS:
        existing = db.query(SystemSetting).filter(SystemSetting.key == s_data["key"]).first()
        if not existing:
            new_setting = SystemSetting(**s_data)
            db.add(new_setting)
            added_count += 1
            
    db.commit()
    logger.info("Seeded %d default system settings into database.", added_count)
    return added_count
