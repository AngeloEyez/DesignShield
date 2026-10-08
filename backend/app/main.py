"""
FastAPI 核心入口應用 (FastAPI Main Application)

整合 DBOS Durable Execution 引擎、Alembic/SQLAlchemy 資料庫連線與 REST API 路由。
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.db.session import Base, engine
from backend.app.api.v1.api import api_router
from backend.app.workflows.dbos_app import start_dbos, shutdown_dbos

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
)
logger = logging.getLogger("designshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理 (Lifespan Context Manager)
    
    於伺服器啟動時自動初始化資料庫結構並啟動 DBOS 工作流引擎，伺服器關閉時安全釋放資源。
    """
    logger.info("Starting up DesignShield backend application...")
    # 自動建立表格 (保障開發/測試環境順暢執行)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        
        # 確保現有表格欄位完整 (例如 task_type 自動遷移)
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        if "drc_tasks" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("drc_tasks")]
            if "task_type" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE drc_tasks ADD COLUMN task_type VARCHAR(64) DEFAULT 'DRC';"))
                    conn.commit()
                logger.info("Migrated drc_tasks table: added task_type column.")

        # 播種預設規則庫與系統組態
        from backend.app.db.session import SessionLocal
        from backend.app.db.seeds import seed_default_rules, seed_default_settings
        db = SessionLocal()
        try:
            seed_default_rules(db)
            seed_default_settings(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning("Database schema check warning: %s", e)
        
    # 啟動 DBOS Durable Execution 引擎
    try:
        start_dbos()
    except Exception as e:
        logger.warning("DBOS start warning: %s", e)
        
    # 初始化 Pattern Engine 與規則庫編譯快取 (預載入 YAML 規則、統一校驗與編譯 Regex)
    try:
        from backend.app.services.pattern_service import PatternService
        svc = PatternService.get_instance()
        init_res = svc.initialize_and_warmup(strict=False)
        if not init_res.get("success"):
            logger.warning("Pattern YAML validation found errors during startup: %s", init_res.get("errors"))
        else:
            logger.info("Pattern engines compiled and warmed up successfully: %s", init_res.get("compile_stats"))
    except Exception as e:
        logger.error("Pattern Engine startup initialization failed: %s", e)

    # 啟動每日系統維護背景任務 (自動清理過期任務與孤兒檔案)
    import asyncio
    from backend.app.engine.cleaner import cleanup_expired_tasks_and_orphan_files

    async def daily_cleanup_worker():
        while True:
            try:
                await asyncio.sleep(86400)
                from backend.app.db.session import SessionLocal
                clean_db = SessionLocal()
                try:
                    logger.info("Executing scheduled daily cleanup of expired tasks and orphan files...")
                    res = cleanup_expired_tasks_and_orphan_files(clean_db)
                    logger.info("Daily cleanup completed: %s", res)
                finally:
                    clean_db.close()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error in daily cleanup worker: %s", e)

    cleanup_worker_task = asyncio.create_task(daily_cleanup_worker())

    yield

    cleanup_worker_task.cancel()
    try:
        await cleanup_worker_task
    except (asyncio.CancelledError, Exception):
        pass

    # 伺服器關閉時優雅結束 DBOS
    logger.info("Shutting down DesignShield backend application...")
    try:
        shutdown_dbos()
    except Exception as e:
        logger.warning("DBOS shutdown warning: %s", e)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 設定跨來源資源共享 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊 API v1 路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["system"])
def health_check():
    """系統健康度檢查端點 (包含 FastAPI/DBOS, Database, LLM 燈號資訊)"""
    from backend.app.core.health import get_system_health_details
    return get_system_health_details()
