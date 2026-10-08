#!/usr/bin/env python3
"""
統一規則庫與 PartDB 驗證腳本 (Unified Rule & PartDB Validator)

職責:
1. 校驗 Level 1 (patterns/components/) 元件規則 YAML
2. 校驗 Level 2 (patterns/buses/, power/, signals/) 拓撲規則 YAML
3. 校驗 Level 3 (patterns/rules/) DRC 規則 YAML (必填欄位、Severity 白名單、Tags 白名單)
4. 校驗 PartDB (patterns/partdb/data/) 零件資料是否符合 patterns/partdb/schema/*.json
"""

import os
import sys
import json
import glob
import yaml
from jsonschema import validate, ValidationError


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS_DIR = os.path.join(ROOT_DIR, "patterns")
TAGS_SCHEMA_FILE = os.path.join(PATTERNS_DIR, "rules", "tags.schema.json")
PARTDB_SCHEMA_DIR = os.path.join(PATTERNS_DIR, "partdb", "schema")
PARTDB_DATA_DIR = os.path.join(PATTERNS_DIR, "partdb", "data")

VALID_SEVERITIES = {"Fatal", "Error", "Warning", "Info"}
VALID_CHECK_TYPES = {"topology_check", "python_script", "llm_agent"}


def load_tags_whitelist() -> set:
    if not os.path.exists(TAGS_SCHEMA_FILE):
        return set()
    with open(TAGS_SCHEMA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return set(data.get("items", {}).get("enum", []))


def validate_level1_rules() -> list:
    errors = []
    comp_dir = os.path.join(PATTERNS_DIR, "components")
    if not os.path.exists(comp_dir):
        return errors
        
    for yf in glob.glob(os.path.join(comp_dir, "*.yaml")):
        try:
            with open(yf, "r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
            for idx, data in enumerate(docs):
                if not data:
                    continue
                if not isinstance(data, dict):
                    errors.append(f"[Level 1] {yf} doc[{idx}]: 內容必須為 YAML 字典結構")
                    continue
                if "name" not in data or "priority" not in data or "matches" not in data or "assigns" not in data:
                    errors.append(f"[Level 1] {yf} doc[{idx}]: 缺少 name / priority / matches / assigns 必填欄位")
        except Exception as e:
            errors.append(f"[Level 1] {yf}: 解析失敗 - {e}")
    return errors


def validate_level2_rules() -> list:
    errors = []
    for sub in ["buses", "power", "signals"]:
        sub_dir = os.path.join(PATTERNS_DIR, sub)
        if not os.path.exists(sub_dir):
            continue
        for yf in glob.glob(os.path.join(sub_dir, "*.yaml")):
            try:
                with open(yf, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    errors.append(f"[Level 2] {yf}: 內容必須為 YAML 字典結構")
                    continue
                if "name" not in data or "category" not in data or "priority" not in data:
                    errors.append(f"[Level 2] {yf}: 缺少 name / category / priority 必填欄位")
            except Exception as e:
                errors.append(f"[Level 2] {yf}: 解析失敗 - {e}")
    return errors


def validate_level3_rules(tags_whitelist: set) -> list:
    errors = []
    rules_dir = os.path.join(PATTERNS_DIR, "rules")
    if not os.path.exists(rules_dir):
        return errors
        
    for root, _, files in os.walk(rules_dir):
        for f in files:
            if not f.endswith(".yaml") and not f.endswith(".yml"):
                continue
            yf = os.path.join(root, f)
            rel_path = os.path.relpath(yf, ROOT_DIR)
            try:
                with open(yf, "r", encoding="utf-8") as stream:
                    data = yaml.safe_load(stream)
                    
                if not isinstance(data, dict):
                    errors.append(f"[Level 3] {rel_path}: 內容必須為 YAML 字典結構")
                    continue
                    
                for required in ["name", "tags", "severity", "trigger_conditions", "check_logic"]:
                    if required not in data:
                        errors.append(f"[Level 3] {rel_path}: 缺少必填欄位 '{required}'")
                        
                severity = data.get("severity")
                if severity not in VALID_SEVERITIES:
                    errors.append(f"[Level 3] {rel_path}: severity '{severity}' 不在合法值內 {VALID_SEVERITIES}")
                    
                tags = data.get("tags", [])
                if not isinstance(tags, list):
                    errors.append(f"[Level 3] {rel_path}: 'tags' 必須為陣列")
                else:
                    for t in tags:
                        if tags_whitelist and t not in tags_whitelist:
                            errors.append(f"[Level 3] {rel_path}: 標籤 '{t}' 未在 tags.schema.json 白名單註冊")
                            
                check_logic = data.get("check_logic")
                steps = check_logic if isinstance(check_logic, list) else [check_logic]
                for idx, step in enumerate(steps):
                    if not isinstance(step, dict) or "type" not in step:
                        errors.append(f"[Level 3] {rel_path}: check_logic[{idx}] 缺少 'type' 欄位")
                    elif step["type"] not in VALID_CHECK_TYPES:
                        errors.append(f"[Level 3] {rel_path}: check_logic 類型 '{step['type']}' 不在合法值內 {VALID_CHECK_TYPES}")
                        
            except Exception as e:
                errors.append(f"[Level 3] {rel_path}: YAML 解析失敗 - {e}")
    return errors


def validate_partdb() -> list:
    errors = []
    if not os.path.exists(PARTDB_DATA_DIR):
        return errors

    # 載入所有 schema
    schemas = {}
    if os.path.exists(PARTDB_SCHEMA_DIR):
        for sf in glob.glob(os.path.join(PARTDB_SCHEMA_DIR, "schema_*.json")):
            interface_key = os.path.basename(sf).replace("schema_", "").replace(".json", "").upper()
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    schemas[interface_key] = json.load(f)
            except Exception as e:
                errors.append(f"[PartDB Schema] {sf}: Schema 解析失敗 - {e}")

    for yf in glob.glob(os.path.join(PARTDB_DATA_DIR, "*.yaml")):
        rel_path = os.path.relpath(yf, ROOT_DIR)
        try:
            with open(yf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                errors.append(f"[PartDB] {rel_path}: 內容必須為 YAML 字典結構")
                continue
            if "pn" not in data:
                errors.append(f"[PartDB] {rel_path}: 缺少必填零件型號欄位 'pn'")
                
            interfaces = data.get("interfaces", {})
            for if_name, if_spec in interfaces.items():
                schema = schemas.get(if_name.upper())
                if schema:
                    try:
                        validate(instance=if_spec, schema=schema)
                    except ValidationError as ve:
                        errors.append(f"[PartDB] {rel_path} 介面 '{if_name}' 不符合 Schema: {ve.message}")
        except Exception as e:
            errors.append(f"[PartDB] {rel_path}: 解析失敗 - {e}")

    return errors


def main():
    print("=" * 60)
    print("🚀 DesignShield 規則庫與 PartDB 統一校驗器")
    print("=" * 60)

    tags_whitelist = load_tags_whitelist()
    print(f"[*] 載入 Tags 白名單: {len(tags_whitelist)} 個合法標籤")

    all_errors = []
    
    print("[*] 正在驗證 Level 1 元件辨識規則...")
    l1_errs = validate_level1_rules()
    all_errors.extend(l1_errs)
    
    print("[*] 正在驗證 Level 2 網路拓撲規則...")
    l2_errs = validate_level2_rules()
    all_errors.extend(l2_errs)
    
    print("[*] 正在驗證 Level 3 DRC 驗證規範...")
    l3_errs = validate_level3_rules(tags_whitelist)
    all_errors.extend(l3_errs)
    
    print("[*] 正在驗證 PartDB 零件規格庫...")
    pdb_errs = validate_partdb()
    all_errors.extend(pdb_errs)

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
