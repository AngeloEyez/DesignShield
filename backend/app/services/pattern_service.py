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

        # 透過 DB 同步狀態覆蓋記憶體快取與引擎 (Reconcile)
        self.reconcile_and_apply_rule_statuses(tree)

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

    def reconcile_and_apply_rule_statuses(self, tree: Optional[Dict[str, Any]] = None) -> None:
        """
        掃描磁碟 YAML 規則與資料庫 RuleStatus 進行核對 (Reconcile):
        1. 若 DB 無該規則：由 YAML 初始化 (Seed-on-First-Sight) 寫入 DB。
        2. 若 DB 已有該規則：以 DB 的 enabled 狀態覆蓋記憶體快取與 Engine。
        3. 若 DB 存在但磁碟上已無該規則：刪除 DB 中的孤兒紀錄，保持對齊。
        """
        target_tree = tree or self._cache
        if not target_tree:
            return

        try:
            from backend.app.db.session import SessionLocal
            from backend.app.models.rule_status import RuleStatus
            from backend.app.engine.pattern_engine import get_component_engine
            from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
        except Exception as e:
            logger.warning("Could not import database models for rule status reconcile: %s", e)
            return

        db = SessionLocal()
        try:
            # 1. 收集磁碟上所有 Level 1 ~ 3 規則
            disk_rules = {}  # rule_name -> dict(level, category_path, yaml_enabled, rule_obj)
            for r in target_tree.get("level1", []):
                r_name = r.get("name")
                if r_name:
                    dom = r.get("_domain")
                    cat_path = f"level1_components/{dom}" if dom and dom != "root" else "level1_components"
                    disk_rules[r_name] = {
                        "level": "level1",
                        "category_path": cat_path,
                        "yaml_enabled": bool(r.get("enabled", True)),
                        "obj": r
                    }

            for r in target_tree.get("level2", []):
                r_name = r.get("name")
                if r_name:
                    disk_rules[r_name] = {
                        "level": "level2",
                        "category_path": f"level2_topology/{r.get('_domain', 'buses')}",
                        "yaml_enabled": bool(r.get("enabled", True)),
                        "obj": r
                    }

            for r in target_tree.get("level3", []):
                r_name = r.get("name")
                if r_name:
                    disk_rules[r_name] = {
                        "level": "level3",
                        "category_path": f"level3_rules/{r.get('_domain', '')}".rstrip('/'),
                        "yaml_enabled": bool(r.get("enabled", True)),
                        "obj": r
                    }

            # 2. 查詢 DB 中現存所有規則狀態
            db_records = {rec.rule_name: rec for rec in db.query(RuleStatus).all()}

            # 3. 處理新規則 (新增至 DB) 與舊規則狀態覆蓋 (以 DB 為主)
            comp_engine = get_component_engine()
            topo_engine = TopologyPatternEngine.get_instance()

            for r_name, d_info in disk_rules.items():
                if r_name not in db_records:
                    # DB 無紀錄：以 YAML 狀態播種至 DB
                    new_rec = RuleStatus(
                        rule_name=r_name,
                        level=d_info["level"],
                        category_path=d_info["category_path"],
                        enabled=d_info["yaml_enabled"]
                    )
                    db.add(new_rec)
                    # 確保記憶體物件保持 YAML 狀態
                    d_info["obj"]["enabled"] = d_info["yaml_enabled"]
                else:
                    # DB 已有紀錄：以 DB 的 enabled 覆蓋記憶體快取
                    db_enabled = bool(db_records[r_name].enabled)
                    d_info["obj"]["enabled"] = db_enabled
                    # 同步更新底層 Engine 規則物件
                    if d_info["level"] == "level1":
                        comp_engine.update_rule_enabled(r_name, db_enabled)
                    elif d_info["level"] == "level2":
                        topo_engine.update_rule_enabled(r_name, db_enabled)

            # 4. 刪除磁碟已不存在的孤兒紀錄
            for r_name, rec in db_records.items():
                if r_name not in disk_rules:
                    db.delete(rec)
                    logger.info("Removed orphan rule status from DB: %s", r_name)

            db.commit()
            logger.info("Reconciled %d disk rules with DB rule statuses.", len(disk_rules))
        except Exception as e:
            db.rollback()
            logger.error("Failed to reconcile rule statuses with database: %s", e)
        finally:
            db.close()

    def update_rule_status(self, rule_name: str, enabled: bool) -> Optional[Dict[str, Any]]:
        """
        即時更新特定規則的 enabled 狀態:
        1. 寫入 DB
        2. 同步更新 PatternService 記憶體快取
        3. 同步更新 ComponentPatternEngine / TopologyPatternEngine
        """
        from backend.app.db.session import SessionLocal
        from backend.app.models.rule_status import RuleStatus
        from backend.app.engine.pattern_engine import get_component_engine
        from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine

        if not self._cache:
            self.get_pattern_tree()

        db = SessionLocal()
        try:
            rec = db.query(RuleStatus).filter(RuleStatus.rule_name == rule_name).first()
            if not rec:
                # 若 DB 尚無記錄，從現存快取判斷該規則層級與路徑
                target_rule = None
                target_level = "level3"
                category_path = "level3_rules"

                for r in self._cache.get("level1", []):
                    if r.get("name") == rule_name:
                        target_rule = r
                        target_level = "level1"
                        dom = r.get("_domain")
                        category_path = f"level1_components/{dom}" if dom and dom != "root" else "level1_components"
                        break

                if not target_rule:
                    for r in self._cache.get("level2", []):
                        if r.get("name") == rule_name:
                            target_rule = r
                            target_level = "level2"
                            category_path = f"level2_topology/{r.get('_domain', 'buses')}"
                            break

                if not target_rule:
                    for r in self._cache.get("level3", []):
                        if r.get("name") == rule_name:
                            target_rule = r
                            target_level = "level3"
                            category_path = f"level3_rules/{r.get('_domain', '')}".rstrip('/')
                            break

                if not target_rule:
                    return None

                rec = RuleStatus(
                    rule_name=rule_name,
                    level=target_level,
                    category_path=category_path,
                    enabled=enabled
                )
                db.add(rec)
            else:
                rec.enabled = enabled

            db.commit()

            # 同步更新記憶體快取
            found = False
            for r in self._cache.get("level1", []):
                if r.get("name") == rule_name:
                    r["enabled"] = enabled
                    found = True
                    get_component_engine().update_rule_enabled(rule_name, enabled)
                    break

            if not found:
                for r in self._cache.get("level2", []):
                    if r.get("name") == rule_name:
                        r["enabled"] = enabled
                        found = True
                        TopologyPatternEngine.get_instance().update_rule_enabled(rule_name, enabled)
                        break

            if not found:
                for r in self._cache.get("level3", []):
                    if r.get("name") == rule_name:
                        r["enabled"] = enabled
                        found = True
                        break

            if rule_name in self._level3_map:
                self._level3_map[rule_name]["enabled"] = enabled

            return {
                "rule_name": rule_name,
                "level": rec.level,
                "enabled": enabled,
                "updated_at": rec.updated_at.isoformat() if rec.updated_at else None
            }
        except Exception as e:
            db.rollback()
            logger.error("Failed to update rule status for %s: %s", rule_name, e)
            raise
        finally:
            db.close()

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
        self._partdb_parts = partdb_data.get("parts", [])
        self._partdb_cache = {p["pn"]: p for p in self._partdb_parts}

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
                "partdb_parts_count": len(self._partdb_parts),
                "tags_count": len(tags)
            }
        }
        self._cache = tree

        # 首次載入或強制更新時進行狀態核對與覆寫
        self.reconcile_and_apply_rule_statuses(tree)

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

    def query_partdb(
        self,
        pn: str,
        interface: Optional[str] = None,
        mfg: Optional[str] = None,
        supplier: Optional[str] = None,
        vendor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        查詢特定型號之 PartDB 規格 (支援雙層檢索: Mfg 精確比對 + 唯一料號自動匹配)

        Args:
            pn: 零件料號 (如 "TXS0102", "STM32F405")
            interface: 介面名稱 (如 "I2C", "USB")
            mfg: 原廠製造商簡稱或代碼 (如 "TI", "ST", "TDK"，對齊 XML 之 Mfg 屬性)
            supplier: 相容參數 (同 mfg)
            vendor: 舊版相容參數 (同 mfg)
        """
        if not getattr(self, "_partdb_parts", None):
            self.get_pattern_tree()

        target_pn = (pn or "").strip().upper()
        if not target_pn:
            return None

        target_mfg = mfg or supplier or vendor
        clean_mfg = target_mfg.strip().upper() if target_mfg else None

        # 1. 收集料號匹配之候選元件
        candidates = []
        for p in self._partdb_parts:
            p_pn = p.get("pn", "").upper()
            if p_pn == target_pn or target_pn.startswith(p_pn) or p_pn.startswith(target_pn):
                candidates.append(p)

        matched_part = None

        # 2. 若指定製造商，比對 mfg (並相容 legacy supplier / vendor_code / manufacturer)
        if clean_mfg:
            for c in candidates:
                c_mfg_val = c.get("mfg", "").upper()
                c_sup = c.get("supplier", "").upper()
                c_code = c.get("vendor_code", "").upper()
                c_legacy_mfg = c.get("manufacturer", "").upper()
                if (clean_mfg == c_mfg_val or clean_mfg in c_mfg_val or c_mfg_val in clean_mfg or
                    clean_mfg == c_sup or clean_mfg in c_sup or
                    clean_mfg == c_code or clean_mfg in c_legacy_mfg or c_legacy_mfg in clean_mfg):
                    matched_part = c
                    break

        # 3. 若未指定製造商或指定製造商未查得
        if not matched_part:
            if len(candidates) == 1:
                # 庫中唯一元件，自動命中
                matched_part = candidates[0]
            elif len(candidates) > 1:
                # 存在多家製造商同料號衝突，記錄警告並取第一家
                mfgs_found = [c.get("mfg") or c.get("supplier") or c.get("vendor_code") or c.get("manufacturer") for c in candidates]
                logger.warning(
                    f"PartDB query '{pn}' is ambiguous across multiple manufacturers: {mfgs_found}. "
                    f"Selecting default: {candidates[0].get('mfg') or candidates[0].get('supplier')}"
                )
                matched_part = candidates[0]

        if not matched_part:
            return None

        if interface:
            return matched_part.get("interfaces", {}).get(interface)
        return matched_part

    def _load_level1(self) -> List[Dict[str, Any]]:
        results = []
        l1_dir = os.path.join(PATTERNS_DIR, "level1_components")
        if not os.path.exists(l1_dir):
            l1_dir = os.path.join(PATTERNS_DIR, "components")
        if not os.path.exists(l1_dir):
            return results

        # 全自動遞迴掃描 level1_components/ 下所有子目錄 (支援任意子目錄與深度)
        for root, _, files in os.walk(l1_dir):
            for file in sorted(files):
                if file.startswith("_") or not (file.endswith(".yaml") or file.endswith(".yml")):
                    continue
                fpath = os.path.join(root, file)
                rel_dir = os.path.relpath(root, l1_dir)
                domain = "root" if rel_dir == "." else rel_dir.split(os.sep)[0]
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                        docs = list(yaml.safe_load_all(raw_text))
                        for doc in docs:
                            if doc and isinstance(doc, dict):
                                doc["_domain"] = domain
                                doc["_filename"] = file
                                doc["_rel_path"] = os.path.relpath(fpath, PATTERNS_DIR)
                                doc["_raw_yaml"] = raw_text
                                doc["enabled"] = bool(doc.get("enabled", True))
                                results.append(doc)
                except Exception as e:
                    logger.error(f"Error loading Level 1 pattern {fpath}: {e}")
        return results

    def _load_level2(self) -> List[Dict[str, Any]]:
        results = []
        l2_dir = os.path.join(PATTERNS_DIR, "level2_topology")
        if os.path.exists(l2_dir):
            # 全自動遞迴掃描 level2_topology/ 下所有子目錄 (buses/, power/, signals/, 等)
            for root, _, files in os.walk(l2_dir):
                for file in sorted(files):
                    if file.startswith("_") or not (file.endswith(".yaml") or file.endswith(".yml")):
                        continue
                    fpath = os.path.join(root, file)
                    rel_dir = os.path.relpath(root, l2_dir)
                    domain = "root" if rel_dir == "." else rel_dir.split(os.sep)[0]
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            raw_text = f.read()
                            data = yaml.safe_load(raw_text)
                            if data and isinstance(data, dict):
                                data["_domain"] = domain
                                data["_filename"] = file
                                data["_rel_path"] = os.path.relpath(fpath, PATTERNS_DIR)
                                data["_raw_yaml"] = raw_text
                                data["enabled"] = bool(data.get("enabled", True))
                                results.append(data)
                    except Exception as e:
                        logger.error(f"Error loading Level 2 pattern {fpath}: {e}")
        else:
            # 向後相容舊版三目錄
            for domain in ["buses", "power", "signals"]:
                dpath = os.path.join(PATTERNS_DIR, domain)
                if not os.path.exists(dpath):
                    continue
                for fpath in sorted(glob.glob(os.path.join(dpath, "*.yaml"))):
                    fname = os.path.basename(fpath)
                    if fname.startswith("_"):
                        continue
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            raw_text = f.read()
                            data = yaml.safe_load(raw_text)
                            if data and isinstance(data, dict):
                                data["_domain"] = domain
                                data["_filename"] = fname
                                data["_raw_yaml"] = raw_text
                                data["enabled"] = bool(data.get("enabled", True))
                                results.append(data)
                    except Exception as e:
                        logger.error(f"Error loading Level 2 pattern {fpath}: {e}")
        return results

    def _load_level3(self) -> List[Dict[str, Any]]:
        results = []
        rules_dir = os.path.join(PATTERNS_DIR, "level3_rules")
        if not os.path.exists(rules_dir):
            rules_dir = os.path.join(PATTERNS_DIR, "rules")
        if not os.path.exists(rules_dir):
            return results

        for root, _, files in os.walk(rules_dir):
            for file in sorted(files):
                if file.startswith("_") or not (file.endswith(".yaml") or file.endswith(".yml")):
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
                            data["enabled"] = bool(data.get("enabled", True))
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
            yaml_files = []
            for root, _, files in os.walk(data_dir):
                for f in sorted(files):
                    if f.endswith(".yaml") or f.endswith(".yml"):
                        yaml_files.append(os.path.join(root, f))
            for df in sorted(yaml_files):
                try:
                    with open(df, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                        data = yaml.safe_load(raw_text)
                        if data and isinstance(data, dict):
                            data["_filename"] = os.path.basename(df)
                            data["_raw_yaml"] = raw_text
                            data["_rel_path"] = os.path.relpath(df, PATTERNS_DIR)
                            rel_dir = os.path.relpath(os.path.dirname(df), data_dir)
                            data["_domain"] = "root" if rel_dir == "." else rel_dir
                            if "mfg" not in data and "_" in data["_filename"]:
                                data["mfg"] = data["_filename"].split("_")[0]
                            if "mfg_pn" not in data and "pn" in data:
                                data["mfg_pn"] = data["pn"]
                            parts.append(data)
                except Exception as e:
                    logger.error(f"Error loading PartDB data {df}: {e}")

        return {"parts": parts, "schemas": schemas}

    def _load_tags(self) -> List[str]:
        tags_file = os.path.join(PATTERNS_DIR, "level3_rules", "tags.schema.json")
        if not os.path.exists(tags_file):
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
