"""
系統健康度檢查模組 (System Health Check Service)

提供 FastAPI/DBOS、Database (PostgreSQL/SQLite) 與 LLM 推理引擎之健康燈號檢查。
"""

import os
import logging
from typing import Dict, Any
from sqlalchemy import text

logger = logging.getLogger("designshield.health")


def check_database_health() -> Dict[str, Any]:
    """檢查資料庫連線健康度"""
    from backend.app.core.config import settings
    from backend.app.db.session import engine

    db_type = "PostgreSQL" if "postgresql" in settings.DATABASE_URL.lower() else "SQLite"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "label": f"Database ({db_type})",
            "message": "連線正常"
        }
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        return {
            "status": "error",
            "label": f"Database ({db_type})",
            "message": "連線中斷"
        }


def check_fastapi_dbos_health() -> Dict[str, Any]:
    """檢查 FastAPI 與 DBOS 工作流引擎健康度"""
    try:
        from backend.app.workflows.dbos_app import _dbos_initialized
        if _dbos_initialized:
            msg = "DBOS 工作流引擎在線"
        else:
            msg = "FastAPI 服務在線"
        return {
            "status": "healthy",
            "label": "FASTAPI / DBOS",
            "message": msg
        }
    except Exception:
        return {
            "status": "healthy",
            "label": "FASTAPI / DBOS",
            "message": "在線"
        }


def check_llm_health() -> Dict[str, Any]:
    """檢查 LLM 大語言模型推理連線狀態"""
    import urllib.request
    from backend.app.core.config import settings
    from backend.app.core.env_manager import parse_raw_env_file, get_env_file_path

    env_dict = parse_raw_env_file(get_env_file_path())
    provider = (env_dict.get("LITELLM_PROVIDER") or os.environ.get("LITELLM_PROVIDER") or "local").strip().lower()
    model = (env_dict.get("LOCAL_LLM_MODEL") or os.environ.get("LOCAL_LLM_MODEL") or settings.LOCAL_LLM_MODEL).strip()

    if provider in ("gemini", "google"):
        api_key = env_dict.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") or env_dict.get("LOCAL_LLM_API_KEY", "")
        if api_key and str(api_key).strip() and str(api_key).strip() != "EMPTY":
            return {
                "status": "healthy",
                "label": "LLM (Gemini)",
                "provider": "gemini",
                "model": model or "gemini-2.5-flash",
                "message": "金鑰已配置"
            }
        else:
            return {
                "status": "warning",
                "label": "LLM (Gemini)",
                "provider": "gemini",
                "model": model or "gemini-2.5-flash",
                "message": "待設定 API 金鑰"
            }

    # 其他雲端 Provider (OpenRouter, OpenAI, Groq, DeepSeek, Anthropic)
    if provider in ("openrouter", "openai", "groq", "deepseek", "anthropic"):
        key_var = f"{provider.upper()}_API_KEY"
        key_val = env_dict.get(key_var) or os.environ.get(key_var) or env_dict.get("LOCAL_LLM_API_KEY")
        if key_val and str(key_val).strip() and str(key_val).strip() != "EMPTY":
            return {
                "status": "healthy",
                "label": f"LLM ({provider.title()})",
                "provider": provider,
                "model": model,
                "message": "金鑰已配置"
            }
        else:
            return {
                "status": "warning",
                "label": f"LLM ({provider.title()})",
                "provider": provider,
                "model": model,
                "message": f"未設定 {key_var}"
            }

    # 本地 LLM (local)
    llm_url = (env_dict.get("LOCAL_LLM_URL") or os.environ.get("LOCAL_LLM_URL") or settings.LOCAL_LLM_URL).strip().rstrip("/")
    if llm_url.endswith("/v1"):
        target_url = f"{llm_url}/models"
    else:
        target_url = f"{llm_url}/v1/models"

    try:
        req = urllib.request.Request(target_url, headers={"User-Agent": "DesignShield/0.1.0"}, method="GET")
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            if resp.status == 200:
                return {
                    "status": "healthy",
                    "label": "本地 LLM",
                    "provider": "local",
                    "model": model,
                    "message": "連線正常"
                }
    except Exception:
        fallback_url = f"{llm_url}/models"
        try:
            req = urllib.request.Request(fallback_url, headers={"User-Agent": "DesignShield/0.1.0"}, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return {
                        "status": "healthy",
                        "label": "本地 LLM",
                        "provider": "local",
                        "model": model,
                        "message": "連線正常"
                    }
        except Exception:
            pass

    return {
        "status": "warning",
        "label": "本地 LLM",
        "provider": "local",
        "model": model,
        "message": "未連線或伺服器離線"
    }


def get_system_health_details() -> Dict[str, Any]:
    """彙整完整系統健康狀態"""
    from backend.app.core.config import settings

    api_health = check_fastapi_dbos_health()
    db_health = check_database_health()
    llm_health = check_llm_health()

    overall_status = "healthy"
    if db_health["status"] == "error":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "components": {
            "api": api_health,
            "database": db_health,
            "llm": llm_health
        }
    }
