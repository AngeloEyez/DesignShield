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
