"""
測試規則庫熱重載與編譯快取 (Rule Recompile & Validation Tests)

驗證範圍:
1. Unified Rule Validator (Level 1~3, PartDB, Regex 語法校驗)
2. ComponentPatternEngine.reload() 與 Regex 預編譯快取
3. TopologyPatternEngine.reload()
4. PatternService.reload_with_compilation() 成功與取消機制
5. POST /api/v1/patterns/reload 端點回應結構與狀態碼
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
import yaml

from backend.app.main import app
from scripts.validate_rules import (
    validate_all_rules,
    validate_level1_rules,
    validate_level2_rules,
    validate_level3_rules,
    validate_partdb,
)
from backend.app.engine.pattern_engine import get_component_engine
from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
from backend.app.services.pattern_service import PatternService


client = TestClient(app)


def test_validator_on_current_rules():
    """驗證當前倉庫中的所有 YAML 規則與 PartDB 全數合法"""
    is_valid, errors = validate_all_rules()
    assert is_valid is True, f"預期全數通過，但有錯誤: {errors}"
    assert len(errors) == 0


def test_validator_detects_invalid_regex_and_missing_fields():
    """驗證檢查工具能精準抓出正則語法錯誤與缺漏必填欄位"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        comp_dir = os.path.join(tmp_dir, "components")
        os.makedirs(comp_dir, exist_ok=True)

        # 寫入無效 regex 的 YAML
        bad_yaml = {
            "name": "bad_rule",
            "priority": 100,
            "matches": {
                "value_regex": "[a-",  # 未閉合括號
            },
            "assigns": {
                "category": "IC",
                "sub_category": "MCU",
                "functional_role": "Master",
                "is_electrical": True,
                "confidence": 0.9,
            }
        }
        with open(os.path.join(comp_dir, "bad.yaml"), "w", encoding="utf-8") as f:
            yaml.dump(bad_yaml, f)

        errors = validate_level1_rules(patterns_dir=tmp_dir)
        assert len(errors) >= 1
        assert any("正規表示式" in err and "語法錯誤" in err for err in errors)


def test_component_engine_reload_and_regex_cache():
    """驗證 ComponentPatternEngine.reload() 能清空並重新填入 regex 快取"""
    engine = get_component_engine()
    count = engine.reload()
    assert count > 0
    cached_regexes = engine.get_cached_regex_count()
    assert cached_regexes > 0, "應預編譯並快取正則表示式"


def test_topology_engine_reload():
    """驗證 TopologyPatternEngine.reload() 能正常重載規則"""
    engine = TopologyPatternEngine.get_instance()
    count = engine.reload()
    assert count > 0


def test_pattern_service_reload_with_compilation():
    """驗證 PatternService.reload_with_compilation() 能產出完整的 compile_stats"""
    svc = PatternService.get_instance()
    res = svc.reload_with_compilation(strict=True)
    assert res["success"] is True
    assert "compile_stats" in res
    stats = res["compile_stats"]
    assert stats["level1_rules"] > 0
    assert stats["level2_rules"] > 0
    assert stats["level3_rules"] > 0
    assert stats["regex_compiled"] > 0
    assert stats["compile_time_ms"] >= 0


def test_api_reload_endpoint_success():
    """驗證 POST /api/v1/patterns/reload 端點成功回傳狀態與編譯統計"""
    response = client.post("/api/v1/patterns/reload")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "compile_stats" in data
    assert data["compile_stats"]["level1_rules"] > 0
    assert data["compile_stats"]["level2_rules"] > 0
    assert data["compile_stats"]["level3_rules"] > 0


def test_api_reload_endpoint_cancels_on_validation_failure(monkeypatch):
    """驗證當 YAML 校驗失敗時，取消編譯並回傳 HTTP 400 與錯誤列表"""
    fake_errors = ["[Level 3] test.yaml: 缺少必填欄位 severity"]
    import backend.app.services.pattern_service as ps_module
    monkeypatch.setattr(ps_module, "validate_all_rules", lambda: (False, fake_errors))

    response = client.post("/api/v1/patterns/reload")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "已取消編譯" in data["message"]
    assert data["errors"] == fake_errors
