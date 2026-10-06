"""
系統核心設定模組 (System Configuration Module)

讀取環境變數與系統預設值，支援從 .env 檔案自動載入配置。
所有的資料庫連線、本地 LLM 端點與儲存路徑均集中於此管理。
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 載入 .env 檔案
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=True)
elif Path("/app/.env").exists():
    load_dotenv(dotenv_path=Path("/app/.env"), override=True)
elif Path(".env").exists():
    load_dotenv(dotenv_path=Path(".env"), override=True)


class Settings(BaseSettings):
    """
    系統整體設定類別 (System Settings Class)
    
    使用 Pydantic BaseSettings 從環境變數讀取配置，提供類型安全保證。
    """
    
    # 專案資訊
    PROJECT_NAME: str = "DesignShield - Schematic DRC System"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # 主控伺服器主機與埠號
    SERVER_HOST: str = os.getenv("SERVER_HOST", "192.168.1.16")
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8080"))
    
    # 資料庫連線配置 (支援 PostgreSQL 與 SQLite 測試環境)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./designshield.db"
    )
    
    # DBOS 系統資料庫連線配置 (預設與主資料庫同源或獨立設定)
    DBOS_SYSTEM_DATABASE_URL: str = os.getenv(
        "DBOS_SYSTEM_DATABASE_URL",
        "sqlite:///./dbos_system.db"
    )
    
    # LiteLLM 多模型服務端點配置 (支援 Local LLM, Gemini, OpenRouter, OpenAI, Anthropic 等)
    LITELLM_PROVIDER: str = os.getenv("LITELLM_PROVIDER", "local")
    LOCAL_LLM_URL: str = os.getenv("LOCAL_LLM_URL", "http://192.168.1.5:8000/v1")
    LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "openai/qwen")
    LOCAL_LLM_API_KEY: str = os.getenv("LOCAL_LLM_API_KEY", "EMPTY")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # 檔案儲存路徑配置 (Storage Paths)
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./storage/uploads")
    STAGING_DIR: str = os.getenv("STAGING_DIR", "./storage/staging")
    REPORT_DIR: str = os.getenv("REPORT_DIR", "./storage/reports")
    
    # 檔案生命週期管理預設值 (Retention Days)
    UPLOAD_RETENTION_DAYS: int = int(os.getenv("UPLOAD_RETENTION_DAYS", "7"))
    
    # 觀測性服務 (Langfuse - 可選)
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    
    # CORS 跨來源資源共享允許清單
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# 全域設定單例物件
settings = Settings()
