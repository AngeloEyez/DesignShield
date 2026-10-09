# DesignShield SDK 開發者指南：YAML 伴生腳本開發 (Developer Guide)

本手冊指導硬體工程師、領域專家與 AI 代理如何使用 `designshield.sdk` 開發 **Level 3 DRC 伴生動態檢查腳本** (`patterns/rules/scripts/*.py`)。

---

## 1. 什麼是 YAML 伴生腳本？

在 DesignShield 的 Level 3 設計規則驗證中，我們採用「混合式評估架構」：
* **宣告式 YAML (`type: "topology_check"`)**：用於極速評估通用的電路底線（例如：所有 I2C 匯流排都必須有上拉電阻）。
* **動態 Python 腳本 (`type: "python_script"`)**：當規則涉及**特定 IC 晶片型號的進階電氣要求**（例如：STM32F4 在特定頻率下嚴禁對地電容、阻值需介於 2k~10k 歐姆）時，YAML 會透過 `script_path` 引用一支伴生 Python 腳本，結合 `PartDB` 零件規格庫進行精確查表與決定性驗證。

所有伴生腳本統一存放於：
```
patterns/rules/scripts/<checker_name>.py
```

---

## 2. 腳本標準結構與入口函式

每一支伴生 Python 腳本都必須定義且匯出標準入口函式 `execute()`：

```python
"""
I2C 動態特規檢查腳本
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
    執行規則檢查

    Args:
        context: 注入之執行期上下文 (包含 context.target 目標節點)
        graph_api: 拓撲查詢唯讀介面
        part_db: 晶片規格查表介面
        params: YAML 傳遞之額外自訂參數 (選填)

    Returns:
        Union[List[RuleViolation], RuleResult]: 
            - 若有違規：回傳 List[RuleViolation]
            - 若完全合規：回傳 RuleResult.PASS 或空清單 []
    """
    violations: List[RuleViolation] = []
    
    # 撰寫檢查邏輯...
    
    return violations if violations else RuleResult.PASS
```

---

## 3. 核心 API 使用手冊

### 3.1 `context`: 執行期上下文
* `context.target`：命中 YAML `trigger_conditions` 的目標圖譜節點（通常為匯流排網路 `NetNode` 或零件 `ComponentNode`）。
  * 支援**屬性存取**與**字典存取**：
    * `net.name` 或 `net['net_name']`：網路名稱（例如 `"I2C1_SDA"`）。
    * `net.bus_type`：匯流排類型（例如 `"I2C"`）。
    * `net.is_power` / `net.is_ground`：布林標記。
    * `net.operating_voltage`：工作公稱電壓（例如 `3.3`）。

### 3.2 `graph_api`: 唯讀拓撲安全查詢
`GraphAPI` 提供針對電路圖譜的高階拓撲查詢方法，回傳的節點皆已封裝為 `ComponentNode` 或 `NetNode`：

| 方法名稱 | 說明 | 回傳型別 |
| :--- | :--- | :--- |
| `get_master_device(bus_node)` | 取得連接於此匯流排之主控晶片 (MCU/SoC) | `Optional[ComponentNode]` |
| `get_slave_devices(bus_node)` | 取得連接於此匯流排之所有受控晶片 (Sensor, EEPROM 等) | `List[ComponentNode]` |
| `get_pullup_resistors(net_node)` | 取得一端連接至該網路且另一端連接至電源軌之上拉電阻 | `List[ComponentNode]` |
| `has_capacitor_to_gnd(net_node)` | 檢查該網路是否有電容連接至地 (GND) | `bool` |
| `has_series_resistor(net_node)` | 檢查訊號路徑上是否配置串聯匹配電阻 | `bool` |
| `has_component_in_series(net_node, component_type)` | 檢查訊號路徑是否串聯指定類型元件 (如 `"Resistor"`, `"Capacitor"`) | `bool` |
| `get_connected_components(net_node)` | 取得連接於此網路的所有實體元件清單 | `List[ComponentNode]` |
| `get_connected_nets(comp_node)` | 取得連接於此元件的所有網路清單 | `List[NetNode]` |

**ComponentNode 常用屬性**：
* `comp.pn`：零件型號（例如 `"STM32F405"`）。
* `comp.ref_des`：電路板參考位號（例如 `"U1"`, `"R12"`）。
* `comp.part_value`：標稱值（例如 `"4.7k"`, `"100nF"`）。
* `comp.functional_role`：動態拓撲角色（例如 `"Bus_Master"`, `"Pull_up"`, `"Filter"`）。
* 若為電阻，`comp.get("resistance_ohm")` 會提供解析後之數值浮點數（例如 `4700.0`）。

### 3.3 `part_db`: 晶片規格庫查表
* `part_db.query(pn=str, interface=Optional[str])`：
  查詢晶片在特定介面的硬體規範：
  ```python
  ic_specs = part_db.query(pn=master_ic.pn, interface="I2C")
  if ic_specs:
      evidence = ic_specs.get("_meta", {}) # 溯源手冊頁碼與引述
      forbid_cap = ic_specs.get("forbid_gnd_capacitor", False)
      pullup_range = ic_specs.get("pullup_range_ohms") # [min, max]
  ```

### 3.4 `RuleViolation`: 違規報告建構
當偵測到違反電氣規範時，建立 `RuleViolation` 物件：
```python
violations.append(RuleViolation(
    message=f"主控晶片 {master_ic.ref_des} ({master_ic.pn}) 規格書明定 I2C SCL/SDA 嚴禁外接接地電容。",
    severity="ERROR", # 可為 "FATAL", "ERROR", "WARNING", "INFO"
    evidence=evidence_meta # 將規格書來源注入違規證據中
))
```

---

## 4. 沙盒安全開發限制 (Sandbox Security Rules)

所有伴生腳本皆在 **SDK Sandbox** 受限環境中執行。腳本編譯前會經過嚴格的 AST 靜態語法樹審查，執行時亦享有 5 秒逾時保護：

* ❌ **絕對禁止的行為**：
  * 禁止匯入底層系統模組：`os`, `sys`, `subprocess`, `socket`, `shutil`, `pathlib` 等。
  * 禁止檔案系統存取：禁止呼叫 `open()`。
  * 禁止動態代碼執行：禁止呼叫 `eval()`, `exec()`, `compile()`。
  * 禁止危險反射：禁止存取 `__subclasses__`, `__bases__`, `__globals__`。
* ✅ **允許匯入的標準函式庫**：
  * `math`, `re`, `json`, `typing`, `dataclasses`, `enum`, `collections`, `itertools`, `functools`。
  * `designshield.sdk` 及其所有導出模組。

---

## 5. 完整範例 (End-to-End Walkthrough)

### 步驟 1: 建立 YAML 規則檔案 (`patterns/rules/interfaces/i2c_stm32_dynamic.yaml`)
```yaml
name: "I2C_PartDB_Dynamic_Compliance"
description: "結合 PartDB 零件規格庫，針對主控晶片驗證阻值範圍與禁止接地電容特規"
tags: ["I2C", "PartDB", "Compliance"]
severity: "Error"

trigger_conditions:
  graph_match:
    attributes:
      type: "net"
      bus_type: "I2C"

check_logic:
  - type: "python_script"
    script_path: "patterns/rules/scripts/i2c_dynamic_checker.py"
```

### 步驟 2: 建立伴生腳本 (`patterns/rules/scripts/i2c_dynamic_checker.py`)
```python
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
    target_net = context.target
    violations: List[RuleViolation] = []

    # 1. 取得 Master IC
    master_ic = graph_api.get_master_device(target_net)
    if not master_ic:
        return RuleResult.PASS

    # 2. 查閱 PartDB 規格
    ic_specs = part_db.query(pn=master_ic.pn, interface="I2C")
    if not ic_specs:
        return RuleResult.PASS

    evidence_meta = ic_specs.get("_meta", {})

    # 3. 檢查接地電容
    if ic_specs.get("forbid_gnd_capacitor", False):
        if graph_api.has_capacitor_to_gnd(target_net):
            violations.append(RuleViolation(
                message=f"晶片 {master_ic.ref_des} ({master_ic.pn}) 規格書明定 I2C 嚴禁外接接地電容",
                severity="ERROR",
                evidence=evidence_meta
            ))

    # 4. 檢查上拉電阻阻值
    if "pullup_range_ohms" in ic_specs:
        pullup_range = ic_specs["pullup_range_ohms"]
        for res in graph_api.get_pullup_resistors(target_net):
            val = res.get("resistance_ohm")
            if val is not None and not (pullup_range[0] <= val <= pullup_range[1]):
                violations.append(RuleViolation(
                    message=f"上拉電阻 {res.ref_des} 阻值 ({val}Ω) 不在要求範圍 {pullup_range} 內",
                    severity="ERROR",
                    evidence=evidence_meta
                ))

    return violations if violations else RuleResult.PASS
```

### 步驟 3: 本地驗證
完成編寫後，於專案根目錄執行統一校驗腳本：
```bash
python scripts/validate_rules.py
```
確認退出碼為 `0` 且無安全違規後，即可提交 Git PR。
