import os
import yaml
import logging
from typing import List, Dict, Any, Tuple
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

    def load_rules(self, rules_dir: str):
        """
        掃描目錄下所有 .yaml 檔案，解析為 ComponentRule 物件，
        並依 priority 由大到小排序。
        """
        if self._is_loaded:
            return

        loaded_rules = []
        path = Path(rules_dir)
        
        if not path.exists() or not path.is_dir():
            logger.warning(f"Pattern directory not found: {rules_dir}")
            return

        for yaml_file in path.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        if not doc:
                            continue
                        rule = ComponentRule(**doc)
                        loaded_rules.append(rule)
            except Exception as e:
                logger.error(f"Failed to load rule from {yaml_file}: {e}")

        # 依 priority 降冪排序 (First-Match Wins 機制的核心)
        self.rules = sorted(loaded_rules, key=lambda r: r.priority, reverse=True)
        self._is_loaded = True
        logger.info(f"Loaded {len(self.rules)} component pattern rules from {rules_dir}.")

        # 初始化時先預走訪一次所有規則，觸發 evaluator 內的 regex compile 快取
        dummy_data = {"ref_des": "", "description": "", "part_value": "", "package": "", "mfg_pn": "", "pins_count": 0}
        for rule in self.rules:
            try:
                self.evaluator.evaluate(rule.matches, dummy_data)
            except Exception:
                pass # 忽略 dummy_data 造成的潛在不匹配，我們只要觸發編譯

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
                return rule.assigns.dict(), rule.name

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
    return _engine_instance
