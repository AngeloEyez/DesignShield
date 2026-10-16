# DesignShield SDK 開發者指南：YAML 伴生腳本開發 (Developer Guide)

本手冊指導硬體工程師、領域專家與 AI 代理 (AI Agents) 如何使用 `designshield.sdk` 開發與維護 **Level 3 DRC 伴生動態檢查腳本**。

---

## 1. 什麼是 YAML 伴生腳本？

在 DesignShield 的 Level 3 設計規則驗證中，我們採用「混合式評估架構」：
* **宣告式 YAML (`type: "topology_check"`)**：用於極速評估通用的電路底線（例如：所有 I2C 匯流排都必須有上拉電阻）。
* **動態 Python 腳本 (`type: "python_script"`)**：當規則涉及**特定 IC 晶片型號的進階電氣要求**、**端到端差分通道追蹤**、**多端點扇出**或**動態裝配 BOM 狀態審計**時，YAML 會透過「同目錄、同檔名」約定自動綁定一支伴生 Python 腳本，結合 SDK 高階模型與 `PartDB` 規格庫進行精確查表與決定性驗證。

伴生腳本遵循「就近存放原則」，與所屬 YAML 規則存放於相同目錄：
```
patterns/rules/<domain>/<checker_name>.yaml
patterns/rules/<domain>/<checker_name>.py
```

---

## 2. 腳本標準結構與入口函式

每一支伴生 Python 腳本都必須定義且匯出標準入口函式 `execute()`：

```python
"""
Level 3 DRC 標準伴生腳本範本
"""
from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    DifferentialChannel,
    SingleEndedChannel,
)

def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[RulePass, RuleViolation, List[RuleViolation], RuleResult]:
    """
    執行規則檢查入口函式

    @param {RuleContext} context - 注入之執行期上下文 (包含 context.target 目標節點)
    @param {GraphAPI} graph_api - 拓撲查詢唯讀介面
    @param {PartDB} part_db - 零件規格查表介面
    @param {Dict[str, Any]} params - YAML 傳遞之額外自訂參數 (選填)
    @returns {Union[RulePass, RuleViolation, List[RuleViolation], RuleResult]} 
        - 若有違規：回傳 List[RuleViolation] 或單一 RuleViolation
        - 若完全合規：回傳 RulePass
        - 若不適用：回傳 RuleResult.SKIPPED
    """
    violations: List[RuleViolation] = []
    
    # 撰寫檢查邏輯...
    
    return violations if violations else RulePass(...)
```

---

## 3. 核心 API 使用手冊

### 3.1 `context`: 執行期上下文
* `context.target`：命中 YAML `trigger_conditions` 的目標圖譜節點（通常為匯流排網路 `NetNode` 或零件 `ComponentNode`）。
  * 支援**屬性存取**與**字典存取**：
    * `net.name` 或 `net['net_name']`：網路名稱（例如 `"USB_DP"`, `"I2C1_SDA"`）。
    * `net.bus_type`：匯流排類型（例如 `"USB"`, `"I2C"`, `"DDR"`）。
    * `net.is_power` / `net.is_ground`：布林標記。
    * `net.operating_voltage`：工作公稱電壓（例如 `3.3`）。

---

### 3.2 `graph_api`: 唯讀拓撲安全查詢
`GraphAPI` 提供針對電路圖譜的高階拓撲查詢方法，所有回傳節點皆已自動封裝：

| 方法名稱 | 說明 | 回傳型別 |
| :--- | :--- | :--- |
| `get_differential_channel(target)` | **【推薦】取得高速差分雙軌高階通道模型** (自動解析 P/N 夥伴、起點正規化、多端點扇出) | `Optional[DifferentialChannel]` |
| `get_single_ended_channel(target)` | **【推薦】取得單端訊號高階通道模型** (自動收集上拉/下拉與對地分流濾波) | `Optional[SingleEndedChannel]` |
| `is_mounted(ref_des_or_node)` | 檢查元件在當前 Config 與 MP 模式下是否上件 | `bool` |
| `has_placeholder(ref_des)` | 檢查元件是否在線路圖中預留佔位 (無論當前是否上件) | `bool` |
| `get_master_device(bus_node)` | 取得連接於此匯流排之主控晶片 (MCU/SoC/Host) | `Optional[ComponentNode]` |
| `get_slave_devices(bus_node)` | 取得連接於此匯流排之所有受控晶片 (Sensor, EEPROM 等) | `List[ComponentNode]` |
| `get_pullup_resistors(net_node)` | 取得一端連接至該網路且另一端連接至電源軌之上拉電阻 | `List[ComponentNode]` |
| `has_capacitor_to_gnd(net_node)` | 檢查該網路是否有電容連接至地 (GND) | `bool` |
| `has_series_resistor(net_node)` | 檢查訊號路徑上是否配置串聯匹配電阻 | `bool` |
| `trace_differential_end_to_end(net_node)` | 穿越串聯被動元件，底層追蹤網路到達之所有實體端點 IC/連接器 | `List[Dict[str, Any]]` |
| `check_differential_pair_symmetry(p_net, n_net)` | 底層評估 P/N 差分對端點元件與串聯電容被動元件之拓撲對稱性 | `Dict[str, Any]` |

---

### 3.3 SDK 高階通道模型 (`designshield.sdk.channel`)

為避免伴生腳本自行用十幾行程式碼重複組裝拓撲與連線，SDK 提供了**開箱即用的高階通道物件**：

#### (1) `DifferentialChannel` (高速差分雙軌通道)
呼叫 `channel = graph_api.get_differential_channel(target)` 取得：

* **屬性一覽**：
  * `channel.p_net_name` / `channel.n_net_name`：正負極主網段名稱。
  * `channel.root_ref`：源端元件 RefDes（依晶片/插座啟發式權重自動選定，如 CPU 插槽或主控 IC）。
  * `channel.target_refs`：目標接收端 RefDes 清單（支援直連 1 對多發散，如 `['XMM1', 'XMM2']`）。
  * `channel.endpoint_refs`：所有端點元件之 RefDes 清單。
  * `channel.pass_component_refs`：途經之所有串聯穿透元件 RefDes 清單（如 AC 電容、共模扼流圈 CMC 等）。
  * `channel.all_component_refs`：通道所有元件 RefDes 清單（端點 + 穿透）。
  * `channel.covered_nets`：通道覆蓋之全部子網段名稱（供引擎註冊去重防止重覆觸發）。
* **狀態審計一覽**：
  * `channel.is_continuous: bool`：**電氣訊號導通狀態**（兩端端點皆已裝配上件，且中間無任何串聯元件未上件時為 `True`；任一串聯元件未上件時為 `False`）。
  * `channel.endpoints_mounted: bool`：兩端端點是否皆已上件（若有任一端未上件，代表通道在當前配置下未啟用）。
  * `channel.unmounted_endpoints: List`：未上件端點清單。
  * `channel.unmounted_pass_components: List`：未上件串聯穿透元件清單（即造成開路中斷的元件）。
  * `channel.is_symmetric: bool`：P/N 軌道對稱性。
* **拓撲與標題輸出**：
  * `channel.title: str`：人類易讀通道標題，自動展開鏈路與多端點（例如 `"XU1 -> XMM1, XMM2 (M_B_DDR1_DQS0 差分通道)"` 或 `"TU1 -> R10 -> TJ1 (TCP0_RT_SSRX0 差分通道)"`）。
  * `channel.to_topology() -> Dict[str, Any]`：**一鍵產出符合 UniversalTopology 契約的完整拓撲字典**，內建雙軌軌道、實體焊點、直連扇出導線與串聯段落。

#### (2) `SingleEndedChannel` (單端訊號與匯流排通道)
呼叫 `channel = graph_api.get_single_ended_channel(target)` 取得：

* `channel.pull_ups`：連接至合法電源軌之上拉電阻節點清單。
* `channel.pull_downs`：連接至基準接地之地線下拉電阻節點清單。
* `channel.shunts`：對地分流濾波元件（如去耦電容、TVS 靜電防護管）。
* `channel.has_pullup: bool` / `channel.has_pulldown: bool` / `channel.has_shunt_cap: bool`：極速特徵布林判定。
* `channel.to_topology() -> Dict[str, Any]`：產出包含主訊號軌道與垂直分支（上拉至 VCC、下拉接地、接地分流）的拓撲字典。

---

### 3.4 `part_db`: 晶片規格庫查表
* `part_db.query(pn=str, interface=Optional[str])`：
  查詢晶片在特定介面的硬體規範：
  ```python
  ic_specs = part_db.query(pn=master_ic.pn, interface="I2C")
  if ic_specs:
      evidence = ic_specs.get("_meta", {}) # 溯源手冊頁碼與引述
      forbid_cap = ic_specs.get("forbid_gnd_capacitor", False)
      pullup_range = ic_specs.get("pullup_range_ohms") # [min, max]
  ```

---

### 3.5 結果回傳契約 (`RulePass` / `RuleViolation`)
* **合格回傳**：
  ```python
  return RulePass(
      evidence={
          "checked_target": channel.title,
          "audit_summary": "差分通道兩端皆已上件，串聯元件全數導通。",
          "covered_nets": channel.covered_nets,
          "topology": channel.to_topology(),
      },
      target_nodes={
          "components": channel.all_component_refs,
          "nets": channel.covered_nets,
      }
  )
  ```
* **違規回傳**：
  ```python
  violations.append(RuleViolation(
      error_message=f"差分通道中間串聯元件 {comp.display_ref_des} 未上件，導致電氣開路中斷！",
      recommendation=f"請將 {comp.ref_des} 標註為上件以維持通道導通。",
      severity="ERROR",
      evidence={
          "channel_title": channel.title,
          "topology": channel.to_topology(),
          "covered_nets": channel.covered_nets,
      },
      target_nodes={
          "components": [comp.ref_des] + channel.endpoint_refs,
          "nets": channel.covered_nets,
      }
  ))
  ```

---

## 4. 沙盒安全開發限制 (Sandbox Security Rules)

所有伴生腳本皆在 **SDK Sandbox** 受限環境中執行。腳本編譯前會經過嚴格的 AST 靜態語法樹審查，執行時享有 5 秒逾時保護：

* ❌ **絕對禁止的行為**：
  * 禁止匯入底層系統模組：`os`, `sys`, `subprocess`, `socket`, `shutil`, `pathlib` 等。
  * 禁止檔案系統存取：禁止呼叫 `open()`。
  * 禁止動態代碼執行：禁止呼叫 `eval()`, `exec()`, `compile()`。
  * 禁止危險反射：禁止存取 `__subclasses__`, `__bases__`, `__globals__`。
* ✅ **允許匯入的標準函式庫**：
  * `math`, `re`, `json`, `typing`, `dataclasses`, `enum`, `collections`, `itertools`, `functools`。
  * `designshield.sdk` 及其所有導出子模組 (`models`, `graph_api`, `part_db`, `topology`, `channel`)。

---

## 5. 實戰撰寫範例：差分通道導通性檢查

```python
"""
差分通道導通與完整性檢查 (30 行極簡範本)
"""
from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    DifferentialChannel,
)

def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[RulePass, RuleViolation, List[RuleViolation], RuleResult]:
    # 1. 一鍵取得高階差分通道模型
    channel: DifferentialChannel = graph_api.get_differential_channel(context.target)
    if not channel:
        return RuleResult.SKIPPED

    # 2. 端點數量不足 (例如單端懸空) 安全略過
    if len(channel.p_endpoints) < 2:
        return RulePass(
            evidence={
                "checked_target": channel.title,
                "topology": channel.to_topology(),
                "audit_summary": f"差分網路 {channel.p_net_name} 連接端點少於 2 個，不構成完整通道。"
            },
            target_nodes={"nets": [channel.p_net_name]}
        )

    # 3. 兩端端點若未上件，代表通道未處於啟用工作狀態，安全略過
    if not channel.endpoints_mounted:
        unm_names = [ep.get("ref_des") for ep in channel.unmounted_endpoints]
        return RulePass(
            evidence={
                "checked_target": channel.title,
                "topology": channel.to_topology(),
                "audit_summary": f"通道端點 ({', '.join(filter(None, unm_names))}) 未上件，該通道未啟用，安全略過。"
            },
            target_nodes={"components": channel.endpoint_refs, "nets": channel.covered_nets}
        )

    # 4. 兩端端點皆上件：檢查中間串聯元件是否全數上件 (開路檢查)
    violations: List[RuleViolation] = []
    for comp in channel.unmounted_pass_components:
        ref_des = getattr(comp, "ref_des", None) or comp.get("ref_des")
        display_ref = getattr(comp, "display_ref_des", None) or ref_des
        violations.append(RuleViolation(
            error_message=f"差分通道兩端端點皆已上件，但中間串聯元件 {display_ref} 標註為未上件，導致電氣開路中斷！",
            recommendation=f"請將串聯元件 {ref_des} 標註為上件以確保電氣導通。",
            severity="ERROR",
            evidence={
                "channel_title": channel.title,
                "faulty_component": ref_des,
                "topology": channel.to_topology(),
                "covered_nets": channel.covered_nets,
            },
            target_nodes={"components": [ref_des] + channel.endpoint_refs, "nets": channel.covered_nets}
        ))

    if violations:
        return violations

    # 5. 全數導通
    return RulePass(
        evidence={
            "checked_target": channel.title,
            "audit_summary": "差分通道兩端皆已上件，中間串聯元件全數正常上件，電氣訊號完整導通。",
            "topology": channel.to_topology(),
            "pass_through_components": channel.pass_component_refs,
        },
        target_nodes={"components": channel.all_component_refs, "nets": channel.covered_nets}
    )
```

---

## 6. 本地測試與驗證

撰寫伴生腳本後，請於本地執行對應單元測試以確保 100% 通過：
```bash
backend/.venv/bin/pytest backend/tests/test_sdk_channel.py
```
