"""
預設規則庫播種模組 (DRC Rules Seed Data)

於系統初始化時注入標準傳統啟發式圖論規則 (HEURISTIC) 與大語言模型邏輯推理規則 (LLM)。
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.rule import DrcRule
from backend.app.models.settings import SystemSetting

logger = logging.getLogger("designshield.seeds")

DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "id": "RULE-BUS-I2C-ADDR",
        "name": "I2C 匯流排地址唯一性檢查",
        "category": "Bus Integrity",
        "check_type": "HEURISTIC",
        "is_active": True,
        "parameters": {},
        "prompt_template": None,
        "context_extractor": "extract_i2c_bus_context"
    },
    {
        "id": "RULE-PWR-CAP-DERATING",
        "name": "電源濾波電容耐壓降額檢查",
        "category": "Power Domain",
        "check_type": "HEURISTIC",
        "is_active": True,
        "parameters": {"derating_factor": 0.5, "min_headroom_ratio": 0.3},
        "prompt_template": None,
        "context_extractor": "extract_power_capacitors_context"
    },
    {
        "id": "RULE-PWR-DECOUPLING",
        "name": "晶片電源引腳去耦電容配置檢查",
        "category": "Power Domain",
        "check_type": "HEURISTIC",
        "is_active": True,
        "parameters": {"min_decoupling_cap_uf": 0.01},
        "prompt_template": None,
        "context_extractor": "extract_ic_decoupling_context"
    },
    {
        "id": "RULE-CONN-PINOUT",
        "name": "連接器引腳訊號完整性與保護檢查",
        "category": "Pin Connection",
        "check_type": "HEURISTIC",
        "is_active": True,
        "parameters": {"require_esd_protection": True},
        "prompt_template": None,
        "context_extractor": "extract_connector_context"
    },
    {
        "id": "RULE-LLM-SD-MODE",
        "name": "MicroSD 介面工作模式合理性確認",
        "category": "Interface Mode",
        "check_type": "LLM",
        "is_active": True,
        "parameters": {"interface": "SD_SPI"},
        "prompt_template": (
            "你是一位資深硬體設計審查工程師。請分析以下 MicroSD 介面連線關係：\n"
            "元件與網路上下文: {context}\n"
            "請檢查：\n"
            "1. D0~D3, CLK, CMD/MOSI 引腳是否符合 SPI 或 SDIO 模式之連線意圖。\n"
            "2. 是否存在懸空或未接上拉之關鍵控制引腳。\n"
            "3. 輸出 JSON 格式包含 status (PASS/FAIL/WARNING), severity, description, comment。"
        ),
        "context_extractor": "extract_sd_interface_subgraph"
    },
    {
        "id": "RULE-LLM-POWER-SEQUENCE",
        "name": "晶片上下電時序與復位電路邏輯確認",
        "category": "Power Domain",
        "check_type": "LLM",
        "is_active": True,
        "parameters": {},
        "prompt_template": (
            "分析主控晶片與電源管理 IC (PMIC) 間之 RESET 與 POWER_GOOD 連接關係：\n"
            "上下文: {context}\n"
            "請評估復位上拉電阻與去彈跳電容設計合理性。"
        ),
        "context_extractor": "extract_reset_power_subgraph"
    },
    {
        "id": "RULE-LLM-LEVEL-SHIFT",
        "name": "跨電壓域電平轉換邏輯合理性確認",
        "category": "Signal Integrity",
        "check_type": "LLM",
        "is_active": True,
        "parameters": {},
        "prompt_template": (
            "檢查跨電壓域介面 (例如 3.3V 主控對接 1.8V 感測器)：\n"
            "上下文: {context}\n"
            "判斷是否已配置電平轉換晶片 (Level Shifter) 或雙向場效應管保護。"
        ),
        "context_extractor": "extract_level_shift_subgraph"
    }
]


def seed_default_rules(db: Session) -> int:
    """
    注入系統預設 DRC 規則庫
    
    Args:
        db: 資料庫 Session
        
    Returns:
        int: 新增的規則筆數
    """
    added_count = 0
    for r_data in DEFAULT_RULES:
        existing = db.query(DrcRule).filter(DrcRule.id == r_data["id"]).first()
        if not existing:
            new_rule = DrcRule(**r_data)
            db.add(new_rule)
            added_count += 1
            
    db.commit()
    logger.info("Seeded %d new DRC rules into database.", added_count)
    return added_count


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
