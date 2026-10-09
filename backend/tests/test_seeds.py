"""
系統設定播種單元測試 (Seeds Unit Tests)
"""

from backend.app.db.seeds import seed_default_settings, DEFAULT_SETTINGS
from backend.app.models.settings import SystemSetting


def test_seed_default_settings_idempotent(db_session):
    """測試系統組態設定初次播種與重複播種的冪等性 (Idempotency)"""
    # 初次播種
    count1 = seed_default_settings(db_session)
    assert count1 == len(DEFAULT_SETTINGS)

    all_settings = db_session.query(SystemSetting).all()
    assert len(all_settings) == len(DEFAULT_SETTINGS)

    # 驗證關鍵設定項目存在
    setting_keys = [s.key for s in all_settings]
    assert "upload_retention_days" in setting_keys
    assert "task_timeout_seconds" in setting_keys
    assert "llm_config" in setting_keys
    assert "auto_cleanup_schedule" in setting_keys

    # 第二次播種 (應該為 0 筆新增)
    count2 = seed_default_settings(db_session)
    assert count2 == 0
    assert db_session.query(SystemSetting).count() == len(DEFAULT_SETTINGS)
