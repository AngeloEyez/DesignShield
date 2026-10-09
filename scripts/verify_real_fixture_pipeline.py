"""
真實線路圖樣本完整審查管線與本地 LLM 調用驗證腳本
(Verify Real Fixture Pipeline & Local LLM Integration)

執行完整流程：
1. 匯入 backend/tests/fixtures 中的真實 OrCAD XML 與 Allegro Netlist
2. 解析並建立 NetworkX 二分圖電路模型
3. 執行特徵預先分析
4. 執行 Heuristic 圖論規則檢測
5. 實際調用本地 192.168.1.5:8000/v1 (Qwen3.8-27B) 執行 LLM 邏輯推理
6. 產出結構化 DRC 審查報告並統計結果
"""

import os
import sys
import json
import time

# 將專案根目錄加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
from backend.app.engine.graph import build_schematic_graph
from backend.app.engine.pre_analyzer import analyze_schematic_features
from backend.app.engine.rules.heuristic import run_all_heuristic_checks
from backend.app.engine.rules.llm import run_all_llm_checks


def main():
    print("=" * 80)
    print("🚀 DesignShield 真實電路樣本管線與本地 LLM 審查驗證")
    print("=" * 80)

    # 1. 檢查真實樣本檔案
    xml_path = os.path.abspath("backend/tests/fixtures/sch/cartern-sch-si-20260817.xml")
    netlist_path = os.path.abspath("backend/tests/fixtures/sch/allegro/pstxnet.dat")

    if not os.path.exists(xml_path):
        print(f"❌ 錯誤: 找不到 XML 檔案: {xml_path}")
        return 1
    if not os.path.exists(netlist_path):
        print(f"❌ 錯誤: 找不到 Allegro Netlist 檔案: {netlist_path}")
        return 1

    print(f"📂 1. 讀取真實電路樣本檔案:")
    print(f"   - OrCAD XML: {xml_path} ({os.path.getsize(xml_path) / (1024*1024):.2f} MB)")
    print(f"   - Allegro Netlist: {netlist_path} ({os.path.getsize(netlist_path) / 1024:.2f} KB)")

    # 2. 串流解析
    t0 = time.time()
    xml_data = parse_orcad_xml(xml_path)
    t_xml = time.time() - t0
    print(f"\n⚡ 2. OrCAD XML 串流解析完成 (耗時: {t_xml:.3f} 秒):")
    print(f"   - 解析元件數 (Components): {len(xml_data['components'])}")
    print(f"   - 網路別名數 (Net Aliases): {len(xml_data['net_aliases'])}")

    t0 = time.time()
    netlist_data = parse_allegro_netlist(netlist_path)
    t_net = time.time() - t0
    total_conns = sum(len(conns) for conns in netlist_data.values())
    print(f"\n⚡ 3. Allegro Netlist 解析完成 (耗時: {t_net:.3f} 秒):")
    print(f"   - 解析網路數 (Nets): {len(netlist_data)}")
    print(f"   - 接腳連線數 (Pin Connections): {total_conns}")

    # 3. 合併並建立 NetworkX 二分異質圖
    t0 = time.time()
    merged_data = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged_data)
    t_graph = time.time() - t0

    comp_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "component"]
    net_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "net"]
    print(f"\n🌐 4. NetworkX 二分圖譜構建完成 (耗時: {t_graph:.3f} 秒):")
    print(f"   - 圖譜總節點數 (Total Nodes): {G.number_of_nodes()}")
    print(f"   - 元件節點數 (Component Nodes): {len(comp_nodes)}")
    print(f"   - 網路節點數 (Net Nodes): {len(net_nodes)}")
    print(f"   - 圖譜拓撲唯一邊數 (Unique Edges): {G.number_of_edges()}")

    # 4. 預先分析引擎特徵掃描
    t0 = time.time()
    pre_analysis = analyze_schematic_features(G)
    t_pre = time.time() - t0
    summary = pre_analysis["summary"]
    buses = summary.buses if hasattr(summary, "buses") else summary.get("buses", [])
    platforms = summary.platforms if hasattr(summary, "platforms") else summary.get("platforms", [])
    print(f"\n🔍 5. 電路特徵預先分析完成 (耗時: {t_pre:.3f} 秒):")
    print(f"   - 偵測匯流排協定: {buses}")
    print(f"   - 識別晶片平台架構: {platforms}")
    print(f"   - 推薦 DRC 規則數: {len(pre_analysis['recommended_rules'])}")
    for r in pre_analysis['recommended_rules']:
        r_id = r.id if hasattr(r, "id") else r["id"]
        r_name = r.name if hasattr(r, "name") else r["name"]
        r_cat = r.category if hasattr(r, "category") else r["category"]
        print(f"     * [{r_id}] {r_name} ({r_cat})")

    # 5. 執行全部 4 條確定性 Heuristic 圖論規則
    print(f"\n⚙️ 6. 執行啟發式圖論 DRC 檢測 (Heuristic Rules):")
    heuristic_rule_ids = [
        "RULE-PWR-CAP-DERATING",
        "RULE-PWR-DECOUPLING",
        "RULE-CONN-PINOUT"
    ]
    t0 = time.time()
    heuristic_violations = run_all_heuristic_checks(G, heuristic_rule_ids)
    t_heu = time.time() - t0
    print(f"   - 檢測完成，耗時: {t_heu:.3f} 秒，產出項目數: {len(heuristic_violations)}")
    for v in heuristic_violations:
        st_icon = "✅ PASS" if v["status"] == "PASS" else ("⚠️ WARN" if v["status"] == "WARNING" else "❌ FAIL")
        print(f"     [{st_icon}] {v['rule_id']}: {v['rule_title']}")
        print(f"        -> 現況: {v['description']}")
        print(f"        -> 建議: {v['comment']}")

    # 6. 執行 3 條 LLM 語意邏輯推理規則 (真實呼叫本地 LLM)
    print(f"\n🧠 7. 執行本地 LLM 邏輯推理審查 (Local LLM Reasoning via LiteLLM):")
    print(f"   - LLM 端點: {settings.LOCAL_LLM_URL}")
    print(f"   - LLM 模型: {settings.LOCAL_LLM_MODEL}")
    llm_rule_ids = [
        "RULE-LLM-SD-MODE",
        "RULE-LLM-POWER-SEQUENCE",
        "RULE-LLM-LEVEL-SHIFT"
    ]
    t0 = time.time()
    llm_violations = run_all_llm_checks(G, llm_rule_ids)
    t_llm = time.time() - t0
    print(f"   - LLM 推理完成，耗時: {t_llm:.3f} 秒，產出項目數: {len(llm_violations)}")
    for v in llm_violations:
        actual = v.get("evidence_trail", {}).get("llm_actual_called", False)
        actual_str = "🔥 本地 LLM 真實調用成功" if actual else "⚡ 啟發式降級"
        st_icon = "✅ PASS" if v["status"] == "PASS" else ("⚠️ WARN" if v["status"] == "WARNING" else "❌ FAIL")
        print(f"     [{st_icon}] {v['rule_id']}: {v['rule_title']} ({actual_str})")
        print(f"        -> 現況: {v['description']}")
        print(f"        -> 技術依據: {v.get('evidence_trail', {}).get('llm_reasoning_summary', '無')}")
        print(f"        -> 耗時: {v.get('evidence_trail', {}).get('execution_time_ms', 0)} ms")

    # 7. 彙整最終 DRC 報告
    all_violations = heuristic_violations + llm_violations
    pass_cnt = sum(1 for v in all_violations if v["status"] == "PASS")
    fail_cnt = sum(1 for v in all_violations if v["status"] == "FAIL")
    warn_cnt = sum(1 for v in all_violations if v["status"] == "WARNING")
    total_cnt = len(all_violations)
    pass_rate = round((pass_cnt / total_cnt) * 100, 1) if total_cnt > 0 else 100.0

    report = {
        "report_id": f"REP-VERIFY-{int(time.time())}",
        "schema_version": "1.0.0",
        "sample_files": {
            "xml": os.path.basename(xml_path),
            "netlist": os.path.basename(netlist_path)
        },
        "graph_statistics": {
            "total_nodes": G.number_of_nodes(),
            "component_nodes": len(comp_nodes),
            "net_nodes": len(net_nodes),
            "unique_edges": G.number_of_edges()
        },
        "summary": {
            "total_rules_checked": total_cnt,
            "pass_count": pass_cnt,
            "fail_count": fail_cnt,
            "warning_count": warn_cnt,
            "pass_rate_percentage": pass_rate
        },
        "violations": all_violations
    }

    output_report_path = os.path.abspath("storage/reports/sample_fixture_drc_report.json")
    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"📊 8. 最終 DRC 審查報告統計 (Report Summary):")
    print(f"   - 總審查規則數: {total_cnt}")
    print(f"   - 通過項目 (PASS): {pass_cnt}")
    print(f"   - 警告項目 (WARNING): {warn_cnt}")
    print(f"   - 違規項目 (FAIL): {fail_cnt}")
    print(f"   - 設計規則通過率: {pass_rate}%")
    print(f"   - 完整 JSON 報告已輸出至: {output_report_path}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
