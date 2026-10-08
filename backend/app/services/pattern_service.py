"""
Pattern 規則與 PartDB 檔案掃描與熱載入服務 (Pattern & PartDB Service)

職責:
1. 掃描 patterns/ 目錄樹 (Level 1~3, PartDB, Tags)
2. 快取解析後的結構與原始 YAML 內容至記憶體
3. 支援 reload() 熱重載與動態驗證
"""

import os
import sys
import glob
import json
import logging
from typing import Dict, List, Any, Optional
import yaml

# 根目錄與 patterns 目錄定位
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PATTERNS_DIR = os.path.join(BASE_DIR, "patterns")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.validate_rules import validate_all_rules

logger = logging.getLogger("designshield.pattern_service")


class PatternService:
    _instance: Optional["PatternService"] = None

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._partdb_cache: Dict[str, Dict[str, Any]] = {}
        self._level3_map: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "PatternService":
        if cls._instance is None:
            cls._instance = PatternService()
        return cls._instance

    def reload_with_compilation(self, strict: bool = True) -> Dict[str, Any]:
        """
        統一校驗並重新編譯快取:
        1. 執行 YAML 檢查工具 (validate_all_rules)
        2. 若校驗失敗且 strict=True，取消編譯並回傳錯誤清單
        3. 若通過校驗 (或 strict=False):
           a. 重新編譯 Level 1 元件分類規則與 Regex 快取
           b. 重新載入 Level 2 網路拓撲引擎
           c. 重新整理 PatternService 快取 (Level 1~3, PartDB, Tags)
           d. 計算並回傳編譯耗時與統計數據
        """
        import time
        from backend.app.engine.pattern_engine import get_component_engine
        from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine

        is_valid, errors = validate_all_rules()
        if not is_valid:
            logger.warning("YAML validation found %d errors. Strict mode=%s", len(errors), strict)
            if strict:
                return {
                    "success": False,
                    "message": f"YAML 校驗失敗，已取消編譯 (發現 {len(errors)} 項錯誤)",
                    "errors": errors,
                    "summary": self._cache.get("summary", {}) if self._cache else {},
                    "compile_stats": None
                }

        start_t = time.perf_counter()

        # 重新載入 Level 1 並預編譯 Regex
        comp_engine = get_component_engine()
        l1_count = comp_engine.reload()
        regex_count = comp_engine.get_cached_regex_count()

        # 重新載入 Level 2
        topo_engine = TopologyPatternEngine.get_instance()
        l2_count = topo_engine.reload()

        # 重新整理 PatternService 記憶體快取
        self._cache = None
        self._partdb_cache = {}
        self._level3_map = {}
        tree = self.get_pattern_tree(force_refresh=True)

        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

        compile_stats = {
            "level1_rules": l1_count,
            "level2_rules": l2_count,
            "level3_rules": len(tree.get("level3", [])),
            "partdb_parts": len(tree.get("partdb", {}).get("parts", [])),
            "regex_compiled": regex_count,
            "compile_time_ms": elapsed_ms
        }

        return {
            "success": True,
            "message": f"規則庫與編譯快取重新載入成功 (耗時 {elapsed_ms}ms)",
            "summary": tree.get("summary", {}),
            "compile_stats": compile_stats,
            "errors": errors if not is_valid else []
        }

    def initialize_and_warmup(self, strict: bool = False) -> Dict[str, Any]:
        """系統啟動時呼叫的初始化與預熱方法"""
        return self.reload_with_compilation(strict=strict)

    def reload(self) -> Dict[str, Any]:
        """清除快取並重新載入 patterns 目錄與編譯快取"""
        return self.reload_with_compilation(strict=True)

    def get_pattern_tree(self, force_refresh: bool = False) -> Dict[str, Any]:
        """取得完整的規則庫結構與檔案內容"""
        if self._cache is not None and not force_refresh:
            return self._cache

        l1_rules = self._load_level1()
        l2_rules = self._load_level2()
        l3_rules = self._load_level3()
        partdb_data = self._load_partdb()
        tags = self._load_tags()

        # 建立快速查詢 map
        self._level3_map = {r["name"]: r for r in l3_rules}
        self._partdb_cache = {p["pn"]: p for p in partdb_data.get("parts", [])}

        tree = {
            "level1": l1_rules,
            "level2": l2_rules,
            "level3": l3_rules,
            "partdb": partdb_data,
            "tags": tags,
            "summary": {
                "level1_count": len(l1_rules),
                "level2_count": len(l2_rules),
                "level3_count": len(l3_rules),
                "partdb_parts_count": len(partdb_data.get("parts", [])),
                "tags_count": len(tags)
            }
        }
        self._cache = tree
        return tree

    def get_level3_rules(self) -> List[Dict[str, Any]]:
        """取得所有 Level 3 DRC 規則"""
        if self._cache is None:
            self.get_pattern_tree()
        return self._cache.get("level3", []) if self._cache else []

    def get_level3_rule_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """依名稱查詢單一 Level 3 規則"""
        if not self._level3_map:
            self.get_pattern_tree()
        return self._level3_map.get(name)

    def query_partdb(self, pn: str, interface: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """查詢特定型號之 PartDB 規格"""
        if not self._partdb_cache:
            self.get_pattern_tree()

        # 支援大小寫不敏感比對與模糊前綴
        target_pn = pn.upper()
        matched_part = None
        for k, v in self._partdb_cache.items():
            if k.upper() == target_pn or target_pn.startswith(k.upper()) or k.upper().startswith(target_pn):
                matched_part = v
                break

        if not matched_part:
            return None

        if interface:
            return matched_part.get("interfaces", {}).get(interface)
        return matched_part

    def _load_level1(self) -> List[Dict[str, Any]]:
        results = []
        l1_dir = os.path.join(PATTERNS_DIR, "components")
        if not os.path.exists(l1_dir):
            return results

        for fpath in sorted(glob.glob(os.path.join(l1_dir, "*.yaml"))):
            fname = os.path.basename(fpath)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                    docs = list(yaml.safe_load_all(raw_text))
                    for doc in docs:
                        if doc and isinstance(doc, dict):
                            doc["_filename"] = fname
                            doc["_raw_yaml"] = raw_text
                            results.append(doc)
            except Exception as e:
                logger.error(f"Error loading Level 1 pattern {fpath}: {e}")
        return results

    def _load_level2(self) -> List[Dict[str, Any]]:
        results = []
        for domain in ["buses", "power", "signals"]:
            dpath = os.path.join(PATTERNS_DIR, domain)
            if not os.path.exists(dpath):
                continue
            for fpath in sorted(glob.glob(os.path.join(dpath, "*.yaml"))):
                fname = os.path.basename(fpath)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                        data = yaml.safe_load(raw_text)
                        if data and isinstance(data, dict):
                            data["_domain"] = domain
                            data["_filename"] = fname
                            data["_raw_yaml"] = raw_text
                            results.append(data)
                except Exception as e:
                    logger.error(f"Error loading Level 2 pattern {fpath}: {e}")
        return results

    def _load_level3(self) -> List[Dict[str, Any]]:
        results = []
        rules_dir = os.path.join(PATTERNS_DIR, "rules")
        if not os.path.exists(rules_dir):
            return results

        for root, _, files in os.walk(rules_dir):
            for file in sorted(files):
                if not (file.endswith(".yaml") or file.endswith(".yml")):
                    continue
                fpath = os.path.join(root, file)
                rel_dir = os.path.relpath(root, rules_dir)
                domain = "root" if rel_dir == "." else rel_dir
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                        data = yaml.safe_load(raw_text)
                        if data and isinstance(data, dict):
                            data["_domain"] = domain
                            data["_filename"] = file
                            data["_rel_path"] = os.path.relpath(fpath, PATTERNS_DIR)
                            data["_raw_yaml"] = raw_text
                            results.append(data)
                except Exception as e:
                    logger.error(f"Error loading Level 3 rule {fpath}: {e}")
        return results

    def _load_partdb(self) -> Dict[str, Any]:
        parts = []
        schemas = {}

        schema_dir = os.path.join(PATTERNS_DIR, "partdb", "schema")
        if os.path.exists(schema_dir):
            for sf in glob.glob(os.path.join(schema_dir, "schema_*.json")):
                iface = os.path.basename(sf).replace("schema_", "").replace(".json", "").upper()
                try:
                    with open(sf, "r", encoding="utf-8") as f:
                        schemas[iface] = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading PartDB schema {sf}: {e}")

        data_dir = os.path.join(PATTERNS_DIR, "partdb", "data")
        if os.path.exists(data_dir):
            for df in sorted(glob.glob(os.path.join(data_dir, "*.yaml"))):
                try:
                    with open(df, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                        data = yaml.safe_load(raw_text)
                        if data and isinstance(data, dict):
                            data["_filename"] = os.path.basename(df)
                            data["_raw_yaml"] = raw_text
                            parts.append(data)
                except Exception as e:
                    logger.error(f"Error loading PartDB data {df}: {e}")

        return {"parts": parts, "schemas": schemas}

    def _load_tags(self) -> List[str]:
        tags_file = os.path.join(PATTERNS_DIR, "rules", "tags.schema.json")
        if not os.path.exists(tags_file):
            return []
        try:
            with open(tags_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("items", {}).get("enum", [])
        except Exception as e:
            logger.error(f"Error loading tags schema: {e}")
            return []
