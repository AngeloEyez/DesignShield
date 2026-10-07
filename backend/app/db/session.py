"""
資料庫連線與 Session 管理模組 (Database Session Management)

建立 SQLAlchemy Engine 與 SessionLocal，並提供 FastAPI 依賴注入使用之 get_db 函式。
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
# 宣告式模型基底類別 (置於頂部避免模型循環引用)
Base = declarative_base()

from backend.app.core.config import settings

# 處理 SQLite 與 PostgreSQL 連線參數相容性
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# 建立 SQLAlchemy Engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# 建立 SessionLocal 工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    取得資料庫 Session 之依賴注入產生器 (FastAPI Dependency)
    
    Yields:
        Session: SQLAlchemy Session 物件
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
