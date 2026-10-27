"""
系統設定 API 端點測試 (Settings API Tests)
"""

from backend.app.models.settings import SystemSetting
from backend.app.core.config import settings, is_level1_llm_enabled, is_level2_llm_enabled


def test_settings_api(client, db_session):
    """測試系統設定 API (資料庫為單一信任來源)"""
    setting = SystemSetting(key="test_key", value={"enabled": True}, description="測試設定")
    db_session.add(setting)
    db_session.commit()

    # 查詢全部 (回傳 EnvSettingsResponse 總覽格式)
    all_res = client.get("/api/v1/settings")
    assert all_res.status_code == 200
    data = all_res.json()
    assert "items" in data
    assert "categories" in data
    assert data["total_count"] >= 1

    # 查詢單一特定設定
    get_res = client.get("/api/v1/settings/test_key")
    assert get_res.status_code == 200
    assert get_res.json()["value"]["enabled"] is True

    # 查詢不存在 404
    not_found_res = client.get("/api/v1/settings/no_such_key")
    assert not_found_res.status_code == 404

    # 更新單一設定
    put_res = client.put("/api/v1/settings/test_key", json={"value": {"enabled": False}, "description": "更新說明"})
    assert put_res.status_code == 200
    assert put_res.json()["value"]["enabled"] is False


def test_health_check_api(client):
    """測試健康度檢查端點"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_env_settings_api(client, db_session):
    """測試系統設定總覽端點 (/settings 與 /settings/env 別名相容)"""
    # 測試相容別名端點
    res = client.get("/api/v1/settings/env")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "categories" in data
    assert any(item["key"] == "LANGFUSE_PUBLIC_KEY" for item in data["items"])
    assert any(item["key"] == "LANGFUSE_SECRET_KEY" for item in data["items"])
    assert any(item["key"] == "LITELLM_PROVIDER" for item in data["items"])

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
    assert "ENABLE_LEVEL1_LLM_FALLBACK" in llm_keys
    assert "ENABLE_LEVEL2_LLM_FALLBACK" in llm_keys

    l1_item = next(item for item in data["items"] if item["key"] == "ENABLE_LEVEL1_LLM_FALLBACK")
    assert l1_item["item_type"] == "boolean"
    assert l1_item["requires_restart"] is False


def test_env_settings_update_api(client, db_session):
    """測試系統設定更新端點 (寫入資料庫並即時熱同步，100% 免重啟)"""
    import uuid
    dummy_pub = f"pk-lf-{uuid.uuid4().hex[:12]}"
    dummy_sec = f"sk-lf-{uuid.uuid4().hex[:12]}"
    update_payload = {
        "settings": {
            "LANGFUSE_PUBLIC_KEY": dummy_pub,
            "LANGFUSE_SECRET_KEY": dummy_sec,
            "RETENTION_DAYS_UNSTARTED": "4",
            "LITELLM_PROVIDER": "local"
        }
    }
    res = client.put("/api/v1/settings/env", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "LANGFUSE_PUBLIC_KEY" in data["changed_keys"]
    assert data["requires_restart"] is False
    assert len(data["restart_reasons"]) == 0

    # 驗證資料庫已安全更新
    db_item = db_session.query(SystemSetting).filter(SystemSetting.key == "LANGFUSE_PUBLIC_KEY").first()
    assert db_item is not None
    assert db_item.value == {"value": dummy_pub}

    # 驗證執行期 settings 單例已即時熱同步
    assert settings.LANGFUSE_PUBLIC_KEY == dummy_pub
    assert settings.LANGFUSE_SECRET_KEY == dummy_sec


def test_restart_endpoint_api(client, monkeypatch):
    """測試伺服器重啟端點 (無特權優雅退出)"""
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


def test_dynamic_level_llm_enabled_switch_from_database(client, db_session):
    """測試 is_level1_llm_enabled 與 is_level2_llm_enabled 支援自資料庫與記憶體動態熱生效"""
    # 透過 API 更新為 false
    update_res = client.put("/api/v1/settings", json={
        "settings": {
            "ENABLE_LEVEL1_LLM_FALLBACK": "false",
            "ENABLE_LEVEL2_LLM_FALLBACK": "false"
        }
    })
    assert update_res.status_code == 200

    # 驗證動態函式即時反映出 False
    assert is_level1_llm_enabled() is False
    assert is_level2_llm_enabled() is False

    # 透過 API 更新為 true
    update_res2 = client.put("/api/v1/settings", json={
        "settings": {
            "ENABLE_LEVEL1_LLM_FALLBACK": "true",
            "ENABLE_LEVEL2_LLM_FALLBACK": "true"
        }
    })
    assert update_res2.status_code == 200
    assert is_level1_llm_enabled() is True
    assert is_level2_llm_enabled() is True
