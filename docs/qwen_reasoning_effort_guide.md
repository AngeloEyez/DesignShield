# Qwen 思考深度 (Reasoning Effort) 與 vLLM 調用指南

本文檔記錄 Qwen 系列模型（特別是支援思考鏈之 Qwen3.8 / QwQ 等推理模型）在搭配 vLLM 部署時，自定義思考深度（Reasoning Effort）的參數機制、繞過 vLLM Pydantic 驗證的方法、LiteLLM 整合方式，以及獨立 API Proxy 包裝方案。

---

## 1. 背景與底層機制解析

### 1.1 衝突核心：OpenAI API 規範 vs Qwen 自定義參數
* **vLLM 的頂層 Pydantic 驗證**：
  vLLM 遵循 OpenAI 相容 API 規格，其 Request Body 驗證模型（`ChatCompletionRequest`）將 `reasoning_effort` 限制為固定枚舉值：`Literal["low", "medium", "high"]`。
  若在 HTTP 請求頂層直接帶入 `"reasoning_effort": "xhigh"`，vLLM 的 Pydantic 驗證器會直接攔截並拋出 **HTTP 422 Unprocessable Entity**（`Input should be 'low', 'medium' or 'high'`）。
* **Qwen Jinja2 Chat Template 機制**：
  Qwen 模型的 Hugging Face `tokenizer_config.json` 內部採用 Jinja2 模板來處理思考標籤（`<think>...</think>`）。模板支援多個擴展變數：
  1. `reasoning_effort`：支援 `"low"`, `"medium"`, `"high"`, `"xhigh"`。
  2. `enable_thinking`：布林值（`true` / `false`），用來完全開啟或關閉思考標籤生成。
* **繞過驗證的核心秘密：`chat_template_kwargs`**：
  vLLM 在 `ChatCompletionRequest` 中提供了一個自由字典欄位：
  ```python
  chat_template_kwargs: Optional[Dict[str, Any]] = None
  ```
  Pydantic 不會對 `chat_template_kwargs` 內部的 Key/Value 進行嚴格 enum 限制。vLLM 會將該字典解包直接傳入 Hugging Face 的 `tokenizer.apply_chat_template(..., **chat_template_kwargs)`。因此，透過 `chat_template_kwargs` 可以無損將自定義參數注入 Jinja2 模板！

---

## 2. 三種核心調用方式與 curl 範例

### 方式 1：輕度思考 (low) 或 標準思考 (medium)
* **原理**：`low` 與 `medium` 屬於標準 OpenAI 枚舉值，可通過 vLLM 頂層 Pydantic 驗證，並由 vLLM 傳入 template。
* **適用情境**：常規邏輯推理、一般性問答，平衡推理深度與 Token 成本。

```bash
# 輕度思考 (low)
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "請說明量子電腦的基本原理"}],
    "reasoning_effort": "low"
  }'

# 標準思考 (medium)
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "請分析此電路介面的信號完整性問題"}],
    "reasoning_effort": "medium"
  }'
```

---

### 方式 2：強制指定極致深思 (xhigh)（繞過 vLLM Pydantic 檢查）
* **原理**：將 `reasoning_effort: "xhigh"` 改放在 `chat_template_kwargs` 中傳遞，繞過頂層欄位驗證，直接注入 Jinja2 模板。
* **原生預設行為提醒**：**若請求中完全不帶 `reasoning_effort` 或 `enable_thinking`，Qwen 原生預設行為即等同於 `xhigh`（完整思考）**。
* **適用情境**：複雜演算法證明、跨多個訊號網絡的複雜電路拓撲分析。

```bash
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "請分析此複雜演算法的時間與空間複雜度並證明"}],
    "chat_template_kwargs": {
      "reasoning_effort": "xhigh"
    }
  }'
```

---

### 方式 3：完全關閉思考（提升互動速度、不浪費 Token）
* **原理**：將 `chat_template_kwargs` 的 `enable_thinking` 設為 `false`。Jinja 模板在組裝 Prompt 時不會引導輸出 `<think>` 標籤，模型會像一般 Instruct 模型一樣直接輸出回答。
* **優勢**：
  * **顯著降低延遲**：從幾十秒的推論時間縮短至數百毫秒～數秒。
  * **大幅節省 Token**：不產生任何 Reasoning Tokens，適合高併發或即時問答。
* **適用情境**：簡易問答、分類器任務（如元器件類別分類）、結構化 JSON 輸出抽取。

```bash
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "1+1=?"}],
    "chat_template_kwargs": {
      "enable_thinking": false
    }
  }'
```

---

## 3. 調用模式矩陣對照表

| 模式名稱 | 傳遞參數位置 | 參數範例 | 預估思考 Token | 回應延遲 | 適用場景 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **關閉思考 (Fast)** | `chat_template_kwargs` | `{"enable_thinking": false}` | 0 tokens | 最快 (~1-3s) | 元件分類、簡單查詢、即時對話 |
| **輕度思考 (Low)** | 頂層 Request Body | `"reasoning_effort": "low"` | ~100 - 500 tokens | 快 (~3-8s) | 一般 DRC 規則判斷、常見硬體模式確認 |
| **標準思考 (Medium)** | 頂層 Request Body | `"reasoning_effort": "medium"` | ~500 - 1500 tokens | 中等 (~8-20s) | 綜合架構檢查、具有分支邏輯的電路判斷 |
| **極致深思 (xhigh)** | `chat_template_kwargs` | `{"reasoning_effort": "xhigh"}` | > 2000 tokens | 較慢 (~20-60s) | 複雜數學證明、多介面交互影響深度診斷 |
| **預設未指定** | 無 | *(未帶任何思考參數)* | 原生預設 (等同 xhigh) | 較慢 | 預設行為 |

---

## 4. LiteLLM 處理方式評估與實作

LiteLLM 支援透傳非標準參數至底層 Provider，有以下三種落地方案：

### 4.1 方案 A：LiteLLM Python SDK 的 `extra_body`（最直接、零架構更動）
在 Python 中呼叫 LiteLLM 時，透過 `extra_body` 可以將任意字典透傳至 HTTP 請求 Body：

```python
import litellm

# 1. 完全關閉思考
response = litellm.completion(
    model="openai/Qwen3.8-27B",
    messages=[{"role": "user", "content": "電容 C1 的封裝規格是什麼？"}],
    api_base="http://192.168.1.5:8000/v1",
    api_key="EMPTY",
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": False
        }
    }
)

# 2. 強制指定 xhigh 極致深思
response = litellm.completion(
    model="openai/Qwen3.8-27B",
    messages=[{"role": "user", "content": "請深度分析整個電源樹的反向灌電風險"}],
    api_base="http://192.168.1.5:8000/v1",
    api_key="EMPTY",
    extra_body={
        "chat_template_kwargs": {
            "reasoning_effort": "xhigh"
        }
    }
)

# 3. 輕度思考 (low)
response = litellm.completion(
    model="openai/Qwen3.8-27B",
    messages=[{"role": "user", "content": "檢查 MicroSD 引腳模式"}],
    api_base="http://192.168.1.5:8000/v1",
    api_key="EMPTY",
    reasoning_effort="low"
)
```

---

### 4.2 方案 B：LiteLLM Proxy 虛擬模型路由（推薦：上游呼叫者完全免改 Code）
若系統使用獨立的 LiteLLM Proxy，可在 `config.yaml` 定義不同別名模型：

```yaml
model_list:
  # 快速不思考模式 (適合 DRC 掃描與元件分類)
  - model_name: qwen-fast
    litellm_params:
      model: openai/Qwen3.8-27B
      api_base: http://192.168.1.5:8000/v1
      api_key: EMPTY
      extra_body:
        chat_template_kwargs:
          enable_thinking: false

  # 標準思考模式
  - model_name: qwen-balanced
    litellm_params:
      model: openai/Qwen3.8-27B
      api_base: http://192.168.1.5:8000/v1
      api_key: EMPTY
      reasoning_effort: medium

  # 極致深思模式
  - model_name: qwen-deep
    litellm_params:
      model: openai/Qwen3.8-27B
      api_base: http://192.168.1.5:8000/v1
      api_key: EMPTY
      extra_body:
        chat_template_kwargs:
          reasoning_effort: "xhigh"
```

* **優勢**：前端、後端各規則、LangChain、OpenWebUI 等所有用戶端，只需將請求模型改為 `qwen-fast` 或 `qwen-deep`，完全不需要自行處理由 HTTP Body 傳送的客製化參數！

---

### 4.3 方案 C：LiteLLM Pre-Call Callback（自動參數轉換攔截器）
若希望用戶端依舊傳入標準 OpenAI 格式（例如 `"reasoning_effort": "xhigh"` 或 `"none"`），但透過 LiteLLM 中間件自動修正：

```python
from litellm.integrations.custom_logger import CustomLogger

class QwenReasoningEffortInterceptor(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache_key, data, call_type):
        model = data.get("model", "")
        if "qwen" in model.lower():
            effort = data.get("reasoning_effort")
            if effort == "xhigh":
                # 從頂層移除以避免 vLLM Pydantic 報錯，並塞入 extra_body
                data.pop("reasoning_effort", None)
                data.setdefault("extra_body", {}).setdefault("chat_template_kwargs", {})["reasoning_effort"] = "xhigh"
            elif effort in ("none", "off", "disabled"):
                data.pop("reasoning_effort", None)
                data.setdefault("extra_body", {}).setdefault("chat_template_kwargs", {})["enable_thinking"] = False
        return data

# 掛載攔截器
import litellm
litellm.callbacks = [QwenReasoningEffortInterceptor()]
```

---

## 5. 包裝專屬 API Adapter (Gateway Proxy) 評估與實作

### 5.1 是否需要包裝專屬 API？
| 評估面向 | 採用 LiteLLM / 內建封裝 | 包裝獨立 API Gateway / Adapter |
| :--- | :--- | :--- |
| **架構複雜度** | **低**（現有架構直接可用） | **中**（多一個獨立微服務需維護） |
| **跨工具相容性** | 依賴調用方使用 LiteLLM 或改 prompt/body | **最高**（任何只認 OpenAI 規格的軟體均可透明串接） |
| **維護成本** | 僅需更新 Python 工具函式 | 需維護 Docker 容器、健康檢查、網路轉發 |
| **適用情境** | 專案主要以 Python 後端呼叫為主 | 有多種異質工具（如 VSCode 外掛、Dify、Chatbox）直連本地模型 |

### 5.2 獨立 API Adapter 參考實作 (FastAPI + httpx)
若決定建立一個輕量級的中繼 Gateway（例如監聽於 `http://localhost:8001/v1`，轉發至 `http://192.168.1.5:8000/v1`）：

```python
"""
Qwen-to-vLLM Reasoning Adapter
提供標準 OpenAI 相容介面，自動將 reasoning_effort 轉譯為 vLLM 可接受之 chat_template_kwargs。
"""
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response
import httpx

app = FastAPI(title="Qwen Reasoning Adapter")
VLLM_BACKEND_URL = "http://192.168.1.5:8000"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    
    # 提取與轉換 reasoning_effort
    effort = payload.get("reasoning_effort")
    chat_template_kwargs = payload.setdefault("chat_template_kwargs", {})
    
    if effort == "xhigh":
        # 移除頂層避免 vLLM Pydantic 422 錯誤
        payload.pop("reasoning_effort", None)
        chat_template_kwargs["reasoning_effort"] = "xhigh"
    elif effort in ("none", "off", "disable", "disabled"):
        payload.pop("reasoning_effort", None)
        chat_template_kwargs["enable_thinking"] = False
    elif payload.get("enable_thinking") is False:
        chat_template_kwargs["enable_thinking"] = False
        payload.pop("enable_thinking", None)
        
    # 轉發請求至 vLLM
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    client = httpx.AsyncClient(timeout=300.0)
    
    if payload.get("stream", False):
        async def forward_stream():
            async with client.stream("POST", f"{VLLM_BACKEND_URL}/v1/chat/completions", json=payload, headers=headers) as upstream:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            await client.aclose()
        return StreamingResponse(forward_stream(), media_type="text/event-stream")
    else:
        upstream_resp = await client.post(f"{VLLM_BACKEND_URL}/v1/chat/completions", json=payload, headers=headers)
        await client.aclose()
        return Response(content=upstream_resp.content, status_code=upstream_resp.status_code, media_type="application/json")
```

---

## 6. DesignShield 系統實際落地實作 (LLMProfile 架構)

系統已於 `backend/app/engine/rules/llm.py` 中完整實作 **情境策略 (Preset Profiles)** 架構與智慧相容解析器：

### 6.1 Preset Profile 規格矩陣
| Profile | 溫度 (Temperature) | 思考設定 (Qwen / local) | 思考設定 (雲端 Provider) | DesignShield 指派任務 | 典型單次耗時 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`FAST`** | `0.0` | `chat_template_kwargs: {"enable_thinking": False}` | 不帶思考標籤，低溫 | **元件模糊分類器 (`ComponentClassifier`)** | ~1 - 2 秒 (極速) |
| **`BALANCED`** | `0.1` | `reasoning_effort: "low"` | `reasoning_effort: "low"` | **三大 DRC 規則 (SD/復位/電平轉換)** | ~4 - 8 秒 (平衡) |
| **`DEEP`** | `0.1` | `chat_template_kwargs: {"reasoning_effort": "xhigh"}` | `reasoning_effort: "high"` | **全板電源樹/複雜跨域診斷 (預留)** | ~20 - 45 秒 (深度) |

### 6.2 模組呼叫方式

#### 1. 結構化批次分類器 (`backend/app/engine/classifier.py`)
```python
from backend.app.engine.rules.llm import call_litellm_completion, LLMProfile

# 自動套用 FAST Profile (temperature=0.0, enable_thinking=False)
response = call_litellm_completion(
    prompt=prompt,
    timeout=600.0,
    max_tokens=4000,
    profile=LLMProfile.FAST
)
```

#### 2. DRC 審查規則函式 (`backend/app/engine/rules/llm.py`)
```python
from backend.app.engine.rules.llm import call_local_llm_reasoning, LLMProfile

# 預設即為 BALANCED (亦可明確指定)
llm_resp = call_local_llm_reasoning(
    prompt=prompt,
    profile=LLMProfile.BALANCED
)
```

### 6.3 智慧跨 Provider 相容機制 (Multi-Provider Graceful Fallback)
解析函式 `resolve_llm_profile_params` 具備自動感應能力：
* 當模型為 Qwen 或 Provider 為本地端點時，自動為 `FAST` 生成 `enable_thinking: False`，為 `DEEP` 生成繞過 vLLM Pydantic 限制的 `chat_template_kwargs: {"reasoning_effort": "xhigh"}`。
* 當切換至雲端模型（如 Gemini、OpenAI、Claude）時，自動回退或平移至標準相容參數，避免傳送未知欄位導致雲端 SDK 拋錯。

