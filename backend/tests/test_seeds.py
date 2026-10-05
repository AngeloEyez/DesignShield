"""
規則庫播種單元測試 (Seeds Unit Tests)
"""

from backend.app.db.seeds import seed_default_rules, DEFAULT_RULES
from backend.app.models.rule import DrcRule


def test_seed_default_rules_idempotent(db_session):
    """測試規則庫初次播種與重複播種的冪等性 (Idempotency)"""
    # 初次播種
    count1 = seed_default_rules(db_session)
    assert count1 == len(DEFAULT_RULES)

    all_rules = db_session.query(DrcRule).all()
    assert len(all_rules) == len(DEFAULT_RULES)

    # 驗證關鍵規則存在
    rule_ids = [r.id for r in all_rules]
    assert "RULE-BUS-I2C-ADDR" in rule_ids
    assert "RULE-PWR-CAP-DERATING" in rule_ids
    assert "RULE-LLM-SD-MODE" in rule_ids

    # 第二次播種 (應該為 0 筆新增)
    count2 = seed_default_rules(db_session)
    assert count2 == 0
    assert db_session.query(DrcRule).count() == len(DEFAULT_RULES)
