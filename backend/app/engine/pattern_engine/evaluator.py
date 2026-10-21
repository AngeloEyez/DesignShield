import re
from typing import Dict, Any, List, Union, Optional
from .models import MatchCondition

class PatternEvaluator:
    """
    通用條件評估器 (Generic Pattern Evaluator)
    
    負責針對元件特徵資料，進行 match_any / match_all 與通用屬性運算子 (Key-Operator Map) 的遞迴樹狀求值。
    支援運算子:
      - exact / eq: 完全相等 (字串預設大小寫不敏感，可顯式指定 case_sensitive: true)
      - ne: 不等於
      - regex: 正規表達式比對 (支援 re.search 與快取預熱)
      - prefix: 前綴比對
      - suffix: 後綴比對
      - in: 集合成員比對 (傳入列表)
      - not_in: 集合排除
      - min / gte: 數值下限 (大於等於)
      - max / lte: 數值上限 (小於等於)
      - exists: 屬性是否存在且非空 (布林值)
    """

    def __init__(self):
        # 快取編譯好的正規表示式 (Regex Cache)，以字串作為 key
        self._regex_cache: Dict[str, re.Pattern] = {}

    def clear_cache(self):
        """清空正規表示式快取"""
        self._regex_cache.clear()

    def get_cached_regex_count(self) -> int:
        """取得目前快取之編譯正則數量"""
        return len(self._regex_cache)

    def _get_regex(self, pattern_str: str) -> re.Pattern:
        """取得或編譯快取的正規表示式"""
        if pattern_str not in self._regex_cache:
            self._regex_cache[pattern_str] = re.compile(pattern_str)
        return self._regex_cache[pattern_str]

    def precompile_condition(self, condition: Union[MatchCondition, Dict[str, Any]]) -> int:
        """
        遞迴走訪條件樹，預先將所有 regex 運算子字串編譯並快取至 _regex_cache。
        
        @param {Union[MatchCondition, Dict[str, Any]]} condition - 條件物件或字典
        @returns {int} 成功編譯或快取之正則式數量
        """
        if isinstance(condition, MatchCondition):
            cond_dict = condition.to_dict()
        elif isinstance(condition, dict):
            cond_dict = condition
        else:
            return 0

        count = 0
        if "match_any" in cond_dict and isinstance(cond_dict["match_any"], list):
            for sub in cond_dict["match_any"]:
                count += self.precompile_condition(sub)
        if "match_all" in cond_dict and isinstance(cond_dict["match_all"], list):
            for sub in cond_dict["match_all"]:
                count += self.precompile_condition(sub)

        for key, val in cond_dict.items():
            if key in ("match_any", "match_all"):
                continue
            if isinstance(val, dict):
                reg = val.get("regex")
                if reg and isinstance(reg, str):
                    self._get_regex(reg)
                    count += 1
            elif key == "regex" and isinstance(val, str):
                self._get_regex(val)
                count += 1

        return count

    @staticmethod
    def extract_attribute_value(attr_name: str, comp_data: Dict[str, Any]) -> Any:
        """
        自 comp_data 中提取屬性值。支援標準屬性與 props.<key> / user_props.<key>。
        
        @param {str} attr_name - 屬性名稱 (如 'ref_des', 'bom', 'props.CCL')
        @param {Dict[str, Any]} comp_data - 元件資料字典
        @returns {Any} 屬性值或 None
        """
        if attr_name == "any_text":
            val = str(comp_data.get("part_value", "") or "")
            mpn = str(comp_data.get("mfg_pn", "") or "")
            desc = str(comp_data.get("description", "") or "")
            pkg = str(comp_data.get("package", "") or "")
            return f"{val} {mpn} {desc} {pkg}".strip()

        if attr_name.startswith("props.") or attr_name.startswith("user_props."):
            prop_key = attr_name.split(".", 1)[1]
            user_props = comp_data.get("user_props") or {}
            if isinstance(user_props, dict):
                return user_props.get(prop_key)
            return None

        if attr_name == "bom":
            bom_val = comp_data.get("bom")
            if bom_val is not None and str(bom_val).strip() != "":
                return str(bom_val).strip()
            user_props = comp_data.get("user_props") or {}
            if isinstance(user_props, dict):
                return str(user_props.get("BOM", "")).strip()
            return ""

        if attr_name in comp_data:
            return comp_data[attr_name]

        # 若標準欄位查無，嘗試由 user_props 尋找
        user_props = comp_data.get("user_props") or {}
        if isinstance(user_props, dict) and attr_name in user_props:
            return user_props[attr_name]

        return None

    def evaluate_operator(self, attr_val: Any, rule_spec: Any) -> bool:
        """
        評估單一屬性值是否滿足規格 (支援純值簡寫或運算子字典)。
        
        @param {Any} attr_val - 提取之實際屬性值
        @param {Any} rule_spec - 規則宣告之運算子字典或簡寫純值
        @returns {bool} 若符合回傳 True
        """
        # 1. 簡寫：若 rule_spec 為 list，視為 in 運算子
        if isinstance(rule_spec, list):
            return self._eval_in(attr_val, rule_spec, case_sensitive=False)

        # 2. 簡寫：若 rule_spec 為純值 (str, int, float, bool)，視為 exact / eq
        if not isinstance(rule_spec, dict):
            return self._eval_exact(attr_val, rule_spec, case_sensitive=False)

        # 3. 運算子字典
        case_sensitive = bool(rule_spec.get("case_sensitive", False))

        for op, target in rule_spec.items():
            if op == "case_sensitive":
                continue

            if op in ("exact", "eq"):
                if not self._eval_exact(attr_val, target, case_sensitive):
                    return False
            elif op == "ne":
                if self._eval_exact(attr_val, target, case_sensitive):
                    return False
            elif op == "regex":
                if not self._eval_regex(attr_val, str(target)):
                    return False
            elif op == "prefix":
                if not self._eval_prefix(attr_val, str(target), case_sensitive):
                    return False
            elif op == "suffix":
                if not self._eval_suffix(attr_val, str(target), case_sensitive):
                    return False
            elif op == "in":
                targets = target if isinstance(target, (list, set, tuple)) else [target]
                if not self._eval_in(attr_val, targets, case_sensitive):
                    return False
            elif op == "not_in":
                targets = target if isinstance(target, (list, set, tuple)) else [target]
                if self._eval_in(attr_val, targets, case_sensitive):
                    return False
            elif op in ("min", "gte"):
                if not self._eval_gte(attr_val, target):
                    return False
            elif op in ("max", "lte"):
                if not self._eval_lte(attr_val, target):
                    return False
            elif op == "exists":
                has_val = attr_val is not None and str(attr_val).strip() != ""
                if bool(target) != has_val:
                    return False
            else:
                # 未知運算子，預設不滿足
                return False

        return True

    def _eval_exact(self, val: Any, target: Any, case_sensitive: bool) -> bool:
        """完全相等比對 (數值型轉數值比對，字串型依 case_sensitive 進行大小寫比對)"""
        if val is None:
            return target is None

        # 數值比對
        if isinstance(target, (int, float)) and not isinstance(target, bool):
            try:
                return float(val) == float(target)
            except (ValueError, TypeError):
                return False

        s_val = str(val)
        s_target = str(target)
        if not case_sensitive:
            return s_val.strip().upper() == s_target.strip().upper()
        return s_val.strip() == s_target.strip()

    def _eval_regex(self, val: Any, pattern: str) -> bool:
        """正規表達式比對"""
        s_val = "" if val is None else str(val)
        return bool(self._get_regex(pattern).search(s_val))

    def _eval_prefix(self, val: Any, prefix: str, case_sensitive: bool) -> bool:
        """前綴比對"""
        s_val = "" if val is None else str(val)
        if not case_sensitive:
            return s_val.upper().startswith(prefix.upper())
        return s_val.startswith(prefix)

    def _eval_suffix(self, val: Any, suffix: str, case_sensitive: bool) -> bool:
        """後綴比對"""
        s_val = "" if val is None else str(val)
        if not case_sensitive:
            return s_val.upper().endswith(suffix.upper())
        return s_val.endswith(suffix)

    def _eval_in(self, val: Any, target_list: Any, case_sensitive: bool) -> bool:
        """列表包含比對"""
        for item in target_list:
            if self._eval_exact(val, item, case_sensitive):
                return True
        return False

    def _eval_gte(self, val: Any, min_val: Any) -> bool:
        """大於等於比對"""
        try:
            return float(val) >= float(min_val)
        except (ValueError, TypeError):
            return False

    def _eval_lte(self, val: Any, max_val: Any) -> bool:
        """小於等於比對"""
        try:
            return float(val) <= float(max_val)
        except (ValueError, TypeError):
            return False

    def evaluate(self, condition: Union[MatchCondition, Dict[str, Any]], comp_data: Dict[str, Any]) -> bool:
        """
        評估目前的 condition 是否符合 comp_data 的特徵。
        
        @param {Union[MatchCondition, Dict[str, Any]]} condition - 條件物件或字典
        @param {Dict[str, Any]} comp_data - 元件資料字典
        @returns {bool} 若符合回傳 True
        """
        if isinstance(condition, MatchCondition):
            cond_dict = condition.to_dict()
        elif isinstance(condition, dict):
            cond_dict = condition
        else:
            return True

        # 1. 遞迴處理 match_any (OR 邏輯：任一成立即可)
        if "match_any" in cond_dict and cond_dict["match_any"] is not None:
            if not any(self.evaluate(sub_cond, comp_data) for sub_cond in cond_dict["match_any"]):
                return False

        # 2. 遞迴處理 match_all (AND 邏輯：所有皆須成立)
        if "match_all" in cond_dict and cond_dict["match_all"] is not None:
            if not all(self.evaluate(sub_cond, comp_data) for sub_cond in cond_dict["match_all"]):
                return False

        # 3. 評估當前層級宣告的所有屬性比對 (AND 邏輯：所有屬性皆須符合)
        for attr_name, rule_spec in cond_dict.items():
            if attr_name in ("match_any", "match_all"):
                continue
            if rule_spec is None:
                continue
            attr_val = self.extract_attribute_value(attr_name, comp_data)
            if not self.evaluate_operator(attr_val, rule_spec):
                return False

        return True
