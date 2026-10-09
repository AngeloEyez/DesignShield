import os
import yaml
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from .models import ComponentRule
from .evaluator import PatternEvaluator

logger = logging.getLogger(__name__)

class ComponentPatternEngine:
    """
    狀態化單例。負責在啟動時載入所有 components 下的 YAML 規則，
    並於執行期間提供高效能的 `First-Match Wins` 元件分類服務。
    """
    def __init__(self):
        self.rules: List[ComponentRule] = []
        self.evaluator = PatternEvaluator()
        self._is_loaded = False
        self._rules_dir: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ComponentPatternEngine":
        return get_component_engine()

    def get_cached_regex_count(self) -> int:
        """取得目前 evaluator 快取之已編譯正則表達式數量"""
        return self.evaluator.get_cached_regex_count()

    def reload(self, rules_dir: Optional[str] = None) -> int:
        """
        強制清空規則與正規式編譯快取，並重新載入與預熱編譯。
        回傳載入的規則數量。
        """
        target_dir = rules_dir or self._rules_dir
        if not target_dir:
            candidates = [
                Path(__file__).resolve().parents[4] / "patterns" / "components",
                Path(__file__).resolve().parents[3] / "patterns" / "components",
                Path.cwd() / "patterns" / "components",
                Path("/app/patterns/components"),
            ]
            for p in candidates:
                if p.exists() and p.is_dir():
                    target_dir = str(p)
                    break

        self.rules = []
        self.evaluator.clear_cache()
        self._is_loaded = False
        if target_dir:
            self.load_rules(str(target_dir), force=True)
        return len(self.rules)

    def load_rules(self, rules_dir: str, force: bool = False):
        """
        掃描目錄下所有 .yaml 檔案，解析為 ComponentRule 物件，
        並依 priority 由大到小排序。
        """
        if self._is_loaded and not force:
            return

        self._rules_dir = rules_dir
        loaded_rules = []
        path = Path(rules_dir)
        
        if not path.exists() or not path.is_dir():
            logger.warning(f"Pattern directory not found: {rules_dir}")
            return

        for yaml_file in sorted(path.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        if not doc:
                            continue
                        rule = ComponentRule(**doc)
                        # 若 YAML 同目錄存在同檔名伴生腳本且未手動指定，自動關聯
                        companion_py = yaml_file.with_suffix(".py")
                        if not rule.script_path and companion_py.exists():
                            rule.script_path = str(companion_py)
                        loaded_rules.append(rule)
            except Exception as e:
                logger.error(f"Failed to load rule from {yaml_file}: {e}")

        # 依 priority 降冪排序 (First-Match Wins 機制的核心)
        self.rules = sorted(loaded_rules, key=lambda r: r.priority, reverse=True)
        self._is_loaded = True
        logger.info(f"Loaded {len(self.rules)} component pattern rules from {rules_dir}.")

        # 完整走訪每條規則的所有條件樹，預先編譯正則表達式並寫入 evaluator 快取
        regex_compiled_count = 0
        for rule in self.rules:
            try:
                regex_compiled_count += self.evaluator.precompile_condition(rule.matches)
            except Exception as e:
                logger.warning(f"Failed to precompile regex for rule {rule.name}: {e}")
        logger.info(f"Precompiled {regex_compiled_count} regex patterns into cache (cache size: {self.evaluator.get_cached_regex_count()}).")

    def classify(self, ref_des: str, part_value: str, description: str, package: str, mfg_pn: str, pins_count: int) -> Tuple[Dict[str, Any], str]:
        """
        對單一元件進行分類。
        返回: (AssignData 的字典, 命中的 Rule Name)
        若全部未命中，返回預設的 Unknown 保底分類。
        """
        if not self._is_loaded:
            logger.error("ComponentPatternEngine has not loaded rules yet!")
            
        comp_data = {
            "ref_des": ref_des or "",
            "part_value": part_value or "",
            "description": description or "",
            "package": package or "",
            "mfg_pn": mfg_pn or "",
            "pins_count": pins_count or 0
        }

        # First-Match Wins 評估
        for rule in self.rules:
            if self.evaluator.evaluate(rule.matches, comp_data):
                assigned = rule.assigns.dict()
                # 若存在伴生腳本，呼叫沙盒執行進行深層特徵解算與屬性覆蓋
                if rule.script_path and os.path.exists(rule.script_path):
                    try:
                        from designshield.sdk.sandbox import SandboxedScriptRunner
                        with open(rule.script_path, "r", encoding="utf-8") as sf:
                            py_source = sf.read()
                        custom_assign = SandboxedScriptRunner.execute_script_source(
                            source_code=py_source,
                            context=comp_data,
                            graph_api=None,
                            part_db=None,
                            params={},
                            filename=rule.script_path
                        )
                        if isinstance(custom_assign, dict):
                            assigned.update(custom_assign)
                    except Exception as e:
                        logger.warning("Level 1 伴生腳本 [%s] 執行失敗: %s", rule.script_path, e)
                return assigned, rule.name

        # Fallback 保底機制 (未命中任何規則)
        fallback_assign = {
            "category": "Unknown",
            "sub_category": "Unknown",
            "functional_role": "None",
            "is_electrical": True, # 預設當作電氣件保留
            "confidence": 0.1
        }
        return fallback_assign, "fallback_unknown"

# 全域單例
_engine_instance = ComponentPatternEngine()

def get_component_engine() -> ComponentPatternEngine:
    """
    獲取引擎單例。
    若在非 FastAPI (如 CLI 或測試腳本) 環境中被呼叫，
    且尚未載入規則，則執行懶加載 (Lazy Load) 自動讀取 YAML。
    """
    if not _engine_instance._is_loaded:
        try:
            candidates = [
                Path(__file__).resolve().parents[4] / "patterns" / "components",
                Path(__file__).resolve().parents[3] / "patterns" / "components",
                Path.cwd() / "patterns" / "components",
                Path("/app/patterns/components"),
            ]
            for p in candidates:
                if p.exists() and p.is_dir():
                    _engine_instance.load_rules(str(p))
                    if _engine_instance._is_loaded:
                        break
        except Exception as e:
            logger.error("Auto lazy-load pattern rules failed: %s", e)
    return _engine_instance
