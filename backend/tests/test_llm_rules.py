"""
大語言模型邏輯推理規則單元測試 (LLM Rules Tests)

驗證周邊子圖上下文抽取、LiteLLM 呼叫及本地 LLM 離線時之優雅降級。
"""

import json
from unittest.mock import patch, MagicMock
import networkx as nx
from backend.app.engine.rules.llm import (
    LLMProfile,
    resolve_llm_profile_params,
    extract_interface_subgraph_context,
    call_local_llm_reasoning,
    call_litellm_completion,
    run_llm_sd_mode_check,
    run_llm_power_sequence_check,
    run_llm_level_shift_check,
    run_all_llm_checks,
)


def test_extract_interface_subgraph_context():
    """測試從全域圖譜中抽取指定關鍵字之子圖上下文"""
    G = nx.Graph()
    G.add_node("comp:J2", type="component", ref_des="J2", part_value="MicroSD_Card")
    G.add_node("comp:U1", type="component", ref_des="U1", part_value="STM32F4")
    G.add_node("net:SD_MOSI", type="net", net_name="SD_MOSI")
    G.add_node("net:SD_CLK", type="net", net_name="SD_CLK")
    G.add_edge("comp:J2", "net:SD_MOSI", pin_number="2")
    G.add_edge("comp:U1", "net:SD_MOSI", pin_number="PA7")
    G.add_edge("comp:J2", "net:SD_CLK", pin_number="5")
    G.add_edge("comp:U1", "net:SD_CLK", pin_number="PA5")

    context = extract_interface_subgraph_context(G, "SD")
    assert "J2" in context["components"]
    assert "U1" in context["components"]
    assert "SD_MOSI" in context["nets"]
    assert len(context["connections"]) >= 2


def test_call_local_llm_reasoning_success():
    """測試呼叫本地 LLM 成功回傳 JSON 資料"""
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "status": "PASS",
        "severity": "INFO",
        "description": "引腳連接關係正確。",
        "comment": "介面模式配置合理。"
    })
    mock_resp.choices = [mock_choice]

    with patch("litellm.completion", return_value=mock_resp):
        result = call_local_llm_reasoning("test prompt")
        assert result is not None
        assert result["status"] == "PASS"
        assert "引腳連接關係正確" in result["description"]


def test_call_local_llm_reasoning_fallback_on_error():
    """測試本地 LLM 離線或超時時優雅降級回傳 None"""
    with patch("litellm.completion", side_effect=Exception("Connection refused to 192.168.1.5:8000")):
        result = call_local_llm_reasoning("test prompt", timeout=0.1)
        assert result is None


def test_run_llm_sd_mode_check_offline_graceful():
    """測試本地端點離線時，run_llm_sd_mode_check 具備專家規則優雅降級能力"""
    G = nx.Graph()
    with patch("litellm.completion", side_effect=Exception("Local LLM offline")):
        item = run_llm_sd_mode_check(G)
        assert item["rule_id"] == "RULE-LLM-SD-MODE"
        assert item["check_type"] == "LLM"
        assert item["status"] == "PASS"
        assert "MicroSD" in item["description"]
        assert "SPI" in item["comment"]
        assert "evidence_trail" in item


def test_run_all_llm_checks():
    """測試批量執行所有選定的 LLM 規則"""
    G = nx.Graph()
    rule_ids = ["RULE-LLM-SD-MODE", "RULE-LLM-POWER-SEQUENCE", "RULE-LLM-LEVEL-SHIFT"]
    with patch("litellm.completion", side_effect=Exception("Offline")):
        results = run_all_llm_checks(G, rule_ids)
        assert len(results) == 3
        rule_output_ids = [r["rule_id"] for r in results]
        assert "RULE-LLM-SD-MODE" in rule_output_ids
        assert "RULE-LLM-POWER-SEQUENCE" in rule_output_ids
        assert "RULE-LLM-LEVEL-SHIFT" in rule_output_ids


def test_resolve_llm_profile_params():
    """測試不同 Profile 解析出的參數結構"""
    # 1. FAST Profile (Qwen/local: enable_thinking=False, temp=0.0)
    fast_params = resolve_llm_profile_params(LLMProfile.FAST, model="Qwen3.8-27B", provider="local")
    assert fast_params["temperature"] == 0.0
    assert fast_params["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False

    # 2. BALANCED Profile (Qwen/local: reasoning_effort=low, temp=0.1)
    bal_params = resolve_llm_profile_params(LLMProfile.BALANCED, model="Qwen3.8-27B", provider="local")
    assert bal_params["temperature"] == 0.1
    assert bal_params["reasoning_effort"] == "low"

    # 3. DEEP Profile (Qwen/local: reasoning_effort=xhigh 繞過, temp=0.1)
    deep_params = resolve_llm_profile_params(LLMProfile.DEEP, model="Qwen3.8-27B", provider="local")
    assert deep_params["temperature"] == 0.1
    assert deep_params["extra_body"]["chat_template_kwargs"]["reasoning_effort"] == "xhigh"

    # 4. 雲端非 Qwen 模型 (例如 OpenAI 或 Gemini)
    cloud_params = resolve_llm_profile_params(LLMProfile.DEEP, model="gpt-4o", provider="openai")
    assert cloud_params["temperature"] == 0.1
    assert cloud_params["reasoning_effort"] == "high"
    assert "extra_body" not in cloud_params


def test_call_local_llm_reasoning_profiles_payload():
    """測試 call_local_llm_reasoning 傳入 Profile 時 LiteLLM kwargs 是否正確組裝"""
    with patch("litellm.completion") as mock_comp:
        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps({"status": "PASS", "description": "ok"})
        mock_resp.choices = [mock_choice]
        mock_comp.return_value = mock_resp

        # 測試 DEEP profile
        call_local_llm_reasoning("test deep", profile=LLMProfile.DEEP)
        assert mock_comp.called
        call_kwargs = mock_comp.call_args[1]
        assert call_kwargs["temperature"] == 0.1
        assert call_kwargs["extra_body"]["chat_template_kwargs"]["reasoning_effort"] == "xhigh"


def test_call_litellm_completion_profile_fast():
    """測試 call_litellm_completion 預設 FAST profile 正確關閉思考"""
    with patch("litellm.completion") as mock_comp:
        mock_comp.return_value = {"choices": [{"message": {"content": "ok"}}]}

        call_litellm_completion("test fast")
        assert mock_comp.called
        call_kwargs = mock_comp.call_args[1]
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False

