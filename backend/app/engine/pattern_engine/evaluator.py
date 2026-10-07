import re
from typing import Dict, Any, List, Union
from .models import MatchCondition

class PatternEvaluator:
    """
    負責針對單一元件資料，進行 match_any / match_all 的遞迴樹狀求值。
    """
    def __init__(self):
        # 快取編譯好的正規表示式 (Regex Cache)，以字串作為 key
        self._regex_cache: Dict[str, re.Pattern] = {}

    def _get_regex(self, pattern_str: str) -> re.Pattern:
        if pattern_str not in self._regex_cache:
            self._regex_cache[pattern_str] = re.compile(pattern_str)
        return self._regex_cache[pattern_str]

    def evaluate(self, condition: Union[MatchCondition, Dict[str, Any]], comp_data: Dict[str, Any]) -> bool:
        """
        評估目前的 condition 是否符合 comp_data 的特徵。
        支援 MatchCondition 物件或單純的字典。
        """
        # 如果是字典，將其轉為 MatchCondition 統一處理 (通常在 yaml 讀取後就會是 dict 或轉好模型)
        if isinstance(condition, dict):
            # pydantic v1 / v2 相容解析
            cond = MatchCondition(**condition)
        else:
            cond = condition

        # 遞迴處理 match_any (OR 邏輯)
        if cond.match_any is not None:
            # 只要有一個子條件為 True 就算命中
            return any(self.evaluate(sub_cond, comp_data) for sub_cond in cond.match_any)
            
        # 遞迴處理 match_all (AND 邏輯)
        if cond.match_all is not None:
            # 所有子條件都必須為 True 算命中
            return all(self.evaluate(sub_cond, comp_data) for sub_cond in cond.match_all)

        # 進入 Leaf Node (特徵比對)
        ref = comp_data.get("ref_des", "").upper()
        desc = comp_data.get("description", "").upper()
        val = comp_data.get("part_value", "").upper()
        pkg = comp_data.get("package", "").upper()
        mpn = comp_data.get("mfg_pn", "").upper()
        pins_count = comp_data.get("pins_count", 0)
        
        # 組裝模糊比對用的大字串
        combined_text = f"{val} {mpn} {desc} {pkg}"

        # 1. 檢查引腳數限制
        if cond.pin_count_min is not None and pins_count < cond.pin_count_min:
            return False
        if cond.pin_count_max is not None and pins_count > cond.pin_count_max:
            return False

        # 2. 檢查 Prefix
        if cond.ref_prefix is not None:
            if not ref.startswith(cond.ref_prefix.upper()):
                return False
        if cond.description_prefix is not None:
            if not desc.startswith(cond.description_prefix.upper()):
                return False

        # 3. 檢查 Regex
        if cond.ref_prefix_regex is not None:
            if not self._get_regex(cond.ref_prefix_regex).search(ref):
                return False
        if cond.description_regex is not None:
            if not self._get_regex(cond.description_regex).search(desc):
                return False
        if cond.value_regex is not None:
            if not self._get_regex(cond.value_regex).search(val):
                return False
        if cond.package_regex is not None:
            if not self._get_regex(cond.package_regex).search(pkg):
                return False
        if cond.any_text_regex is not None:
            if not self._get_regex(cond.any_text_regex).search(combined_text):
                return False

        # 若都沒有觸發 False，且節點不是空的 (沒有條件)，則視為 True
        # 這代表這個 Leaf 節點上的所有條件都滿足了
        return True
