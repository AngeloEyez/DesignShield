#!/usr/bin/env python3
"""
統一規則庫與 PartDB 驗證腳本 (Unified Rule & PartDB Validator)

職責:
1. 校驗 Level 1 (patterns/level1_components/) 元件規則 YAML 結構與正規表示式有效性
2. 校驗 Level 2 (patterns/level2_topology/) 拓撲規則 YAML 結構與正規表示式有效性
3. 校驗 Level 3 (patterns/level3_rules/) DRC 規則 YAML (必填欄位、Severity 白名單、Tags 白名單)
4. 校驗 PartDB (patterns/partdb/data/) 零件資料是否符合 patterns/partdb/schema/*.json
"""

import os
import sys
import json
import glob
import re
import ast
from typing import List, Set, Tuple, Optional, Dict, Any
import yaml
from jsonschema import validate, ValidationError

# 定位專案根目錄與 patterns 目錄
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS_DIR = os.path.join(ROOT_DIR, "patterns")

if sys.platform == "win32":
    # 確保 Windows 終端輸出 UTF-8 編碼，避免 cp950 編碼錯誤
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

VALID_SEVERITIES = {"Fatal", "Error", "Warning", "Info"}
VALID_CHECK_TYPES = {"topology_check", "python_script", "llm_agent"}


def load_tags_whitelist(patterns_dir: Optional[str] = None) -> Set[str]:
    p_dir = patterns_dir or PATTERNS_DIR
    tags_schema_file = os.path.join(p_dir, "level3_rules", "tags.schema.json")
    if not os.path.exists(tags_schema_file):
        tags_schema_file = os.path.join(p_dir, "rules", "tags.schema.json")
    if not os.path.exists(tags_schema_file):
        return set()
    try:
        with open(tags_schema_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("items", {}).get("enum", []))
    except Exception:
        return set()


def _check_level1_regexes(cond: Any, file_label: str) -> List[str]:
    """遞迴檢查 Level 1 條件中的 regex 語法是否合法"""
    regex_errors = []
    if not isinstance(cond, dict):
        return regex_errors

    if "match_any" in cond and isinstance(cond["match_any"], list):
        for sub in cond["match_any"]:
            regex_errors.extend(_check_level1_regexes(sub, file_label))
    if "match_all" in cond and isinstance(cond["match_all"], list):
        for sub in cond["match_all"]:
            regex_errors.extend(_check_level1_regexes(sub, file_label))

    for k, v in cond.items():
        if k in ("match_any", "match_all"):
            continue
        pattern = None
        if isinstance(v, dict) and "regex" in v:
            pattern = v["regex"]
        elif (k == "regex" or k.endswith("_regex")) and isinstance(v, str):
            pattern = v

        if pattern:
            try:
                re.compile(pattern)
            except re.error as e:
                regex_errors.append(f"{file_label}: 屬性 '{k}' 之正規表示式 '{pattern}' 語法錯誤 - {e}")
    return regex_errors


SNAKE_CASE_PATTERN = re.compile(r'^[a-z0-9_]+$')


def validate_level1_rules(patterns_dir: Optional[str] = None) -> List[str]:
    errors = []
    p_dir = patterns_dir or PATTERNS_DIR
    comp_dir = os.path.join(p_dir, "level1_components")
    if not os.path.exists(comp_dir):
        comp_dir = os.path.join(p_dir, "components")
    if not os.path.exists(comp_dir):
        return errors

    for yf in sorted(glob.glob(os.path.join(comp_dir, "*.yaml")) + glob.glob(os.path.join(comp_dir, "*.yml"))):
        fname = os.path.basename(yf)
        if fname.startswith("_"):
            continue  # 忽略範本檔
        try:
            with open(yf, "r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
            for idx, data in enumerate(docs):
                label = f"[Level 1] {fname} doc[{idx}]"
                if not data:
                    continue
                if not isinstance(data, dict):
                    errors.append(f"{label}: 內容必須為 YAML 字典結構")
                    continue
                for req in ["name", "priority", "matches", "assigns"]:
                    if req not in data:
                        errors.append(f"{label}: 缺少必填欄位 '{req}'")

                # 校驗命名規範 (全系統統一小寫蛇形)
                name = data.get("name")
                if name and not SNAKE_CASE_PATTERN.match(name):
                    errors.append(f"{label}: 規則名稱 '{name}' 必須為合法小寫蛇形 (snake_case，如 rule_passive_resistor)")

                # 校驗 enabled 欄位型別 (選擇性，若存在必須為布林值)
                if "enabled" in data and not isinstance(data["enabled"], bool):
                    errors.append(f"{label}: 'enabled' 欄位必須為布林值 (true 或 false)")

                # 校驗正則語法
                if "matches" in data and isinstance(data["matches"], dict):
                    errors.extend(_check_level1_regexes(data["matches"], label))
        except Exception as e:
            errors.append(f"[Level 1] {fname}: YAML 解析失敗 - {e}")
    return errors


def _check_level2_condition_regex(cond: Any, file_label: str) -> List[str]:
    errs = []
    if not isinstance(cond, dict):
        return errs
    if "match_any" in cond and isinstance(cond["match_any"], list):
        for block in cond["match_any"]:
            if isinstance(block, dict) and "match_all" in block and isinstance(block["match_all"], list):
                for sub in block["match_all"]:
                    errs.extend(_check_level2_condition_regex(sub, file_label))
    if "match_all" in cond and isinstance(cond["match_all"], list):
        for sub in cond["match_all"]:
            errs.extend(_check_level2_condition_regex(sub, file_label))
    for rf in ["net_name_regex", "pin_name_regex"]:
        p = cond.get(rf)
        if p:
            try:
                re.compile(p)
            except re.error as e:
                errs.append(f"{file_label}: 欄位 '{rf}' 之正規表示式 '{p}' 語法錯誤 - {e}")
    return errs


def validate_level2_rules(patterns_dir: Optional[str] = None) -> List[str]:
    errors = []
    p_dir = patterns_dir or PATTERNS_DIR
    l2_dir = os.path.join(p_dir, "level2_topology")
    yaml_files = []
    if os.path.exists(l2_dir):
        for root, _, files in os.walk(l2_dir):
            for f in sorted(files):
                if not f.startswith("_") and (f.endswith(".yaml") or f.endswith(".yml")):
                    yaml_files.append((os.path.relpath(os.path.join(root, f), l2_dir), os.path.join(root, f)))
    else:
        for sub in ["buses", "power", "signals"]:
            sub_dir = os.path.join(p_dir, sub)
            if not os.path.exists(sub_dir):
                continue
            for yf in sorted(glob.glob(os.path.join(sub_dir, "*.yaml"))):
                fname = os.path.basename(yf)
                if not fname.startswith("_"):
                    yaml_files.append((f"{sub}/{fname}", yf))

    for rel_display, yf in yaml_files:
        label = f"[Level 2] {rel_display}"
        try:
            with open(yf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                errors.append(f"{label}: 內容必須為 YAML 字典結構")
                continue
            for req in ["name", "category", "priority"]:
                if req not in data:
                    errors.append(f"{label}: 缺少必填欄位 '{req}'")

            # 校驗命名規範 (全系統統一小寫蛇形)
            name = data.get("name")
            if name and not SNAKE_CASE_PATTERN.match(name):
                errors.append(f"{label}: 規則名稱 '{name}' 必須為合法小寫蛇形 (snake_case，如 i2c_bus, generic_power_rail)")

            # 校驗 enabled 欄位型別 (選擇性，若存在必須為布林值)
            if "enabled" in data and not isinstance(data["enabled"], bool):
                errors.append(f"{label}: 'enabled' 欄位必須為布林值 (true 或 false)")

            # 校驗 signals 內的 regex
            signals = data.get("signals", [])
            if isinstance(signals, list):
                for s_idx, sig in enumerate(signals):
                    if isinstance(sig, dict) and "matches" in sig:
                        errors.extend(_check_level2_condition_regex(sig["matches"], f"{label} signals[{s_idx}]"))
        except Exception as e:
            errors.append(f"{label}: YAML 解析失敗 - {e}")
    return errors


def validate_level3_rules(tags_whitelist: Optional[Set[str]] = None, patterns_dir: Optional[str] = None) -> List[str]:
    errors = []
    p_dir = patterns_dir or PATTERNS_DIR
    rules_dir = os.path.join(p_dir, "level3_rules")
    if not os.path.exists(rules_dir):
        rules_dir = os.path.join(p_dir, "rules")
    if not os.path.exists(rules_dir):
        return errors

    whitelist = tags_whitelist if tags_whitelist is not None else load_tags_whitelist(p_dir)

    for root, _, files in os.walk(rules_dir):
        for f in sorted(files):
            if f.startswith("_") or not (f.endswith(".yaml") or f.endswith(".yml")):
                continue
            yf = os.path.join(root, f)
            rel_path = os.path.relpath(yf, p_dir)
            label = f"[Level 3] {rel_path}"
            try:
                with open(yf, "r", encoding="utf-8") as stream:
                    data = yaml.safe_load(stream)

                if not isinstance(data, dict):
                    errors.append(f"{label}: 內容必須為 YAML 字典結構")
                    continue

                for required in ["name", "tags", "severity", "trigger_conditions", "check_logic"]:
                    if required not in data:
                        errors.append(f"{label}: 缺少必填欄位 '{required}'")

                # 校驗命名規範 (全系統統一小寫蛇形)
                name = data.get("name")
                if name and not SNAKE_CASE_PATTERN.match(name):
                    errors.append(f"{label}: 規則名稱 '{name}' 必須為合法小寫蛇形 (snake_case，如 i2c_pull_up_existence)")

                # 校驗 enabled 欄位型別 (選擇性，若存在必須為布林值)
                if "enabled" in data and not isinstance(data["enabled"], bool):
                    errors.append(f"{label}: 'enabled' 欄位必須為布林值 (true 或 false)")

                severity = data.get("severity")
                if severity and severity not in VALID_SEVERITIES:
                    errors.append(f"{label}: severity '{severity}' 不在合法值內 {VALID_SEVERITIES}")

                tags = data.get("tags", [])
                if not isinstance(tags, list):
                    errors.append(f"{label}: 'tags' 必須為陣列")
                else:
                    for t in tags:
                        if whitelist and t not in whitelist:
                            errors.append(f"{label}: 標籤 '{t}' 未在 tags.schema.json 白名單註冊")

                check_logic = data.get("check_logic")
                steps = check_logic if isinstance(check_logic, list) else [check_logic]
                for idx, step in enumerate(steps):
                    if not isinstance(step, dict) or "type" not in step:
                        errors.append(f"{label}: check_logic[{idx}] 缺少 'type' 欄位")
                    elif step["type"] not in VALID_CHECK_TYPES:
                        errors.append(f"{label}: check_logic 類型 '{step['type']}' 不在合法值內 {VALID_CHECK_TYPES}")
                    elif step["type"] == "python_script":
                        script_path = step.get("script_path")
                        companion_default = os.path.join(os.path.dirname(yf), f"{os.path.splitext(f)[0]}.py")
                        candidates = []
                        if script_path:
                            candidates.extend([
                                os.path.join(ROOT_DIR, script_path),
                                os.path.join(ROOT_DIR, script_path.replace("patterns/rules", "patterns/level3_rules")),
                                os.path.join(p_dir, "level3_rules", script_path),
                                os.path.join(p_dir, "rules", script_path),
                                os.path.join(os.path.dirname(yf), os.path.basename(script_path)),
                            ])
                        candidates.append(companion_default)
                        matched_path = next((p for p in candidates if os.path.exists(p)), None)
                        if not matched_path:
                            errors.append(f"{label}: check_logic[{idx}] 伴生腳本不存在: '{script_path or os.path.basename(companion_default)}'")
                        else:
                            try:
                                from designshield.sdk.sandbox import ASTSecurityValidator, SecurityViolationError
                                with open(matched_path, "r", encoding="utf-8") as sf:
                                    source_code = sf.read()
                                validator = ASTSecurityValidator(filename=os.path.basename(matched_path))
                                validator.validate_code(source_code)

                                parsed_ast = ast.parse(source_code)
                                has_execute = any(isinstance(n, ast.FunctionDef) and n.name == "execute" for n in parsed_ast.body)
                                if not has_execute:
                                    errors.append(f"{label}: 伴生腳本 '{os.path.basename(matched_path)}' 必須定義 'def execute(...)' 入口函式")
                            except SecurityViolationError as sve:
                                errors.append(f"{label}: 伴生腳本 '{os.path.basename(matched_path)}' 沙盒安全審查失敗: {sve}")
                            except Exception as e:
                                errors.append(f"{label}: 伴生腳本 '{os.path.basename(matched_path)}' 驗證異常: {e}")

            except Exception as e:
                errors.append(f"{label}: YAML 解析失敗 - {e}")
    return errors


def validate_partdb(patterns_dir: Optional[str] = None) -> List[str]:
    errors = []
    p_dir = patterns_dir or PATTERNS_DIR
    partdb_data_dir = os.path.join(p_dir, "partdb", "data")
    partdb_schema_dir = os.path.join(p_dir, "partdb", "schema")

    if not os.path.exists(partdb_data_dir):
        return errors

    # 載入所有 schema
    schemas = {}
    if os.path.exists(partdb_schema_dir):
        for sf in glob.glob(os.path.join(partdb_schema_dir, "schema_*.json")):
            interface_key = os.path.basename(sf).replace("schema_", "").replace(".json", "").upper()
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    schemas[interface_key] = json.load(f)
            except Exception as e:
                errors.append(f"[PartDB Schema] {os.path.basename(sf)}: Schema 解析失敗 - {e}")

    # 遞迴遍歷 partdb_data_dir 及其所有分類子目錄 (ics, passives, etc.)
    yaml_files = []
    for root, _, files in os.walk(partdb_data_dir):
        for f in files:
            if f.endswith(".yaml") or f.endswith(".yml"):
                yaml_files.append(os.path.join(root, f))

    for yf in sorted(yaml_files):
        fname = os.path.basename(yf)
        if fname.startswith("_"):
            continue  # 忽略範本或內部系統檔案

        rel_name = os.path.relpath(yf, partdb_data_dir)
        label = f"[PartDB] {rel_name}"

        # 檢驗檔案命名規則: 必須為 <Mfg>_<PartNumber>.yaml
        stem = os.path.splitext(fname)[0]
        if "_" not in stem:
            errors.append(f"{label}: 檔名格式必須為 '<Mfg>_<PartNumber>.yaml' (例如 TI_TXS0102.yaml)")

        try:
            with open(yf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                errors.append(f"{label}: 內容必須為 YAML 字典結構")
                continue
            if "pn" not in data:
                errors.append(f"{label}: 缺少必填零件型號欄位 'pn'")

            # 驗證 mfg 與檔名一致性
            mfg = data.get("mfg") or data.get("supplier") or data.get("vendor_code")
            if mfg and not stem.upper().startswith(mfg.upper() + "_"):
                errors.append(f"{label}: 檔名前綴 '{stem.split('_')[0]}' 與檔案內宣告之 mfg '{mfg}' 不相符")

            # 1. 驗證根 Schema (Base Metadata)
            part_root_schema = schemas.get("PART")
            if part_root_schema:
                try:
                    validate(instance=data, schema=part_root_schema)
                except ValidationError as ve:
                    errors.append(f"{label} 基本結構不符合 schema_part.json: {ve.message}")

            # 2. 驗證引腳矩陣特徵 (pinout)
            if "pinout" in data:
                pinout_schema = schemas.get("PINOUT")
                if pinout_schema:
                    try:
                        validate(instance=data["pinout"], schema=pinout_schema)
                    except ValidationError as ve:
                        errors.append(f"{label} 'pinout' 不符合 Schema: {ve.message}")

            # 3. 驗證供電軌特徵 (power_rails)
            if "power_rails" in data:
                pr_schema = schemas.get("POWER_RAILS")
                if pr_schema:
                    try:
                        validate(instance=data["power_rails"], schema=pr_schema)
                    except ValidationError as ve:
                        errors.append(f"{label} 'power_rails' 不符合 Schema: {ve.message}")

            # 4. 驗證通用零件穿透規格 (pass_through)
            if "pass_through" in data:
                pt_schema = schemas.get("PASS_THROUGH")
                if pt_schema:
                    try:
                        validate(instance=data["pass_through"], schema=pt_schema)
                    except ValidationError as ve:
                        errors.append(f"{label} 'pass_through' 不符合 Schema: {ve.message}")

            # 5. 驗證匯流排介面規格 (interfaces)
            interfaces = data.get("interfaces", {})
            for if_name, if_spec in interfaces.items():
                schema = schemas.get(if_name.upper())
                if schema:
                    try:
                        validate(instance=if_spec, schema=schema)
                    except ValidationError as ve:
                        errors.append(f"{label} 介面 '{if_name}' 不符合 Schema: {ve.message}")
        except Exception as e:
            errors.append(f"{label}: 解析失敗 - {e}")

    return errors


def validate_all_rules(patterns_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    執行規則庫全量校驗，回傳 (是否合法, 錯誤清單)。
    """
    p_dir = patterns_dir or PATTERNS_DIR
    tags_whitelist = load_tags_whitelist(p_dir)

    all_errors: List[str] = []
    all_errors.extend(validate_level1_rules(p_dir))
    all_errors.extend(validate_level2_rules(p_dir))
    all_errors.extend(validate_level3_rules(tags_whitelist, p_dir))
    all_errors.extend(validate_partdb(p_dir))

    return (len(all_errors) == 0, all_errors)


def main():
    print("=" * 60)
    print("🚀 DesignShield 規則庫與 PartDB 統一校驗器")
    print("=" * 60)

    tags_whitelist = load_tags_whitelist()
    print(f"[*] 載入 Tags 白名單: {len(tags_whitelist)} 個合法標籤")

    all_errors = []
    print("[*] 正在驗證 Level 1 元件辨識規則...")
    all_errors.extend(validate_level1_rules())
    print("[*] 正在驗證 Level 2 網路拓撲規則...")
    all_errors.extend(validate_level2_rules())
    print("[*] 正在驗證 Level 3 DRC 驗證規範...")
    all_errors.extend(validate_level3_rules(tags_whitelist))
    print("[*] 正在驗證 PartDB 零件規格庫...")
    all_errors.extend(validate_partdb())

    print("-" * 60)
    if all_errors:
        print(f"❌ 校驗失敗，發現 {len(all_errors)} 項錯誤：")
        for err in all_errors:
            print(f"  • {err}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("✅ 全數規則與 PartDB 資料校驗通過！無格式或語法錯誤。")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
