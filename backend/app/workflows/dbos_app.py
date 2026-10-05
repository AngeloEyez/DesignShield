"""
DBOS 執行引擎初始化模組 (DBOS Engine Initialization)

負責配置與啟動 DBOS Durable Execution 引擎，提供可靠任務執行、斷點接續與步驟追蹤。
"""

import os
import logging
from typing import Optional
from dbos import DBOS, DBOSConfig
from backend.app.core.config import settings

logger = logging.getLogger("designshield.dbos")

_dbos_initialized = False


def init_dbos() -> DBOS:
    """
    初始化 DBOS 引擎實例
    
    Returns:
        DBOS: 初始化後的 DBOS 實例
    """
    global _dbos_initialized
    if _dbos_initialized:
        return DBOS
    
    logger.info("Initializing DBOS with system database: %s", settings.DBOS_SYSTEM_DATABASE_URL)
    
    config = DBOSConfig(
        name="designshield_drc",
        system_database_url=settings.DBOS_SYSTEM_DATABASE_URL,
        log_level="INFO"
    )
    
    dbos_instance = DBOS(config=config)
    _dbos_initialized = True
    return dbos_instance


def start_dbos() -> None:
    """啟動 DBOS 背景佇列與排程監聽"""
    init_dbos()
    try:
        DBOS.launch()
        logger.info("DBOS engine launched successfully.")
    except Exception as e:
        logger.warning("DBOS launch notice: %s", e)


def shutdown_dbos() -> None:
    """優雅關閉 DBOS 引擎"""
    global _dbos_initialized
    if os.environ.get("PYTEST_CURRENT_TEST"):
        # 測試執行期間維持 Session-scoped DBOS 存活
        return
    try:
        DBOS.destroy()
        _dbos_initialized = False
        logger.info("DBOS engine shut down successfully.")
    except Exception as e:
        logger.warning("Error during DBOS shutdown: %s", e)
