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
        
    yield
    
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
    """系統健康度檢查端點"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
