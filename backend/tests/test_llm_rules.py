"""
大語言模型邏輯推理規則單元測試 (LLM Rules Tests)

驗證周邊子圖上下文抽取、LiteLLM 呼叫及本地 LLM 離線時之優雅降級。
"""

import json
from unittest.mock import patch, MagicMock
import networkx as nx
from backend.app.engine.rules.llm import (
    extract_interface_subgraph_context,
    call_local_llm_reasoning,
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
