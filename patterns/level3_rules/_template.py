"""
DesignShield Level 3 DRC 伴生腳本標準範本 (Companion Script Template)

【重要維護說明】
1. 沙盒執行環境: 本腳本受 ASTSecurityValidator 靜態安全審查保護，
   嚴禁使用 eval、exec、os/sys/subprocess 系統呼叫或非白名單模組。
2. 進入點規範: 必須宣告全域函式 `def execute(context, graph_api, part_db, params=None)`。
3. 自動關聯: 腳本檔名若與同目錄 YAML 規則名稱相同，系統會全自動繫結，無需在 YAML 寫死 script_path。
4. 真實資料審計原則: 若遇到需要查詢 PartDB 但資料庫中缺少料號資料時，
   請回傳 RuleSkipped 並標註缺失料號，嚴禁偽造或猜測電氣參數。
"""

from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleSkipped,
    RuleViolation,
    RuleContext,
    ComponentNode,
    NetNode,
    GraphAPI,
    PartDB,
    TopologyGraphBuilder,
)


def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[List[RuleViolation], RulePass, RuleSkipped, RuleResult]:
    """
    DRC 檢驗腳本進入點函式

    Args:
        context: 執行期上下文 (包含 context.target 目標節點 NetNode 或 ComponentNode)
        graph_api: SDK 圖論拓撲查詢介面 (提供連接性、串聯路徑、上拉電阻查詢)
        part_db: SDK 零件規格庫查詢介面 (提供料號特規檢索與 pass_through 查詢)
        params: YAML 傳入之客製參數字典 (預設為空字典)

    Returns:
        Union[List[RuleViolation], RulePass, RuleSkipped, RuleResult]:
        - 合格: 回傳 RulePass(message=..., evidence=..., target_nodes=...)
        - 違規: 回傳 List[RuleViolation(error_message=..., recommendation=..., severity=..., evidence=...)]
        - 資料缺失跳過: 回傳 RuleSkipped(message=..., evidence=...)
    """
    params = params or {}
    target = context.target
    violations: List[RuleViolation] = []

    # 1. 取得目標標的資訊 (依 target 型態是 NetNode 或 ComponentNode 提取)
    if isinstance(target, NetNode):
        target_name = target.net_name
    elif isinstance(target, ComponentNode):
        target_name = target.ref_des
    else:
        target_name = getattr(target, "_id", "UNKNOWN_TARGET")

    # 2. 示範圖論拓撲查詢 (GraphAPI 範例)
    # connected_components = graph_api.get_connected_components(target)

    # 3. 示範 PartDB 查詢與真實資料驗證原則
    # part_info = part_db.get_part(pn="SAMPLE_PN", mfg="SAMPLE_MFG")
    # if not part_info:
    #     return RuleSkipped(
    #         message=f"目標元件缺少 PartDB 規格資料，跳過深度電氣校驗",
    #         evidence={"target": target_name, "missing_pn": "SAMPLE_PN"}
    #     )

    # 4. 判斷邏輯與回傳結構
    # 若檢出違規：
    # violations.append(RuleViolation(
    #     error_message=f"目標 {target_name} 違反電氣設計規則",
    #     recommendation="建議修正電路設計以符合硬體規範",
    #     severity="ERROR",
    #     evidence={"target": target_name, "details": "違規佐證數據"}
    # ))
    # return violations

    # 若檢驗合格 (PASS)：
    return RulePass(
        message=f"目標 {target_name} 符合設計規範",
        evidence={
            "checked_target": target_name,
            "status": "PASS",
        },
        target_nodes=None  # 可傳入特定聚焦節點清單
    )
