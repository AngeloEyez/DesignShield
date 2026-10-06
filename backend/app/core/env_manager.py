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

    # 2. 本地大語言模型推理 (Local LLM)
    {
        "key": "LOCAL_LLM_URL",
        "category": "llm",
        "category_name": "本地大語言模型推理 (Local LLM)",
        "label": "本地 LLM 服務 API 端點",
        "description": "本地大語言模型推理伺服器連線端點 (需相容 OpenAI 協定，支援 vLLM、Ollama 或 llama.cpp 等服務)。",
        "example": "http://192.168.1.5:8000/v1",
        "default": "http://192.168.1.5:8000/v1",
        "is_secret": False,
        "requires_restart": True,
    },
    {
        "key": "LOCAL_LLM_API_KEY",
        "category": "llm",
        "category_name": "本地大語言模型推理 (Local LLM)",
        "label": "本地 LLM 存取金鑰",
        "description": "呼叫本地模型推理服務所需的 API Key。若本地伺服器未啟用鑑權驗證，填入 EMPTY 即可。",
        "example": "EMPTY",
        "default": "EMPTY",
        "is_secret": True,
        "requires_restart": True,
    },
    {
        "key": "LOCAL_LLM_MODEL",
        "category": "llm",
        "category_name": "本地大語言模型推理 (Local LLM)",
        "label": "LLM 推理模型名稱",
        "description": "呼叫本地推理伺服器時指定的模型識別名稱 (例如 openai/qwen 或 openai/local-model)。支援自伺服器即時查詢可用模型列表下拉選取或手動輸入。",
        "example": "openai/qwen",
        "default": "openai/qwen",
        "is_secret": False,
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
        "key": "UPLOAD_RETENTION_DAYS",
        "category": "storage",
        "category_name": "檔案儲存與生命週期管理",
        "label": "暫存檔案保留天數",
        "description": "上傳之 OrCAD 原始壓縮檔與暫存檔案最長保留天數。超過此天數之檔案將被垃圾清理機制自動回收以釋放磁碟空間。",
        "example": "7",
        "default": "7",
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
        {"id": "llm", "name": "本地大語言模型推理 (Local LLM)", "icon": "pi pi-microchip-ai"},
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
                new_lines.append(f"{k}={updates[k]}\n")
                updated_keys_set.add(k)
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
                # 類型轉換
                orig_type = type(getattr(settings, k))
                try:
                    setattr(settings, k, orig_type(v))
                except Exception:
                    setattr(settings, k, v)
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
    若運行於 Docker 容器內且掛載了 docker.sock，調用 Docker 守護進程重新啟動後端容器；
    若在本地環境運行，則排程發出中斷重啟信號。
    """
    logger.info("Triggering server restart action...")
    
    # 檢查是否有 docker.sock
    has_sock = os.path.exists("/var/run/docker.sock")
    
    if has_sock:
        # 重啟 designshield-backend 容器
        status = call_docker_unix_socket("POST", "/containers/designshield-backend/restart")
        if status in (204, 200, 201):
            return {
                "success": True,
                "mode": "docker_socket",
                "message": "已成功透過 Docker 守護進程發送後端容器重啟訊號！"
            }
        else:
            logger.warning(f"Docker API returned status {status}, falling back to process exit")

    # 非 docker.sock 或呼叫失敗時，透過延遲退出程序觸發 Docker (restart: always) 或 supervisor 自動重啟
    def _delayed_exit():
        time.sleep(1.0)
        logger.info("Exiting process to trigger auto-restart...")
        os._exit(0)

    import threading
    t = threading.Thread(target=_delayed_exit, daemon=True)
    t.start()

    return {
        "success": True,
        "mode": "process_exit",
        "message": "已排程後端程序重啟，容器或行程管理器即將自動重新加載。"
    }


def fetch_available_llm_models(api_base: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    即時向設定的 LOCAL_LLM_URL 查詢可用的 LLM 模型清單 (支援 OpenAI 相容協定與 Ollama)
    """
    import urllib.request
    import json

    if not api_base:
        env_dict = parse_raw_env_file(get_env_file_path())
        api_base = env_dict.get("LOCAL_LLM_URL", os.environ.get("LOCAL_LLM_URL", "http://192.168.1.5:8000/v1"))
    if not api_key:
        env_dict = parse_raw_env_file(get_env_file_path())
        api_key = env_dict.get("LOCAL_LLM_API_KEY", os.environ.get("LOCAL_LLM_API_KEY", "EMPTY"))

    clean_base = str(api_base).strip().rstrip("/")
    # 建構 models 端點
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
                # OpenAI 協定: {"data": [{"id": "model-id"}, ...]}
                if "data" in data and isinstance(data["data"], list):
                    for m in data["data"]:
                        if isinstance(m, dict) and "id" in m:
                            models.append(str(m["id"]))
                # Ollama 協定: {"models": [{"name": "model-name"}, ...]}
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
        # 去重並排序
        sorted_models = sorted(list(set(models)))
        return {
            "success": True,
            "api_base": clean_base,
            "models": sorted_models,
            "message": f"成功自 LLM 伺服器取得 {len(sorted_models)} 個可用模型"
        }
    else:
        return {
            "success": False,
            "api_base": clean_base,
            "models": [],
            "message": f"未能取得模型清單 ({error_msg or '未發現可用模型'})，可手動輸入模型名稱"
        }

