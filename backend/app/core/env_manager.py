"""
環境變數與 .env 檔案管理核心模組 (Environment Manager)

負責讀取、解析、安全修改 .env 設定檔，並提供環境變數中文描述、分類元數據
以及伺服器重啟調度功能。
"""

import os
import sys
import time
import socket
import http.client
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

logger = logging.getLogger("designshield.env_manager")

# 尋找生效中的 .env 檔案路徑
def get_env_file_path() -> Path:
    candidates = [
        Path("/app/.env"),
        Path(__file__).resolve().parents[3] / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    # 若皆不存在，預設採用專案根目錄之 .env
    default_path = Path(__file__).resolve().parents[3] / ".env"
    return default_path


# 系統環境變數元數據設定 (含中文說明、範例與是否需重啟標記)
ENV_METADATA_DEFINITIONS: List[Dict[str, Any]] = [
    # 1. 網路與伺服器主機設定
    {
        "key": "SERVER_HOST",
        "category": "server",
        "category_name": "網路與伺服器主機設定",
        "label": "伺服器主機 IP 或網域",
        "description": "全系統集中主控之主機 IP 或網域名稱。更換機器、變更 IP 或綁定內部 DNS 網域時只需修改此處，相關認證跳轉與連線服務將自動套用。",
        "example": "192.168.1.16 或 designshield.local",
        "default": "192.168.1.16",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "FRONTEND_PORT",
        "category": "server",
        "category_name": "網路與伺服器主機設定",
        "label": "前端 Web 服務對外埠號",
        "description": "Docker 部署時前端 Nginx 對外暴露之 HTTP 連接埠號碼 (預設為 8080)。",
        "example": "8080",
        "default": "8080",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "LANGFUSE_NEXTAUTH_URL",
        "category": "server",
        "category_name": "網路與伺服器主機設定",
        "label": "Langfuse 認證跳轉網址",
        "description": "NextAuth 登入認證跳轉之完整絕對網址。需設定為外部使用者瀏覽器存取的位址 (例如 http://192.168.1.16:3000 或 http://${SERVER_HOST}:3000)，以避免登入後被導向使用者本機 localhost。",
        "example": "http://192.168.1.16:3000 或 http://${SERVER_HOST}:3000",
        "default": "http://${SERVER_HOST}:3000",
        "is_secret": False,
        "requires_restart": True,
    },

    # 2. LiteLLM 多模型服務串接 (LiteLLM Providers)
    {
        "key": "LITELLM_PROVIDER",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接 (LiteLLM)",
        "label": "LiteLLM 服務提供商 (Provider)",
        "description": "選擇當前啟用之大語言模型提供商。支援 Google Gemini (gemini)、OpenRouter (openrouter)、本地推理 (local / vLLM / Ollama)、OpenAI (openai)、Anthropic (anthropic)、Groq (groq)、DeepSeek (deepseek) 等相容 LiteLLM 之雲端與本地服務。",
        "example": "local",
        "default": "local",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "LOCAL_LLM_URL",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接 (LiteLLM)",
        "label": "API 服務端點 URL (API Base)",
        "description": "大語言模型 API 服務端點網址。本地端點預設為 http://192.168.1.5:8000/v1；OpenRouter 為 https://openrouter.ai/api/v1；Google Gemini/OpenAI 官方端點若無需自訂代理可留空。",
        "example": "http://192.168.1.5:8000/v1",
        "default": "http://192.168.1.5:8000/v1",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "LOCAL_LLM_API_KEY",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接 (LiteLLM)",
        "label": "API 存取金鑰 (API Key)",
        "description": "呼叫模型服務所需的 API Key (Google Gemini 填入 AIzaSy...、OpenRouter 填入 sk-or-v1-...、本地未啟用鑑權填 EMPTY)。",
        "example": "EMPTY",
        "default": "EMPTY",
        "is_secret": True,
        "requires_restart": True,
    },
    {
        "key": "LOCAL_LLM_MODEL",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接 (LiteLLM)",
        "label": "推理模型名稱 (Model)",
        "description": "指定 LiteLLM 調用的模型名稱。支援各家前綴 (如 gemini/gemini-2.5-flash、openrouter/google/gemini-2.5-flash、openai/qwen、deepseek/deepseek-chat 等)。支援依 Provider 即時查詢下拉選取或手動輸入。",
        "example": "openai/qwen",
        "default": "openai/qwen",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "GEMINI_API_KEY",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接 (LiteLLM)",
        "label": "Google Gemini 專屬金鑰 (選填)",
        "description": "Google AI Studio API Key。若填寫此項，LiteLLM 呼叫 gemini/* 系列模型時將自動以此金鑰進行鑑權。",
        "example": "AIzaSyxxxxxxxxxxxxxxxxxxxx",
        "default": "",
        "is_secret": True,
        "requires_restart": True,
    },
    {
        "key": "OPENROUTER_API_KEY",
        "category": "llm",
        "category_name": "LiteLLM 多模型服務串接 (LiteLLM)",
        "label": "OpenRouter 專屬金鑰 (選填)",
        "description": "OpenRouter API Key。若填寫此項，LiteLLM 呼叫 openrouter/* 系列模型時將自動以此金鑰進行鑑權。",
        "example": "sk-or-v1-xxxxxxxxxxxxxxxxxxxx",
        "default": "",
        "is_secret": True,
        "requires_restart": True,
    },

    # 3. Langfuse 觀測與追蹤服務 (Observability)
    {
        "key": "LANGFUSE_PUBLIC_KEY",
        "category": "langfuse",
        "category_name": "Langfuse 觀測與追蹤服務",
        "label": "Langfuse 公開金鑰 (Public Key)",
        "description": "用於後端 LiteLLM 自動上報 LLM 推理追蹤數據至 Langfuse 的公開金鑰。請至 Langfuse 儀表板中的專案 API Keys 取得。\n範例: LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx",
        "example": "pk-lf-xxxxxxxxxxxxxxxx",
        "default": "",
        "is_secret": False,
        "requires_restart": True,
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
        "requires_restart": True,
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
        "requires_restart": True,
    },

    # 4. 磁碟儲存與檔案生命週期 (Storage & Retention)
    {
        "key": "RETENTION_DAYS_UNSTARTED",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "未開始任務預設保留天數",
        "description": "尚未啟動正式檢測之任務（如僅完成預檢尚未確認規則）預設保留天數。超過此天數將自動清理該任務及其上傳檔案與暫存目錄。",
        "example": "2",
        "default": "2",
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
        "is_secret": False,
        "requires_restart": False,
    },
    {
        "key": "STORAGE_DIR",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "儲存根目錄路徑",
        "description": "系統所有上傳、解壓縮中繼及檢測報告檔案存放之本機或掛載根目錄。",
        "example": "./storage 或 /app/storage",
        "default": "./storage",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "UPLOAD_DIR",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "原始上傳暫存目錄",
        "description": "使用者由前端上傳之 Cadence OrCAD 電路圖封裝檔暫存目錄。",
        "example": "./storage/uploads",
        "default": "./storage/uploads",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "STAGING_DIR",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "解壓與解析暫存目錄",
        "description": "封裝檔解壓縮後之 OrCAD XML、Allegro 網表及圖譜中繼資料處理目錄。",
        "example": "./storage/staging",
        "default": "./storage/staging",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "REPORT_DIR",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "DRC 報告產出目錄",
        "description": "DBOS 完成線路規則檢查後，生成之 HTML/JSON/Markdown 報告存放目錄。",
        "example": "./storage/reports",
        "default": "./storage/reports",
        "is_secret": False,
        "requires_restart": True,
    },

    # 5. 資料庫連線配置 (Database)
    {
        "key": "DATABASE_URL",
        "category": "database",
        "category_name": "核心資料庫連線配置",
        "label": "主資料庫連線字串",
        "description": "PostgreSQL 或 SQLite 資料庫連線 URL，儲存規則庫、分析任務、 step_status 與產出成果。",
        "example": "postgresql://designshield:shield_secret_2026@postgres:5432/designshield_db",
        "default": "postgresql://designshield:shield_secret_2026@postgres:5432/designshield_db",
        "is_secret": True,
        "requires_restart": True,
    },
    {
        "key": "DBOS_SYSTEM_DATABASE_URL",
        "category": "database",
        "category_name": "核心資料庫連線配置",
        "label": "DBOS 系統狀態資料庫連線",
        "description": "供 DBOS 原生 Durable Execution 引擎儲存斷點接續、Workflow 狀態與排程紀錄之資料庫連線字串。",
        "example": "postgresql://designshield:shield_secret_2026@postgres:5432/designshield_db",
        "default": "postgresql://designshield:shield_secret_2026@postgres:5432/designshield_db",
        "is_secret": True,
        "requires_restart": True,
    },
    {
        "key": "POSTGRES_HOST_PORT",
        "category": "database",
        "category_name": "核心資料庫連線配置",
        "label": "PostgreSQL 主機對外埠號",
        "description": "Docker 部署時 PostgreSQL 映射至主機的連接埠 (預設為 5433 避免與主機既有 5432 埠號衝突)。",
        "example": "5433",
        "default": "5433",
        "is_secret": False,
        "requires_restart": True,
    },
]


def parse_raw_env_file(file_path: Path) -> Dict[str, str]:
    """解析 .env 檔案為鍵值對 (不展開變數)"""
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
                # 去除外層引號
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                env_dict[k] = v
    return env_dict


def get_all_env_settings() -> Dict[str, Any]:
    """
    取得所有 .env 設定項目，包含完整中文詮釋資料與目前數值
    """
    env_path = get_env_file_path()
    raw_env = parse_raw_env_file(env_path)

    items = []
    known_keys = set()

    for meta in ENV_METADATA_DEFINITIONS:
        key = meta["key"]
        known_keys.add(key)
        # 優先取用 .env 中的值，其次取用 os.environ，最後取用預設值
        current_val = raw_env.get(key)
        if current_val is None:
            current_val = os.environ.get(key, meta.get("default", ""))

        items.append({
            "key": key,
            "value": current_val,
            "category": meta["category"],
            "category_name": meta["category_name"],
            "label": meta["label"],
            "description": meta["description"],
            "example": meta["example"],
            "default": meta.get("default", ""),
            "is_secret": meta.get("is_secret", False),
            "requires_restart": meta.get("requires_restart", True)
        })

    # 若 .env 中有自訂未定義項目，一併附帶於自訂分類
    for k, v in raw_env.items():
        if k not in known_keys:
            items.append({
                "key": k,
                "value": v,
                "category": "custom",
                "category_name": "其他自訂設定 (Custom Settings)",
                "label": k,
                "description": f"自訂環境變數項目：{k}",
                "example": "",
                "default": "",
                "is_secret": "KEY" in k.upper() or "SECRET" in k.upper() or "PASSWORD" in k.upper(),
                "requires_restart": True
            })

    # 取得分類列表
    categories = [
        {"id": "server", "name": "網路與伺服器主機設定", "icon": "pi pi-globe"},
        {"id": "llm", "name": "LiteLLM 多模型服務串接 (LiteLLM)", "icon": "pi pi-microchip-ai"},
        {"id": "langfuse", "name": "Langfuse 觀測與追蹤服務", "icon": "pi pi-chart-line"},
        {"id": "storage", "name": "檔案儲存與生命週期管理", "icon": "pi pi-database"},
        {"id": "database", "name": "核心資料庫連線配置", "icon": "pi pi-server"},
    ]

    return {
        "env_file_path": str(env_path),
        "items": items,
        "categories": categories,
        "total_count": len(items)
    }


def save_env_settings(updates: Dict[str, str]) -> Dict[str, Any]:
    """
    將設定變更安全寫入 .env 檔案中，保留既有註解排版，並計算受影響的重啟原因清單。
    """
    env_path = get_env_file_path()
    
    # 建立元數據對照表，判斷哪些 key 變更需要重啟
    restart_map = {meta["key"]: meta.get("requires_restart", True) for meta in ENV_METADATA_DEFINITIONS}
    
    current_raw = parse_raw_env_file(env_path)
    changed_keys = []
    restart_reasons = []

    for k, new_v in updates.items():
        old_v = current_raw.get(k, "")
        if str(new_v) != str(old_v):
            changed_keys.append(k)
            if restart_map.get(k, True):
                restart_reasons.append(k)

    # 讀取原本檔案內容行
    existing_lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    # 行為追蹤：更新既有行或追加新行
    updated_keys_set = set()
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in updates:
                if k not in updated_keys_set:
                    new_lines.append(f"{k}={updates[k]}\n")
                    updated_keys_set.add(k)
                # 若檔案中已有更新過此 key，忽略後續重複行
                continue
        new_lines.append(line)

    # 若有更新中的項目原本不在檔案中，將其追加至最後
    remaining_keys = [k for k in updates.keys() if k not in updated_keys_set]
    if remaining_keys:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append("\n# === 新增設定項目 ===\n")
        for k in remaining_keys:
            new_lines.append(f"{k}={updates[k]}\n")

    # 確保目錄存在並安全寫入
    env_path.parent.mkdir(parents=True, exist_ok=True)
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 同步更新執行時期 os.environ
    for k, v in updates.items():
        os.environ[k] = str(v)

    # 重新熱載入 dotenv
    load_dotenv(dotenv_path=env_path, override=True)

    # 同步更新 Pydantic Settings 單例物件
    try:
        from backend.app.core.config import settings
        for k, v in updates.items():
            if hasattr(settings, k):
                orig_val = getattr(settings, k)
                if isinstance(orig_val, bool):
                    setattr(settings, k, str(v).lower() in ("true", "1", "yes", "t"))
                elif isinstance(orig_val, int):
                    try:
                        setattr(settings, k, int(v))
                    except (ValueError, TypeError):
                        setattr(settings, k, v)
                else:
                    setattr(settings, k, str(v))
    except Exception as e:
        logger.warning(f"Failed to dynamically patch settings singleton: {e}")

    # 若更新了 Langfuse 金鑰，自動重新載入 LiteLLM callbacks
    if "LANGFUSE_PUBLIC_KEY" in updates or "LANGFUSE_SECRET_KEY" in updates:
        try:
            from backend.app.engine.rules import llm
            if updates.get("LANGFUSE_PUBLIC_KEY") and updates.get("LANGFUSE_SECRET_KEY"):
                llm._LANGFUSE_INITIALIZED = False
                llm._init_langfuse_if_configured()
        except Exception as e:
            logger.warning(f"Failed to reinit langfuse callbacks: {e}")

    requires_restart = len(restart_reasons) > 0

    return {
        "success": True,
        "changed_keys": changed_keys,
        "requires_restart": requires_restart,
        "restart_reasons": restart_reasons,
        "message": "設定已成功寫入 .env 檔案！" + (
            f" 警告：變更了需重啟生效的項目 ({', '.join(restart_reasons)})，請點擊「重啟伺服器」以套用新設定。"
            if requires_restart else " 設定已動態生效。"
        )
    }


def call_docker_unix_socket(method: str, path: str) -> Optional[int]:
    """透過本機 /var/run/docker.sock 執行 Docker API 請求"""
    socket_path = "/var/run/docker.sock"
    if not os.path.exists(socket_path):
        return None

    class UnixConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(socket_path)

    try:
        conn = UnixConnection("localhost", timeout=10)
        conn.request(method, path)
        res = conn.getresponse()
        status = res.status
        conn.close()
        return status
    except Exception as e:
        logger.error(f"Error calling Docker socket: {e}")
        return None


def trigger_server_restart() -> Dict[str, Any]:
    """
    執行伺服器重啟調度。
    立即向客戶端返回成功確認 (HTTP 200)，並在背景執行緒中延遲執行重啟，
    確保 HTTP 回應順利傳輸完畢，不致造成連線掛死或超時。
    """
    logger.info("Triggering asynchronous server restart...")

    def _restart_worker():
        # 延遲 0.8 秒，保證當前 HTTP 請求回應已完整傳回瀏覽器
        time.sleep(0.8)

        # 1. 優先嘗試透過 Docker Unix Socket 重啟自身容器
        if os.path.exists("/var/run/docker.sock"):
            hostname = os.environ.get("HOSTNAME", "").strip()
            container_candidates = []
            if hostname:
                container_candidates.append(hostname)
            container_candidates.extend(["designshield-backend-dev", "designshield-backend"])

            for cname in container_candidates:
                try:
                    logger.info(f"Attempting to restart Docker container: {cname}")
                    status = call_docker_unix_socket("POST", f"/containers/{cname}/restart?t=2")
                    if status in (200, 201, 204):
                        logger.info(f"Docker container {cname} restart initiated successfully (status {status})")
                        return
                except Exception as e:
                    logger.info(f"Docker socket call for {cname} disconnected as expected: {e}")
                    return

            logger.warning("Docker API restart call did not succeed, falling back to process exit / touch reload")

        # 2. 若無 docker.sock 或 Docker 重啟未成功，嘗試觸發 Uvicorn 熱重載 (touch main.py)
        try:
            main_py = Path(__file__).resolve().parents[1] / "main.py"
            if main_py.exists():
                main_py.touch()
                logger.info(f"Touched {main_py} to trigger Uvicorn WatchFiles reload")
        except Exception as e:
            logger.warning(f"Failed to touch main.py: {e}")

        # 3. 延遲 1 秒後退出程序，觸發 Docker restart: always 或 Supervisor 重啟
        time.sleep(1.0)
        logger.info("Exiting process to trigger auto-restart...")
        os._exit(0)

    import threading
    t = threading.Thread(target=_restart_worker, daemon=True)
    t.start()

    return {
        "success": True,
        "mode": "async_restart",
        "message": "已排程後端服務重啟，容器即將重新加載新設定。"
    }


def fetch_available_llm_models(
    provider: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    即時向設定的 Provider 或端點查詢可用的 LLM 模型清單
    支援 Google Gemini、OpenRouter、本地推理伺服器 (OpenAI 協定/Ollama)、OpenAI、Anthropic、Groq、DeepSeek 等。
    """
    import urllib.request
    import json

    env_dict = parse_raw_env_file(get_env_file_path())

    p = (provider or env_dict.get("LITELLM_PROVIDER", os.environ.get("LITELLM_PROVIDER", "local"))).strip().lower()

    # 若未指定 provider 但 api_base 有明確特徵時進行推斷
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
        gemini_key = api_key or env_dict.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        if not gemini_key or gemini_key == "EMPTY":
            gemini_key = env_dict.get("LOCAL_LLM_API_KEY", "")
        if gemini_key and str(gemini_key).strip() and str(gemini_key).strip() != "EMPTY":
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
            "message": "成功取得 Google Gemini 官方支援模型清單"
        }

    # 2. OpenRouter
    elif p == "openrouter":
        curated_openrouter = [
            "openrouter/google/gemini-2.5-flash",
            "openrouter/google/gemini-2.5-pro",
            "openrouter/anthropic/claude-3.5-sonnet",
            "openrouter/anthropic/claude-3.5-haiku",
            "openrouter/openai/gpt-4o",
            "openrouter/openai/gpt-4o-mini",
            "openrouter/meta-llama/llama-3.3-70b-instruct",
            "openrouter/deepseek/deepseek-chat",
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen-2.5-72b-instruct"
        ]
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "DesignShield/0.1.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    fetched = []
                    for m in data.get("data", []):
                        mid = m.get("id")
                        if mid:
                            fetched.append(f"openrouter/{mid}")
                    if fetched:
                        all_models = list(dict.fromkeys(curated_openrouter + fetched[:25]))
                        return {
                            "success": True,
                            "provider": "openrouter",
                            "api_base": "https://openrouter.ai/api/v1",
                            "models": all_models,
                            "message": f"成功自 OpenRouter 即時取得可用模型清單 (共 {len(all_models)} 個)"
                        }
        except Exception as e:
            logger.debug("Failed to query live OpenRouter models: %s", e)

        return {
            "success": True,
            "provider": "openrouter",
            "api_base": "https://openrouter.ai/api/v1",
            "models": curated_openrouter,
            "message": "成功取得 OpenRouter 推薦主流模型清單"
        }

    # 3. OpenAI
    elif p == "openai":
        openai_models = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/o1-preview",
            "openai/o1-mini",
            "openai/gpt-4-turbo"
        ]
        return {
            "success": True,
            "provider": "openai",
            "api_base": "https://api.openai.com/v1",
            "models": openai_models,
            "message": "成功取得 OpenAI 官方支援模型清單"
        }

    # 4. Anthropic
    elif p in ("anthropic", "claude"):
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
            "message": "成功取得 Anthropic 官方支援模型清單"
        }

    # 5. Groq
    elif p == "groq":
        groq_models = [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/deepseek-r1-distill-llama-70b",
            "groq/mixtral-8x7b-32768"
        ]
        return {
            "success": True,
            "provider": "groq",
            "api_base": "https://api.groq.com/openai/v1",
            "models": groq_models,
            "message": "成功取得 Groq 高速推理模型清單"
        }

    # 6. DeepSeek
    elif p == "deepseek":
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
        api_base = env_dict.get("LOCAL_LLM_URL", os.environ.get("LOCAL_LLM_URL", "http://192.168.1.5:8000/v1"))
    if not api_key:
        api_key = env_dict.get("LOCAL_LLM_API_KEY", os.environ.get("LOCAL_LLM_API_KEY", "EMPTY"))

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

