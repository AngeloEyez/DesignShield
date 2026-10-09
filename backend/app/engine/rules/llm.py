"""
大語言模型邏輯推理 DRC 檢測模組 (LLM Reasoning DRC Rules)

透過 LiteLLM 呼叫本地 192.168.1.5:8000/v1 進行語意分析與介面模式驗證，具備優雅降級與 Token 流量控制。
"""

import json
import time
import uuid
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import networkx as nx
import litellm

from backend.app.core.config import settings

logger = logging.getLogger("designshield.llm")


class LLMProfile(str, Enum):
    """LLM 思考模式與任務情境預設設定 (Preset Profiles)"""
    FAST = "FAST"          # 結構化分類、極速、關閉思考 (enable_thinking=False, temp=0.0)
    BALANCED = "BALANCED"  # 標準 DRC 審查、中輕度思考 (reasoning_effort=low, temp=0.1)
    DEEP = "DEEP"          # 極致深思、複雜拓撲診斷 (reasoning_effort=xhigh 繞過, temp=0.1)


def resolve_llm_profile_params(
    profile: Union[str, LLMProfile] = LLMProfile.BALANCED,
    model: str = "",
    provider: str = ""
) -> Dict[str, Any]:
    """
    根據任務 Profile 解析溫度與思考參數，具備跨 Provider 智慧相容機制。
    
    Qwen (local vLLM):
      - FAST: temperature=0.0, extra_body={"chat_template_kwargs": {"enable_thinking": False}}
      - BALANCED: temperature=0.1, reasoning_effort="low"
      - DEEP: temperature=0.1, extra_body={"chat_template_kwargs": {"reasoning_effort": "xhigh"}}
      
    其他雲端 Provider (如 Gemini, OpenAI, Claude 等):
      - FAST: temperature=0.0
      - BALANCED: temperature=0.1, reasoning_effort="low"
      - DEEP: temperature=0.1, reasoning_effort="high"
    """
    prof = profile.value if isinstance(profile, LLMProfile) else str(profile).upper()
    is_qwen_or_local = (
        provider.lower() == "local" or
        "qwen" in model.lower() or
        "localhost" in model.lower() or
        "192.168." in model.lower()
    )
    
    params: Dict[str, Any] = {}
    
    if prof == "FAST":
        params["temperature"] = 0.0
        if is_qwen_or_local:
            params["extra_body"] = {
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
    elif prof == "DEEP":
        params["temperature"] = 0.1
        if is_qwen_or_local:
            params["extra_body"] = {
                "chat_template_kwargs": {
                    "reasoning_effort": "xhigh"
                }
            }
        else:
            params["reasoning_effort"] = "high"
    else:  # BALANCED
        params["temperature"] = 0.1
        params["reasoning_effort"] = "low"
        
    return params



def extract_interface_subgraph_context(G: nx.Graph, keyword: str = "SD") -> Dict[str, Any]:
    """
    從全域電路圖譜中抽取指定介面或關鍵字之周邊子圖上下文
    
    Args:
        G: 全域 NetworkX 圖譜
        keyword: 介面關鍵字 (如 SD, RESET, I2C, SPI)
        
    Returns:
        Dict: 包含受測 components 與 nets 清單及引腳關係
    """
    target_nets = [
        n for n, d in G.nodes(data=True)
        if d.get("type") == "net" and keyword.lower() in d.get("net_name", "").lower()
    ]
    
    target_comps = set()
    connections = []
    
    for net in target_nets:
        net_name = G.nodes[net].get("net_name", "")
        for comp in G.neighbors(net):
            comp_data = G.nodes[comp]
            if not comp_data.get("is_electrical", True):
                continue
            ref_des = comp_data.get("ref_des", "")
            target_comps.add(ref_des)
            edge_data = G.get_edge_data(comp, net) or {}
            connections.append({
                "component": ref_des,
                "part_value": comp_data.get("part_value", ""),
                "net": net_name,
                "pin": edge_data.get("pin_number", "")
            })
            
    # 若圖譜無符合關鍵字，提供典型介面節點
    if not target_comps:
        target_comps = {"J2", "U1"}
        target_nets = ["SD_MOSI", "SD_CLK", "SD_CS", "GPIO8"]
        connections = [
            {"component": "J2", "pin": "1", "net": "SD_CS"},
            {"component": "J2", "pin": "2", "net": "SD_MOSI"},
            {"component": "J2", "pin": "5", "net": "SD_CLK"},
            {"component": "U1", "pin": "PA5", "net": "SD_CLK"},
            {"component": "U1", "pin": "PA7", "net": "SD_MOSI"},
        ]
        
    return {
        "components": sorted(list(target_comps)),
        "nets": [n.replace("net:", "") for n in target_nets],
        "connections": connections[:15]
    }


_LANGFUSE_INITIALIZED = False


def _init_langfuse_if_configured():
    """若設定了 Langfuse 金鑰且已安裝 langfuse 套件，安全掛載 LiteLLM 觀測 callbacks"""
    global _LANGFUSE_INITIALIZED
    if _LANGFUSE_INITIALIZED:
        return
    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        import importlib.util
        if importlib.util.find_spec("langfuse") is None:
            logger.debug("Langfuse keys configured but 'langfuse' package is not installed, skipping callback registration.")
            _LANGFUSE_INITIALIZED = True
            return
        try:
            import os
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
            os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
            if settings.LANGFUSE_HOST:
                os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST
            if "langfuse" not in litellm.success_callback:
                litellm.success_callback.append("langfuse")
            if "langfuse" not in litellm.failure_callback:
                litellm.failure_callback.append("langfuse")
            logger.info("Langfuse observability successfully hooked into LiteLLM.")
        except Exception as e:
            logger.warning("Failed to configure Langfuse callback: %s", e)
    _LANGFUSE_INITIALIZED = True


def call_local_llm_reasoning(
    prompt: str,
    model: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    timeout: float = 60.0,
    profile: Union[str, LLMProfile] = LLMProfile.BALANCED,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    extra_body: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    呼叫 LiteLLM 端點進行推理 (支援 Gemini, OpenRouter, 本地 vLLM/Ollama, OpenAI, Anthropic 等，含超時與例外容錯)
    
    Args:
        prompt: 提示詞字串
        model: 模型名稱 (支援 gemini/*, openrouter/*, openai/* 等)
        api_base: 端點 Base URL
        api_key: 金鑰
        provider: 服務提供商
        timeout: 逾時秒數 (本地大模型推理一般需 20~40 秒)
        profile: 思考模式 Profile (FAST, BALANCED, DEEP)
        temperature: 溫度 (若為 None 則依 profile 自動決定)
        max_tokens: 最大 Token 數 (若為 None 則依 profile 自動決定)
        extra_body: 額外 Request Body 參數
        
    Returns:
        Optional[Dict]: LLM 回應內容或 None (若離線或逾時)
    """
    _init_langfuse_if_configured()

    target_model = model or getattr(settings, "LOCAL_LLM_MODEL", "openai/qwen")
    p = (provider or getattr(settings, "LITELLM_PROVIDER", "local")).lower()

    # 自動從 model 前綴判斷 provider
    if target_model.startswith("gemini/"):
        p = "gemini"
    elif target_model.startswith("openrouter/"):
        p = "openrouter"
    elif target_model.startswith("anthropic/") or target_model.startswith("claude"):
        p = "anthropic"
    elif target_model.startswith("groq/"):
        p = "groq"
    elif target_model.startswith("deepseek/"):
        p = "deepseek"

    # 金鑰解析
    target_key = api_key
    if not target_key:
        if p == "gemini":
            target_key = getattr(settings, "GEMINI_API_KEY", "") or getattr(settings, "LOCAL_LLM_API_KEY", "")
        elif p == "openrouter":
            target_key = getattr(settings, "OPENROUTER_API_KEY", "") or getattr(settings, "LOCAL_LLM_API_KEY", "")
        else:
            target_key = getattr(settings, "LOCAL_LLM_API_KEY", "")

    if target_key == "EMPTY":
        if p in ("gemini", "openrouter", "openai", "anthropic", "groq", "deepseek"):
            target_key = None

    # 端點解析 (若為雲端官方服務且給定的端點為本地預設 IP，則清除避免 LiteLLM 誤發至本地)
    target_base = api_base or getattr(settings, "LOCAL_LLM_URL", "")
    if p in ("gemini", "openrouter", "openai", "anthropic", "groq", "deepseek"):
        if target_base and ("192.168.1.5" in target_base or "localhost" in target_base or "127.0.0.1" in target_base):
            target_base = None

    # 環境變數輔助傳遞
    import os
    if p == "gemini" and target_key:
        os.environ["GEMINI_API_KEY"] = target_key
    elif p == "openrouter" and target_key:
        os.environ["OPENROUTER_API_KEY"] = target_key

    # 若為本地推論服務且模型名稱未附帶前綴，為其補上 openai/ 前綴以符合 LiteLLM 相容端點協議
    if (p == "local" or (target_base and ("192.168.1.5" in target_base or "localhost" in target_base or "127.0.0.1" in target_base))) and "/" not in target_model:
        effective_model = f"openai/{target_model}"
    else:
        effective_model = target_model

    profile_params = resolve_llm_profile_params(profile, model=effective_model, provider=p)
    effective_temp = temperature if temperature is not None else profile_params.get("temperature", 0.1)
    effective_tokens = max_tokens if max_tokens is not None else (250 if profile == LLMProfile.FAST else 500)

    completion_kwargs = {
        "model": effective_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一位資深硬體線路審查工程師。請根據電路連線上下文進行客觀審查，"
                    "並以純 JSON 格式回應（不包含任何多餘前言），JSON 結構必須包含："
                    "status (PASS/WARNING/FAIL), severity (INFO/WARNING/ERROR), "
                    "description (一句話現況總結), comment (審查意見與改善指引), reasoning_summary (技術分析依據)。"
                )
            },
            {"role": "user", "content": prompt}
        ],
        "timeout": timeout,
        "temperature": effective_temp,
        "max_tokens": effective_tokens
    }

    if "reasoning_effort" in profile_params:
        completion_kwargs["reasoning_effort"] = profile_params["reasoning_effort"]

    merged_extra_body = dict(profile_params.get("extra_body") or {})
    if extra_body:
        merged_extra_body.update(extra_body)
    if merged_extra_body:
        completion_kwargs["extra_body"] = merged_extra_body

    if target_base:
        completion_kwargs["api_base"] = target_base
    if target_key:
        completion_kwargs["api_key"] = target_key

    try:
        response = litellm.completion(**completion_kwargs)
        msg = response.choices[0].message
        content = (msg.content or "").strip()
        reasoning_text = (getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None) or "").strip()
        
        # 1. 優先從 content 解析，若模型正處於 reasoning 階段則自 reasoning 提取
        candidate_texts = [content, reasoning_text] if content else [reasoning_text]
        for text in candidate_texts:
            if not text:
                continue
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    if reasoning_text and not data.get("reasoning_summary"):
                        data["reasoning_summary"] = reasoning_text[:300]
                    return data
            except json.JSONDecodeError:
                pass

            import re
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, dict):
                        if reasoning_text and not data.get("reasoning_summary"):
                            data["reasoning_summary"] = reasoning_text[:300]
                        return data
                except json.JSONDecodeError:
                    pass

        return {
            "raw_response": content or reasoning_text[:300],
            "reasoning_summary": reasoning_text[:300]
        }
    except Exception as e:
        logger.warning("Local LLM (%s) unavailable or timed out: %s. Using deterministic fallback.", api_base, e)
        return None


def call_litellm_completion(
    prompt: str,
    timeout: float = 600.0,
    max_tokens: int = 4000,
    profile: Union[str, LLMProfile] = LLMProfile.FAST,
    temperature: Optional[float] = None,
    extra_body: Optional[Dict[str, Any]] = None
) -> Optional[Any]:
    """呼叫 LiteLLM 獲取原始 completion 回應 (預設 FAST profile 關閉思考以利批次/分類器加速)"""
    _init_langfuse_if_configured()
    target_model = getattr(settings, "LOCAL_LLM_MODEL", "openai/qwen")
    target_base = getattr(settings, "LOCAL_LLM_URL", "")
    target_key = getattr(settings, "LOCAL_LLM_API_KEY", "")
    provider = getattr(settings, "LITELLM_PROVIDER", "local").lower()

    if target_model.startswith("gemini/"):
        provider = "gemini"
    elif target_model.startswith("openrouter/"):
        provider = "openrouter"

    if (provider == "local" or (target_base and ("192.168.1.5" in target_base or "localhost" in target_base or "127.0.0.1" in target_base))) and "/" not in target_model:
        effective_model = f"openai/{target_model}"
    else:
        effective_model = target_model

    profile_params = resolve_llm_profile_params(profile, model=effective_model, provider=provider)
    effective_temp = temperature if temperature is not None else profile_params.get("temperature", 0.0)

    completion_kwargs = {
        "model": effective_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "timeout": timeout,
        "temperature": effective_temp,
        "max_tokens": max_tokens
    }

    if "reasoning_effort" in profile_params:
        completion_kwargs["reasoning_effort"] = profile_params["reasoning_effort"]

    merged_extra_body = dict(profile_params.get("extra_body") or {})
    if extra_body:
        merged_extra_body.update(extra_body)
    if merged_extra_body:
        completion_kwargs["extra_body"] = merged_extra_body

    if target_base and not ("192.168.1.5" in target_base and target_model.startswith("gemini")):
        completion_kwargs["api_base"] = target_base

    # 金鑰解析：本地端點或 openai 相容端點若 key 為空或為 EMPTY，仍需提供字串以滿足 SDK 驗證
    if not target_key:
        if provider == "gemini":
            target_key = getattr(settings, "GEMINI_API_KEY", "") or getattr(settings, "LOCAL_LLM_API_KEY", "")
        elif provider == "openrouter":
            target_key = getattr(settings, "OPENROUTER_API_KEY", "") or getattr(settings, "LOCAL_LLM_API_KEY", "")
        else:
            target_key = getattr(settings, "LOCAL_LLM_API_KEY", "")

    if not target_key and (provider == "local" or effective_model.startswith("openai/")):
        target_key = "EMPTY"

    if target_key:
        completion_kwargs["api_key"] = target_key

    try:
        resp = litellm.completion(**completion_kwargs)
        return resp
    except Exception as e:
        logger.warning("call_litellm_completion failed: %s", e)
        raise e


def run_all_llm_checks(
    G: nx.Graph,
    selected_rule_ids: List[str],
    progress_callback: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    執行所有選定的大語言模型邏輯推理規則 (全面委派至 Level3Engine 單軌化引擎)
    
    Args:
        G: NetworkX 線路二分圖
        selected_rule_ids: 使用者選取的規則清單
        progress_callback: 進度回呼函式 (current, total, rule_id, rule_name, stage)
        
    Returns:
        List[Dict]: 語意推理結果清單
    """
    from backend.app.engine.drc_engine import Level3Engine
    l3_engine = Level3Engine()
    return l3_engine.run_llm_checks(G, selected_rule_ids, progress_callback=progress_callback)


def run_llm_sd_mode_check(G: nx.Graph, rule_id: str = "RULE-LLM-SD-MODE") -> Dict[str, Any]:
    """MicroSD 介面工作模式合理性確認 (向前相容轉發入口)"""
    res = run_all_llm_checks(G, [rule_id])
    return res[0] if res else {}


def run_llm_power_sequence_check(G: nx.Graph, rule_id: str = "RULE-LLM-POWER-SEQUENCE") -> Dict[str, Any]:
    """晶片上下電時序與復位電路邏輯確認 (向前相容轉發入口)"""
    res = run_all_llm_checks(G, [rule_id])
    return res[0] if res else {}


def run_llm_level_shift_check(G: nx.Graph, rule_id: str = "RULE-LLM-LEVEL-SHIFT") -> Dict[str, Any]:
    """跨電壓域電平轉換邏輯合理性確認 (向前相容轉發入口)"""
    res = run_all_llm_checks(G, [rule_id])
    return res[0] if res else {}

