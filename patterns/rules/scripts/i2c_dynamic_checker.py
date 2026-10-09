"""
I2C 動態特規檢查腳本 (I2C Dynamic Checker)

配合 PartDB 零件規格庫，檢查晶片特定硬體電氣規範 (禁止接地電容、上拉電阻阻值、串聯電阻)。
使用標準 designshield.sdk 型別契約。
"""

from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
)


def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[List[RuleViolation], RuleResult]:
    """
    執行 I2C PartDB 特規檢查

    Args:
        context: 包含 target 節點之上下文
        graph_api: 提供電路拓撲查詢之 GraphAPI
        part_db: PartDB 實例，提供 IC 規格查表
        params: 外部傳入之額外參數

    Returns:
        Union[List[RuleViolation], RuleResult]: 違規清單或 PASS
    """
    target_node = context.target
    violations: List[RuleViolation] = []

    # 取得連線至此匯流排的主控晶片 (Master IC)
    master_ic = graph_api.get_master_device(target_node)
    if not master_ic:
        return RuleResult.PASS

    ic_pn = master_ic.pn
    ic_specs = part_db.query(pn=ic_pn, interface="I2C")
    if not ic_specs:
        return RuleResult.PASS

    evidence_meta = ic_specs.get("_meta", {})

    # 1. 檢查是否嚴禁對地電容
    if ic_specs.get("forbid_gnd_capacitor", False):
        if graph_api.has_capacitor_to_gnd(target_node):
            violations.append(RuleViolation(
                message=f"主控晶片 {master_ic.ref_des} ({ic_pn}) 原廠規格書明定 I2C SCL/SDA 嚴禁外接接地電容",
                severity="ERROR",
                evidence=evidence_meta
            ))

    # 2. 檢查上拉電阻阻值範圍
    if "pullup_range_ohms" in ic_specs:
        pullup_range = ic_specs["pullup_range_ohms"]
        for res in graph_api.get_pullup_resistors(target_node):
            res_val = res.get("resistance_ohm")
            if res_val is not None and not (pullup_range[0] <= res_val <= pullup_range[1]):
                violations.append(RuleViolation(
                    message=f"上拉電阻 {res.ref_des} ({res.part_value}) 阻值不在晶片規格書要求範圍 {pullup_range[0]}Ω ~ {pullup_range[1]}Ω 內",
                    severity="ERROR",
                    evidence=evidence_meta
                ))

    # 3. 檢查串聯電阻
    if ic_specs.get("requires_series_resistor", False):
        if not graph_api.has_series_resistor(target_node):
            violations.append(RuleViolation(
                message=f"晶片 {master_ic.ref_des} ({ic_pn}) 規格書明定 I2C 需配置串聯匹配電阻",
                severity="WARNING",
                evidence=evidence_meta
            ))

    return violations if violations else RuleResult.PASS
