"""
I2C 匯流排上拉電阻存在性與電氣規格檢驗伴生腳本 (I2C Pull-up Resistor Companion Script)

本腳本透過 DesignShield SDK (GraphAPI) 執行：
1. 檢驗 I2C 網路 (SCL / SDA) 是否配置上拉電阻 (Pull-up Resistor)。
2. 檢驗上拉電阻另一端是否確實連接至電源軌 (Power Rail)，而非浮接或接地。
3. 提取上拉電阻位號 (如 R1)、標稱值 (如 4.7k)、換算電阻值 (如 4700Ω) 與連接之電源軌。
4. 比對阻值是否落在標準通訊規範範圍 (1.0kΩ ~ 10.0kΩ)。
5. 檢驗合格 (PASS) 時回傳結構化 RulePass 物件，供 DRC 審計歷程 (Evidence Trail) 完整追溯。
"""

from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
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
) -> Union[List[RuleViolation], RulePass, RuleResult]:
    """
    執行 I2C 上拉電阻存在性與電氣審計

    Args:
        context: 執行期上下文 (包含 context.target 目標網路節點)
        graph_api: SDK 拓撲查詢介面
        part_db: SDK 零件規格庫查詢介面
        params: YAML 外部參數字典

    Returns:
        Union[List[RuleViolation], RulePass, RuleResult]: 違規清單或結構化合格物件
    """
    params = params or {}
    target_net = context.target
    net_name = target_net.net_name
    violations: List[RuleViolation] = []

    # 1. 取得所有連接至該網路且連接電源之上拉電阻
    pullup_resistors = graph_api.get_pullup_resistors(target_net)

    # 2. 存在性檢查：若未發現任何上拉電阻
    if not pullup_resistors:
        return [RuleViolation(
            error_message=f"I2C 匯流排訊號線 ({net_name}) 缺少上拉電阻配置",
            recommendation="建議在 I2C 訊號線配置 2.2kΩ ~ 10kΩ 之上拉電阻至電源軌 (如 +3.3V)。",
            severity="ERROR",
            evidence={
                "checked_target": net_name,
                "pullup_found": False,
                "detected_resistors_count": 0,
            },
            target_nodes={
                "components": [],
                "nets": [net_name]
            }
        )]

    # 規範範圍閥值 (可由 params 覆寫，預設 1.0kΩ ~ 10.0kΩ)
    min_ohm = float(params.get("min_resistance_ohm", 1000.0))
    max_ohm = float(params.get("max_resistance_ohm", 10000.0))

    resistors_audit_list: List[Dict[str, Any]] = []
    involved_components: List[str] = []

    for r in pullup_resistors:
        ref_des = r.ref_des
        part_val = r.part_value
        res_ohm = r.get("resistance_ohm")
        power_rail = r.get("power_rail")
        power_v = r.get("power_rail_voltage")
        involved_components.append(ref_des)

        # 3. 連接至電源軌完整性檢查
        if not power_rail:
            violations.append(RuleViolation(
                error_message=f"I2C 匯流排訊號線 ({net_name}) 上拉電阻 {ref_des} 另一端未正確連接至電源軌",
                recommendation="請確認上拉電阻電源端連接至合法電源軌，避免浮接造成通訊失效。",
                severity="ERROR",
                evidence={
                    "checked_target": net_name,
                    "resistor": ref_des,
                    "power_rail": None
                },
                target_nodes={
                    "components": [ref_des],
                    "nets": [net_name]
                }
            ))
            continue

        # 4. 阻值合理性檢查
        is_val_compliant = True
        val_status_msg = "符合標準範圍"
        if res_ohm is not None:
            if res_ohm < min_ohm or res_ohm > max_ohm:
                is_val_compliant = False
                val_status_msg = f"偏離標準範圍 ({min_ohm}Ω ~ {max_ohm}Ω)"
                violations.append(RuleViolation(
                    error_message=f"I2C 訊號線 ({net_name}) 上拉電阻 {ref_des} 阻值 ({part_val}, 約 {res_ohm:.0f}Ω) {val_status_msg}",
                    recommendation=f"建議將上拉電阻調整為 {min_ohm/1000:.1f}kΩ ~ {max_ohm/1000:.1f}kΩ 之標準值，避免上升時間不足或功耗過大。",
                    severity="WARNING",
                    evidence={
                        "checked_target": net_name,
                        "resistor": ref_des,
                        "part_value": part_val,
                        "measured_ohm": res_ohm,
                        "min_limit_ohm": min_ohm,
                        "max_limit_ohm": max_ohm,
                        "power_rail": power_rail
                    },
                    target_nodes={
                        "components": [ref_des],
                        "nets": [net_name]
                    }
                ))

        resistors_audit_list.append({
            "ref_des": ref_des,
            "part_value": part_val,
            "resistance_ohm": res_ohm,
            "power_rail": power_rail,
            "power_rail_voltage": power_v,
            "compliant": is_val_compliant,
            "status_description": val_status_msg
        })

    if violations:
        return violations

    # 5. 全數合規：回傳結構化 RulePass 審計歷程
    summary_parts = [
        f"{item['ref_des']} ({item['part_value'] or (str(item['resistance_ohm']) + 'Ω')} → {item['power_rail']})"
        for item in resistors_audit_list
    ]
    audit_summary_text = f"已驗證 {net_name} 正確配置上拉電阻: " + ", ".join(summary_parts) + f"，符合 {min_ohm/1000:.1f}kΩ ~ {max_ohm/1000:.1f}kΩ 設計規範。"

    return RulePass(
        evidence={
            "checked_target": net_name,
            "pullup_found": True,
            "pullup_count": len(resistors_audit_list),
            "resistors": resistors_audit_list,
            "spec_threshold": {
                "min_ohms": min_ohm,
                "max_ohms": max_ohm,
                "description": f"I2C 匯流排標準上拉電阻規範 ({min_ohm/1000:.1f}kΩ ~ {max_ohm/1000:.1f}kΩ)"
            },
            "audit_summary": audit_summary_text
        },
        target_nodes={
            "components": involved_components,
            "nets": [net_name]
        },
        message=f"I2C 匯流排 {net_name} 上拉電阻檢驗合格"
    )
