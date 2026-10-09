"""
I2C 動態特規檢查腳本 (相容轉發入口)

向下相容轉發至 patterns/rules/scripts/i2c_dynamic_checker.py。
"""

from typing import Dict, List, Any
from patterns.rules.scripts.i2c_dynamic_checker import execute as new_execute
from designshield.sdk.models import RuleViolation, RuleResult


def execute(context: Any, graph_api: Any, part_db: Any, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    向下相容入口，自動將 RuleViolation / RuleResult 轉譯為 Dict 清單
    """
    res = new_execute(context, graph_api, part_db, params)
    if isinstance(res, RuleResult) or res is None or res == RuleResult.PASS:
        return []
    if isinstance(res, list):
        out = []
        for item in res:
            if isinstance(item, RuleViolation):
                out.append(item.to_dict())
            elif isinstance(item, dict):
                out.append(item)
        return out
    return []
