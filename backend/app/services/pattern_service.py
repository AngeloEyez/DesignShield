"""
Pattern 規則與 PartDB 檔案掃描與熱載入服務 (Pattern & PartDB Service)

職責:
1. 掃描 patterns/ 目錄樹 (Level 1~3, PartDB, Tags)
2. 快取解析後的結構與原始 YAML 內容至記憶體
3. 支援 reload() 熱重載與動態驗證
"""

import os
import glob
import json
import logging
from typing import Dict, List, Any, Optional
import yaml

logger = logging.getLogger("designshield.pattern_service")

# 根目錄與 patterns 目錄定位
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PATTERNS_DIR = os.path.join(BASE_DIR, "patterns")


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

    def reload(self) -> Dict[str, Any]:
        """清除快取並重新載入 patterns 目錄"""
        self._cache = None
        self._partdb_cache = {}
        self._level3_map = {}
        return self.get_pattern_tree(force_refresh=True)

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
