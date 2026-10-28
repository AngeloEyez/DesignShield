"""
系統設定與環境配置核心管理模組 (Settings & Environment Manager)

負責管理系統業務動態設定（LiteLLM 模型、Langfuse 遙測、檔案儲存生命週期），
以關聯式資料庫 (system_settings) 為單一信任來源 (SSOT)，支援記憶體即時熱更新 (Zero-Downtime)，
並提供中文描述、分類元數據與無特權之伺服器重啟調度功能。
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("designshield.env_manager")


def extract_setting_value(raw: Any) -> Any:
    """
    從資料庫 SystemSetting.value (JSON) 提取實際數值，相容不同資料結構與歷史格式。
    
    Args:
        raw: 原始儲存的 JSON 物件或純量數值
        
    Returns:
        Any: 提取後的純量數值或原始內容
    """
    if isinstance(raw, dict):
        if "value" in raw:
            return raw["value"]
        if "days" in raw:
            return raw["days"]
        if "seconds" in raw:
            return raw["seconds"]
    return raw


# 尋找生效中的 .env 檔案路徑 (僅供啟動引導與歷史測試相容使用)
def get_env_file_path() -> Path:
    """取得實體 .env 檔案路徑 (供啟動引導與單元測試相容)"""
    candidates = [
        Path("/app/.env"),
        Path(__file__).resolve().parents[3] / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return Path(__file__).resolve().parents[3] / ".env"


def parse_raw_env_file(file_path: Path) -> Dict[str, str]:
    """解析 .env 檔案為鍵值對 (供啟動引導與測試隔離相容)"""
    env_dict = {}
    if not file_path.exists():
        return env_dict
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                k, v = stripped.split("=", 1)
                k = k.strip()
                v = v.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                env_dict[k] = v
    return env_dict


# 系統業務設定元數據定義 (以資料庫為單一信任來源，全部支援即時熱生效，免重啟)
ENV_METADATA_DEFINITIONS: List[Dict[str, Any]] = [
    # 1. LiteLLM 多模型服務串接 (LiteLLM Providers)
    {
        "key": "LITELLM_PROVIDER",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "LiteLLM 服務提供商 (Provider)",
        "description": "選擇當前啟用之大語言模型提供商。支援 Google Gemini (gemini)、OpenRouter (openrouter)、本地推理 (local / vLLM / Ollama)、OpenAI (openai)、Anthropic (anthropic)、Groq (groq)、DeepSeek (deepseek) 等相容 LiteLLM 之雲端與本地服務。",
        "example": "local",
        "default": "local",
        "is_secret": False,
        "requires_restart": False,
    },
    {
        "key": "LLM_API_BASE",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "API 服務端點 URL (API Base)",
        "description": "大語言模型 API 服務端點網址。本地端點預設為 http://192.168.1.5:8000/v1；OpenRouter 為 https://openrouter.ai/api/v1；Google Gemini/OpenAI 官方端點若無需自訂代理可留空。",
        "example": "http://192.168.1.5:8000/v1",
        "default": "http://192.168.1.5:8000/v1",
        "is_secret": False,
        "requires_restart": False,
    },
    {
        "key": "LLM_API_KEY",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "API 存取金鑰 (API Key)",
        "description": "呼叫模型服務所需的 API Key (Google Gemini 填入 AIzaSy...、OpenRouter 填入 sk-or-v1-...、本地未啟用鑑權填 EMPTY)。",
        "example": "EMPTY",
        "default": "EMPTY",
        "is_secret": True,
        "requires_restart": False,
    },
    {
        "key": "LLM_MODEL",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "推理模型名稱 (Model)",
        "description": "指定 LiteLLM 調用的模型名稱。支援各家前綴 (如 gemini/gemini-2.5-flash、openrouter/google/gemini-2.5-flash、openai/qwen、deepseek/deepseek-chat 等)。支援依 Provider 即時查詢下拉選取或手動輸入。",
        "example": "openai/qwen",
        "default": "openai/qwen",
        "is_secret": False,
        "requires_restart": False,
    },
    {
        "key": "GEMINI_API_KEY",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "Google Gemini 專屬金鑰 (選填)",
        "description": "Google AI Studio API Key。若填寫此項，LiteLLM 呼叫 gemini/* 系列模型時將自動以此金鑰進行鑑權。",
        "example": "AIzaSyxxxxxxxxxxxxxxxxxxxx",
        "default": "",
        "is_secret": True,
        "requires_restart": False,
    },
    {
        "key": "OPENROUTER_API_KEY",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "OpenRouter 專屬金鑰 (選填)",
        "description": "OpenRouter API Key。若填寫此項，LiteLLM 呼叫 openrouter/* 系列模型時將自動以此金鑰進行鑑權。",
        "example": "sk-or-v1-xxxxxxxxxxxxxxxxxxxx",
        "default": "",
        "is_secret": True,
        "requires_restart": False,
    },
    {
        "key": "ENABLE_LEVEL1_LLM_FALLBACK",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "Level 1 零件分類 LLM 保底推論開關",
        "description": "當 Level 1 元件未能命中任何 YAML 規則 (信心度 < 0.6) 時，是否呼叫大語言模型進行語意保底推論。\n啟用時：發送微批次請求由 LLM 識別元件類別、次類別與功能角色；\n停用時：跳過 LLM 分析，直接套用 Unknown/None 保底分類，零延遲且節省 Token。",
        "example": "true 或 false",
        "default": "true",
        "item_type": "boolean",
        "is_secret": False,
        "requires_restart": False,
    },
    {
        "key": "ENABLE_LEVEL2_LLM_FALLBACK",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接",
        "label": "Level 2 網路拓撲 LLM 保底推論開關",
        "description": "當 Level 2 網路未能命中任何 YAML 拓撲規則且名稱模糊 (信心度 < 0.6) 時，是否呼叫大語言模型進行語意保底推論。\n啟用時：結合網路連接之 IC 引腳特徵由 LLM 判定匯流排類型或電源軌；\n停用時：跳過 LLM 分析，直接套用 Signal/General_Signal 預設分類，完全依賴純規則演算法。",
        "example": "true 或 false",
        "default": "true",
        "item_type": "boolean",
        "is_secret": False,
        "requires_restart": False,
    },

    # 2. Langfuse 觀測與追蹤服務 (Observability)
    {
        "key": "LANGFUSE_PUBLIC_KEY",
        "category": "langfuse",
        "category_name": "Langfuse 觀測與追蹤服務",
        "label": "Langfuse 公開金鑰 (Public Key)",
        "description": "用於後端 LiteLLM 自動上報 LLM 推理追蹤數據至 Langfuse 的公開金鑰。請至 Langfuse 儀表板中的專案 API Keys 取得。\n範例: LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx",
        "example": "pk-lf-xxxxxxxxxxxxxxxx",
        "default": "",
        "is_secret": False,
        "requires_restart": False,
    },
    {
        "key": "LANGFUSE_SECRET_KEY",
        "category": "langfuse",
        "category_name": "Langfuse 觀測與追蹤服務",
        "label": "Langfuse 私密金鑰 (Secret Key)",
        "description": "用於後端 LiteLLM 安全驗證與寫入 Telemetry 紀錄的私密金鑰。請至 Langfuse 儀表板中的專案 API Keys 取得。\n範例: LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx",
        "example": "sk-lf-xxxxxxxxxxxxxxxx",
        "default": "",
        "is_secret": True,
        "requires_restart": False,
    },
    {
        "key": "LANGFUSE_HOST",
        "category": "langfuse",
        "category_name": "Langfuse 觀測與追蹤服務",
        "label": "Langfuse 伺服器端點",
        "description": "後端服務連線並傳送追蹤資料之 Langfuse 伺服器位址 (在 Docker 內部網路中可填 http://langfuse:3000 或對外 http://192.168.1.16:3000)。",
        "example": "http://langfuse:3000",
        "default": "http://langfuse:3000",
        "is_secret": False,
        "requires_restart": False,
    },

    # 3. 磁碟儲存與檔案生命週期 (Storage & Retention)
    {
        "key": "RETENTION_DAYS_UNSTARTED",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "未開始任務預設保留天數",
        "description": "尚未啟動正式檢測之任務（如僅完成預檢尚未確認規則）預設保留天數。超過此天數將自動清理該任務及其上傳檔案與暫存目錄。",
        "example": "2",
        "default": "2",
        "item_type": "integer",
        "is_secret": False,
        "requires_restart": False,
    },
    {
        "key": "RETENTION_DAYS_FINISHED",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "已完成/失敗任務預設保留天數",
        "description": "已完成檢測、失敗或取消之中止任務預設保留天數。超過此天數將自動清除該任務、產出報告與綁定之所有磁碟檔案。",
        "example": "5",
        "default": "5",
        "item_type": "integer",
        "is_secret": False,
        "requires_restart": False,
    },
]

# 業務分類列表
SETTING_CATEGORIES = [
    {"id": "llm", "name": "LiteLLM 多模型服務串接", "icon": "pi pi-microchip-ai"},
    {"id": "langfuse", "name": "Langfuse 觀測與追蹤服務", "icon": "pi pi-chart-line"},
    {"id": "storage", "name": "檔案儲存與生命週期管理", "icon": "pi pi-database"},
]


def sync_runtime_settings(updates: Dict[str, Any]) -> None:
    """
    即時同步記憶體中的 settings 單例物件與行程環境變數，達成 100% 零停機即時生效。
    
    Args:
        updates: 更新的設定字典
    """
    from backend.app.core.config import settings

    for k, v in updates.items():
        if hasattr(settings, k):
            orig_val = getattr(settings, k)
            if isinstance(orig_val, bool):
                setattr(settings, k, str(v).lower() in ("true", "1", "yes", "t", "enable", "enabled"))
            elif isinstance(orig_val, int):
                try:
                    setattr(settings, k, int(v))
                except (ValueError, TypeError):
                    setattr(settings, k, v)
            else:
                setattr(settings, k, str(v))
        os.environ[k] = str(v)

    # 若更新了 Langfuse 金鑰或端點，自動重新載入 LiteLLM callbacks
    if any(k in updates for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")):
        try:
            from backend.app.engine.rules import llm
            if getattr(settings, "LANGFUSE_PUBLIC_KEY", "") and getattr(settings, "LANGFUSE_SECRET_KEY", ""):
                llm._LANGFUSE_INITIALIZED = False
                llm._init_langfuse_if_configured()
        except Exception as e:
            logger.warning(f"Failed to reinit langfuse callbacks: {e}")


def get_all_env_settings(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    自資料庫讀取所有系統設定項目，包含完整中文詮釋資料與目前數值。
    若資料庫中尚未建立特定設定鍵，則自動退回全域 settings 單例預設值。
    
    Args:
        db: 可選的 SQLAlchemy Session 物件
        
    Returns:
        Dict: 包含項目列表、分類列表與中繼資料
    """
    from backend.app.core.config import settings
    from backend.app.models.settings import SystemSetting

    close_session = False
    if db is None:
        from backend.app.db.session import SessionLocal
        db = SessionLocal()
        close_session = True

    try:
        db_items = db.query(SystemSetting).all()
        db_map = {item.key: extract_setting_value(item.value) for item in db_items}
    finally:
        if close_session:
            db.close()

    items = []
    for meta in ENV_METADATA_DEFINITIONS:
        key = meta["key"]
        if key in db_map and db_map[key] is not None:
            current_val = db_map[key]
        else:
            current_val = getattr(settings, key, os.environ.get(key, meta.get("default", "")))

        items.append({
            "key": key,
            "value": str(current_val) if current_val is not None else "",
            "category": meta["category"],
            "category_name": meta["category_name"],
            "label": meta["label"],
            "description": meta["description"],
            "example": meta["example"],
            "default": meta.get("default", ""),
            "item_type": meta.get("item_type", "string"),
            "is_secret": meta.get("is_secret", False),
            "requires_restart": False
        })

    return {
        "env_file_path": "database://system_settings",
        "items": items,
        "categories": SETTING_CATEGORIES,
        "total_count": len(items)
    }


def save_env_settings(updates: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
    """
    將設定變更安全寫入資料庫 system_settings 資料表，並即時同步記憶體快取。
    完全不修改磁碟上的實體 .env 檔案，達成資料庫單一信任來源與零中斷即時生效。
    
    Args:
        updates: 更新的鍵值對字典
        db: 可選的 SQLAlchemy Session
        
    Returns:
        Dict: 包含成功狀態、變更鍵列表與重啟檢查結果
    """
    from backend.app.models.settings import SystemSetting

    close_session = False
    if db is None:
        from backend.app.db.session import SessionLocal
        db = SessionLocal()
        close_session = True

    meta_dict = {m["key"]: m for m in ENV_METADATA_DEFINITIONS}
    changed_keys = []

    try:
        for k, new_v in updates.items():
            changed_keys.append(k)
            item = db.query(SystemSetting).filter(SystemSetting.key == k).first()
            label = meta_dict[k]["label"] if k in meta_dict else k
            if item:
                item.value = {"value": new_v}
            else:
                db.add(SystemSetting(key=k, value={"value": new_v}, description=label))

            # 相容性同步至舊版特定設定鍵 (如 retention_days_unstarted 等)
            if k == "RETENTION_DAYS_UNSTARTED":
                legacy = db.query(SystemSetting).filter(SystemSetting.key == "retention_days_unstarted").first()
                val_dict = {"days": int(new_v)}
                if legacy:
                    legacy.value = val_dict
                else:
                    db.add(SystemSetting(key="retention_days_unstarted", value=val_dict, description="未開始任務保留天數"))

            elif k == "RETENTION_DAYS_FINISHED":
                legacy = db.query(SystemSetting).filter(SystemSetting.key == "retention_days_finished").first()
                val_dict = {"days": int(new_v)}
                if legacy:
                    legacy.value = val_dict
                else:
                    db.add(SystemSetting(key="retention_days_finished", value=val_dict, description="已完成/失敗任務保留天數"))

            elif k == "LLM_API_BASE" or k == "LLM_MODEL":
                legacy = db.query(SystemSetting).filter(SystemSetting.key == "llm_config").first()
                llm_val = legacy.value if (legacy and isinstance(legacy.value, dict)) else {"temperature": 0.1, "max_tokens": 1024}
                if k == "LLM_API_BASE":
                    llm_val["api_base"] = str(new_v)
                if k == "LLM_MODEL":
                    llm_val["model"] = str(new_v)
                if legacy:
                    legacy.value = llm_val
                else:
                    db.add(SystemSetting(key="llm_config", value=llm_val, description="本地 LLM 推理伺服器連線與生成參數設定"))

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save settings to database: {e}")
        raise
    finally:
        if close_session:
            db.close()

    # 即時同步記憶體中的 settings 單例
    sync_runtime_settings(updates)

    return {
        "success": True,
        "changed_keys": changed_keys,
        "requires_restart": False,
        "restart_reasons": [],
        "message": "設定已成功儲存至資料庫並即時生效！"
    }


def trigger_server_restart() -> Dict[str, Any]:
    """
    執行伺服器重啟調度。
    完全不依賴高特權之 /var/run/docker.sock，採用非特權行程自我優雅退出，
    由容器生命週期策略 (Docker restart: always) 或 Uvicorn 自動重新加載。
    
    Returns:
        Dict: 重啟排程確認資訊
    """
    logger.info("Triggering non-privileged asynchronous server restart...")

    def _restart_worker():
        # 延遲 0.8 秒，保證當前 HTTP 請求回應已完整傳回瀏覽器
        time.sleep(0.8)

        # 1. 嘗試觸發 Uvicorn 熱重載 (touch main.py)
        try:
            main_py = Path(__file__).resolve().parents[1] / "main.py"
            if main_py.exists():
                main_py.touch()
                logger.info(f"Touched {main_py} to trigger Uvicorn WatchFiles reload")
        except Exception as e:
            logger.warning(f"Failed to touch main.py: {e}")

        # 2. 延遲 0.5 秒後自我終止行程，觸發 Docker restart: always 自動重開
        time.sleep(0.5)
        logger.info("Exiting process to trigger container auto-restart...")
        os._exit(0)

    import threading
    t = threading.Thread(target=_restart_worker, daemon=True)
    t.start()

    return {
        "success": True,
        "mode": "async_restart",
        "message": "已排程後端服務重啟，程序即將重新加載。"
    }


def fetch_available_llm_models(
    provider: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    即時向設定的 Provider 或端點查詢可用的 LLM 模型清單。
    支援 Google Gemini、OpenRouter、本地推理伺服器 (OpenAI 協定/Ollama)、OpenAI、Anthropic、Groq、DeepSeek 等。
    
    Args:
        provider: 模型供應商識別名稱
        api_base: 服務端點網址
        api_key: 存取金鑰
        
    Returns:
        Dict: 模型清單與狀態訊息
    """
    import urllib.request
    import json
    from backend.app.core.config import settings

    p = (provider or getattr(settings, "LITELLM_PROVIDER", "local")).strip().lower()

    if api_base:
        if "openrouter" in api_base:
            p = "openrouter"
        elif "generativelanguage.googleapis.com" in api_base:
            p = "gemini"
        elif "api.openai.com" in api_base:
            p = "openai"
        elif "api.groq.com" in api_base:
            p = "groq"
        elif "deepseek.com" in api_base:
            p = "deepseek"
        elif "anthropic.com" in api_base:
            p = "anthropic"

    # 1. Google Gemini
    if p in ("gemini", "google"):
        curated_gemini = [
            "gemini/gemini-2.5-pro",
            "gemini/gemini-2.5-flash",
            "gemini/gemini-2.0-flash",
            "gemini/gemini-2.0-flash-lite",
            "gemini/gemini-1.5-pro",
            "gemini/gemini-1.5-flash",
        ]
        gemini_key = api_key or getattr(settings, "GEMINI_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
        if gemini_key == "EMPTY":
            gemini_key = ""
        if gemini_key and str(gemini_key).strip():
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key.strip()}"
                req = urllib.request.Request(url, headers={"User-Agent": "DesignShield/0.1.0"})
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        fetched = []
                        for m in data.get("models", []):
                            m_name = m.get("name", "")
                            if "gemini" in m_name:
                                fetched.append(f"gemini/{m_name.replace('models/', '')}")
                        if fetched:
                            all_models = list(dict.fromkeys(curated_gemini + fetched))
                            return {
                                "success": True,
                                "provider": "gemini",
                                "api_base": "https://generativelanguage.googleapis.com",
                                "models": all_models,
                                "message": f"成功自 Google Gemini API 即時取得 {len(all_models)} 個可用模型"
                            }
            except Exception as e:
                logger.debug("Failed to query live Google Gemini models: %s", e)

        return {
            "success": True,
            "provider": "gemini",
            "api_base": "https://generativelanguage.googleapis.com",
            "models": curated_gemini,
            "message": "已載入 Google Gemini 精選推薦模型清單"
        }

    # 2. OpenRouter
    if p == "openrouter":
        curated_openrouter = [
            "openrouter/google/gemini-2.5-flash",
            "openrouter/google/gemini-2.5-pro",
            "openrouter/anthropic/claude-3.5-sonnet",
            "openrouter/openai/gpt-4o",
            "openrouter/meta-llama/llama-3.3-70b-instruct",
            "openrouter/deepseek/deepseek-chat",
            "openrouter/qwen/qwen-2.5-72b-instruct"
        ]
        openrouter_key = api_key or getattr(settings, "OPENROUTER_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
        if openrouter_key == "EMPTY":
            openrouter_key = ""
        if openrouter_key and str(openrouter_key).strip():
            try:
                url = "https://openrouter.ai/api/v1/models"
                req = urllib.request.Request(url, headers={
                    "Authorization": f"Bearer {openrouter_key.strip()}",
                    "User-Agent": "DesignShield/0.1.0"
                })
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        models = [f"openrouter/{m['id']}" for m in data.get("data", []) if "id" in m]
                        if models:
                            return {
                                "success": True,
                                "provider": "openrouter",
                                "api_base": "https://openrouter.ai/api/v1",
                                "models": models[:60],
                                "message": f"成功自 OpenRouter 即時取得 {len(models)} 個可用模型"
                            }
            except Exception as e:
                logger.debug("Failed to query OpenRouter models: %s", e)

        return {
            "success": True,
            "provider": "openrouter",
            "api_base": "https://openrouter.ai/api/v1",
            "models": curated_openrouter,
            "message": "已載入 OpenRouter 精選主流模型清單"
        }

    # 3. OpenAI 官方
    if p == "openai":
        openai_models = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/o1",
            "openai/o3-mini",
            "openai/gpt-4-turbo"
        ]
        return {
            "success": True,
            "provider": "openai",
            "api_base": "https://api.openai.com/v1",
            "models": openai_models,
            "message": "成功取得 OpenAI 官方推薦模型清單"
        }

    # 4. Anthropic 官方
    if p == "anthropic":
        anthropic_models = [
            "anthropic/claude-3-5-sonnet-20241022",
            "anthropic/claude-3-5-haiku-20241022",
            "anthropic/claude-3-opus-20240229"
        ]
        return {
            "success": True,
            "provider": "anthropic",
            "api_base": "https://api.anthropic.com",
            "models": anthropic_models,
            "message": "成功取得 Anthropic 官方模型清單"
        }

    # 5. Groq
    if p == "groq":
        groq_models = [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/mixtral-8x7b-32768",
            "groq/gemma2-9b-it"
        ]
        return {
            "success": True,
            "provider": "groq",
            "api_base": "https://api.groq.com/openai/v1",
            "models": groq_models,
            "message": "成功取得 Groq 高速推理模型清單"
        }

    # 6. DeepSeek 官方
    if p == "deepseek":
        deepseek_models = [
            "deepseek/deepseek-chat",
            "deepseek/deepseek-reasoner"
        ]
        return {
            "success": True,
            "provider": "deepseek",
            "api_base": "https://api.deepseek.com/v1",
            "models": deepseek_models,
            "message": "成功取得 DeepSeek 官方模型清單"
        }

    # 7. 本地推理伺服器 (Local LLM / vLLM / Ollama / llama.cpp)
    if not api_base:
        api_base = getattr(settings, "LLM_API_BASE", "http://192.168.1.5:8000/v1")
    if not api_key:
        api_key = getattr(settings, "LLM_API_KEY", "EMPTY")

    clean_base = str(api_base).strip().rstrip("/")
    if clean_base.endswith("/v1"):
        target_url = f"{clean_base}/models"
    else:
        target_url = f"{clean_base}/v1/models"

    headers = {
        "User-Agent": "DesignShield/0.1.0",
        "Accept": "application/json"
    }
    if api_key and str(api_key).strip() and str(api_key).strip() != "EMPTY":
        headers["Authorization"] = f"Bearer {str(api_key).strip()}"

    models = []
    error_msg = ""

    try:
        req = urllib.request.Request(target_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=4.0) as response:
            if response.status == 200:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                if "data" in data and isinstance(data["data"], list):
                    for m in data["data"]:
                        if isinstance(m, dict) and "id" in m:
                            models.append(str(m["id"]))
                elif "models" in data and isinstance(data["models"], list):
                    for m in data["models"]:
                        if isinstance(m, dict) and "name" in m:
                            models.append(str(m["name"]))
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Failed to query {target_url}: {e}")

    # 若未找到且未以 /v1 結尾，嘗試備援網址 {clean_base}/models
    if not models and not clean_base.endswith("/v1"):
        fallback_url = f"{clean_base}/models"
        try:
            req = urllib.request.Request(fallback_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as response:
                if response.status == 200:
                    body = response.read().decode("utf-8")
                    data = json.loads(body)
                    if "data" in data and isinstance(data["data"], list):
                        for m in data["data"]:
                            if isinstance(m, dict) and "id" in m:
                                models.append(str(m["id"]))
        except Exception:
            pass

    if models:
        sorted_models = sorted(list(set(models)))
        return {
            "success": True,
            "provider": "local",
            "api_base": clean_base,
            "models": sorted_models,
            "message": f"成功自本地 LLM 伺服器取得 {len(sorted_models)} 個可用模型"
        }
    else:
        return {
            "success": False,
            "provider": "local",
            "api_base": clean_base,
            "models": [],
            "message": f"未能取得本地模型清單 ({error_msg or '未發現可用模型'})，可手動輸入模型名稱"
        }
