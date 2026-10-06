"""
規則與系統設定 API 端點測試 (Rules & Settings API Tests)
"""

from backend.app.models.rule import DrcRule
from backend.app.models.settings import SystemSetting


def test_rules_api(client, db_session):
    """測試規則庫查詢與新增 API"""
    rule_data = {
        "id": "RULE-TEST-001",
        "name": "測試規則一",
        "category": "Signal Integrity",
        "check_type": "HEURISTIC",
        "is_active": True,
        "parameters": {"max_delay_ns": 2.5}
    }
    
    # 建立
    create_res = client.post("/api/v1/rules", json=rule_data)
    assert create_res.status_code == 201
    assert create_res.json()["id"] == "RULE-TEST-001"

    # 重複建立回傳 400
    duplicate_res = client.post("/api/v1/rules", json=rule_data)
    assert duplicate_res.status_code == 400

    # 查詢清單
    list_res = client.get("/api/v1/rules")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(r["id"] == "RULE-TEST-001" for r in items)

    # 依分類過濾
    filter_res = client.get("/api/v1/rules?category=Signal%20Integrity")
    assert filter_res.status_code == 200
    assert len(filter_res.json()) >= 1

    # 單一規則查詢
    single_res = client.get("/api/v1/rules/RULE-TEST-001")
    assert single_res.status_code == 200
    assert single_res.json()["name"] == "測試規則一"

    # 單一規則不存在
    not_found_res = client.get("/api/v1/rules/RULE-NONEXISTENT")
    assert not_found_res.status_code == 404

    # 修改規則
    update_data = {
        "name": "測試規則一 (已修改)",
        "parameters": {"max_delay_ns": 3.0},
        "is_active": False
    }
    update_res = client.put("/api/v1/rules/RULE-TEST-001", json=update_data)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "測試規則一 (已修改)"
    assert update_res.json()["parameters"]["max_delay_ns"] == 3.0
    assert update_res.json()["is_active"] is False

    # 修改不存在之規則
    up_nf_res = client.put("/api/v1/rules/RULE-NONEXISTENT", json={"name": "新名稱"})
    assert up_nf_res.status_code == 404

    # 刪除規則
    del_res = client.delete("/api/v1/rules/RULE-TEST-001")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 再次查詢已刪除規則
    del_check_res = client.get("/api/v1/rules/RULE-TEST-001")
    assert del_check_res.status_code == 404

    # 刪除不存在規則
    del_nf_res = client.delete("/api/v1/rules/RULE-NONEXISTENT")
    assert del_nf_res.status_code == 404


def test_settings_api(client, db_session):
    """測試系統設定 API"""
    setting = SystemSetting(key="test_key", value={"enabled": True}, description="測試設定")
    db_session.add(setting)
    db_session.commit()

    # 查詢全部
    all_res = client.get("/api/v1/settings")
    assert all_res.status_code == 200
    assert len(all_res.json()) >= 1

    # 查詢單一
    get_res = client.get("/api/v1/settings/test_key")
    assert get_res.status_code == 200
    assert get_res.json()["value"]["enabled"] is True

    # 查詢不存在 404
    not_found_res = client.get("/api/v1/settings/no_such_key")
    assert not_found_res.status_code == 404

    # 更新設定
    put_res = client.put("/api/v1/settings/test_key", json={"value": {"enabled": False}, "description": "更新說明"})
    assert put_res.status_code == 200
    assert put_res.json()["value"]["enabled"] is False


def test_health_check_api(client):
    """測試健康度檢查端點"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_env_settings_api(client):
    """測試 .env 設定讀取端點"""
    res = client.get("/api/v1/settings/env")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "categories" in data
    assert any(item["key"] == "LANGFUSE_PUBLIC_KEY" for item in data["items"])
    assert any(item["key"] == "LANGFUSE_SECRET_KEY" for item in data["items"])
    assert any(item["key"] == "SERVER_HOST" for item in data["items"])

    # 檢查 Langfuse 範例說明
    pub_item = next(item for item in data["items"] if item["key"] == "LANGFUSE_PUBLIC_KEY")
    sec_item = next(item for item in data["items"] if item["key"] == "LANGFUSE_SECRET_KEY")
    assert "LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx" in pub_item["description"]
    assert "LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx" in sec_item["description"]

    # 檢查 LiteLLM 設定項目與順序: 包含 LITELLM_PROVIDER，且 LOCAL_LLM_URL -> LOCAL_LLM_API_KEY -> LOCAL_LLM_MODEL 緊鄰依序排列
    llm_keys = [item["key"] for item in data["items"] if item["category"] == "llm"]
    assert "LITELLM_PROVIDER" in llm_keys
    url_idx = llm_keys.index("LOCAL_LLM_URL")
    assert llm_keys[url_idx:url_idx+3] == ["LOCAL_LLM_URL", "LOCAL_LLM_API_KEY", "LOCAL_LLM_MODEL"]


def test_env_settings_update_api(client):
    """測試 .env 設定更新端點"""
    import uuid
    dummy_pub = f"pk-lf-{uuid.uuid4().hex[:12]}"
    dummy_sec = f"sk-lf-{uuid.uuid4().hex[:12]}"
    update_payload = {
        "settings": {
            "LANGFUSE_PUBLIC_KEY": dummy_pub,
            "LANGFUSE_SECRET_KEY": dummy_sec,
            "UPLOAD_RETENTION_DAYS": "10",
            "LITELLM_PROVIDER": "gemini"
        }
    }
    res = client.put("/api/v1/settings/env", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "LANGFUSE_PUBLIC_KEY" in data["changed_keys"]
    assert data["requires_restart"] is True
    assert "LANGFUSE_PUBLIC_KEY" in data["restart_reasons"]


def test_restart_endpoint_api(client, monkeypatch):
    """測試伺服器重啟端點"""
    from backend.app.api.v1.endpoints import settings as settings_endpoint
    monkeypatch.setattr(settings_endpoint, "trigger_server_restart", lambda: {"success": True, "mode": "mock", "message": "已排程後端程序重啟"})
    res = client.post("/api/v1/settings/restart")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "mode" in data


def test_llm_models_endpoint_api(client):
    """測試 Local LLM 可用模型查詢端點"""
    res = client.get("/api/v1/settings/llm/models?provider=local&api_base=http://192.168.1.5:8000/v1")
    assert res.status_code == 200
    data = res.json()
    assert "success" in data
    assert "models" in data
    assert isinstance(data["models"], list)
    if data["success"]:
        assert len(data["models"]) >= 1


def test_llm_models_endpoint_gemini_and_openrouter(client):
    """測試 Gemini 與 OpenRouter Provider 模型查詢端點"""
    # 測試 Gemini
    res_gemini = client.get("/api/v1/settings/llm/models?provider=gemini")
    assert res_gemini.status_code == 200
    data_g = res_gemini.json()
    assert data_g["success"] is True
    assert data_g["provider"] == "gemini"
    assert any("gemini" in m for m in data_g["models"])

    # 測試 OpenRouter
    res_or = client.get("/api/v1/settings/llm/models?provider=openrouter")
    assert res_or.status_code == 200
    data_or = res_or.json()
    assert data_or["success"] is True
    assert data_or["provider"] == "openrouter"
    assert any("openrouter/" in m for m in data_or["models"])



