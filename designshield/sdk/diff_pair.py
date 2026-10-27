"""
DesignShield SDK 高速差分對極性與夥伴推導核心模組 (Differential Pair Resolution Module)

職責:
1. 提供全系統統一的差分訊號極性判定 (diff_polarity: "P" | "N")。
2. 提供全系統統一的差分互補夥伴名稱推導 (diff_pair_partner)，包含 P -> N 與 N -> P。
3. 內建全套行業標準高速差分命名矩陣 (USB, PCIe, SATA, Ethernet, DDR, MIPI, DisplayPort 等)。
4. 支援動態載入 YAML (如 600_differential_pair.yaml) 與執行期自訂規則註冊，落實單一真實來源 (SSoT)。
"""

import re
from typing import Dict, List, Optional, Tuple, Union, Any


# ==============================================================================
# 行業標準差分極性判定正則表達式 (Industry Standard Polarity Patterns)
# ==============================================================================
DEFAULT_POSITIVE_PATTERN = (
    r"(?i)(?:_P(?:_|$)|AUXP(?:_|$)|_DP(?:_|$)|(?:_|\b)D\+(?:_|$)|"
    r"(?:TX|RX|SSTX|SSRX)P\d*$|_PLUS(?:_|$))"
)

DEFAULT_NEGATIVE_PATTERN = (
    r"(?i)(?:_N(?:_|$)|AUXN(?:_|$)|_DN(?:_|$)|(?:_|\b)D\-(?:_|$)|"
    r"(?:TX|RX|SSTX|SSRX)N\d*$|_MINUS(?:_|$))"
)


# ==============================================================================
# 行業標準差分夥伴雙向互換規則矩陣 (Standard Partner Swap Rules)
# 格式: [正極子字串, 負極子字串]
# 以 '$' 結尾者代表嚴格匹配末尾，避免誤傷網路名稱中段
# ==============================================================================
DEFAULT_PARTNER_SWAP_RULES: List[Tuple[str, str]] = [
    # 1. 隔離電容 / 電阻中間段後綴 (例如 TCP0_TX0_P_C -> TCP0_TX0_N_C)
    ("_P_", "_N_"),
    ("_DP_", "_DN_"),
    ("_D+_", "_D-_"),
    ("_PLUS_", "_MINUS_"),
    ("_TXP_", "_TXN_"),
    ("_RXP_", "_RXN_"),

    # 2. 末尾嚴格匹配 (例如 PCIE_TX_P -> PCIE_TX_N)
    ("_P$", "_N$"),
    ("_DP$", "_DN$"),
    ("_D+$", "_D-$"),
    ("D+$", "D-$"),
    ("_PLUS$", "_MINUS$"),

    # 3. AUX 輔助通道 (例如 AUXP -> AUXN, AUXP_R -> AUXN_R)
    ("AUXP_", "AUXN_"),
    ("AUXP$", "AUXN$"),

    # 4. SuperSpeed / 發射接收專用通道 (例如 SATA0_SATA_TXP -> SATA0_SATA_TXN)
    ("_TXP$", "_TXN$"),
    ("_RXP$", "_RXN$"),
    ("SSTXP", "SSTXN"),
    ("SSRXP", "SSRXN"),
    ("TXP", "TXN"),
    ("RXP", "RXN"),

    # 5. 通用寬鬆保底 (例如 USB_D+ -> USB_D-)
    ("D+", "D-"),
]


class DifferentialPairResolver:
    """
    差分對極性與夥伴網路推導器 (Differential Pair Resolver)

    提供標準化、可配置之差分訊號極性識別與互補夥伴名稱互推演算法。
    """

    def __init__(
        self,
        swap_rules: Optional[List[Tuple[str, str]]] = None,
        positive_pattern: Optional[str] = None,
        negative_pattern: Optional[str] = None,
    ):
        """
        初始化推導器實例

        Args:
            swap_rules: 自訂夥伴替換規則矩陣 [(pos_sub, neg_sub), ...]，若未提供則使用內建標準矩陣
            positive_pattern: 正極判定正則字串
            negative_pattern: 負極判定正則字串
        """
        self.swap_rules: List[Tuple[str, str]] = (
            list(swap_rules) if swap_rules is not None else list(DEFAULT_PARTNER_SWAP_RULES)
        )
        self.positive_pattern: str = positive_pattern or DEFAULT_POSITIVE_PATTERN
        self.negative_pattern: str = negative_pattern or DEFAULT_NEGATIVE_PATTERN

    def register_swap_rule(self, pos_sub: str, neg_sub: str, prepend: bool = True) -> None:
        """
        動態註冊自訂差分命名互換規則

        Args:
            pos_sub: 正極特徵字串 (例如 "_PLUS$")
            neg_sub: 負極特徵字串 (例如 "_MINUS$")
            prepend: 是否優先套用 (預設 True，優先級高於現有預設規則)
        """
        rule = (pos_sub, neg_sub)
        if rule in self.swap_rules:
            self.swap_rules.remove(rule)
        if prepend:
            self.swap_rules.insert(0, rule)
        else:
            self.swap_rules.append(rule)

    def determine_polarity(self, net_name: str) -> Optional[str]:
        """
        判定特定網路名稱之差分極性

        Args:
            net_name: 網路名稱 (例如 "SATA0_SATA_TXP", "USB_DM")

        Returns:
            Optional[str]: "P" (正極), "N" (負極), 若非差分特徵則回傳 None
        """
        if not net_name:
            return None
        clean_name = str(net_name).replace("net:", "").strip()
        if re.search(self.positive_pattern, clean_name):
            return "P"
        if re.search(self.negative_pattern, clean_name):
            return "N"
        return None

    def resolve_partner_candidates(
        self,
        net_name: str,
        target_polarity: Optional[str] = None
    ) -> List[str]:
        """
        推導互補夥伴網路之所有可能名稱候選 (例如 USB_DP -> ["USB_DN", "USB_DM"])

        Args:
            net_name: 當前網路名稱 (例如 "USB_DP")
            target_polarity: 目標極性 ("N" 或 "P")，若省略則由自身極性自動反轉

        Returns:
            List[str]: 所有符合替換特徵的候選網路名稱清單 (去重保持順序)
        """
        if not net_name:
            return []

        clean_name = str(net_name).replace("net:", "").strip()

        if target_polarity is None:
            curr_pol = self.determine_polarity(clean_name)
            if curr_pol == "P":
                target_polarity = "N"
            elif curr_pol == "N":
                target_polarity = "P"
            else:
                return []

        target_polarity = target_polarity.upper()
        candidates: List[str] = []

        if target_polarity == "N":
            for p_pat, n_pat in self.swap_rules:
                if p_pat.endswith("$"):
                    clean_p = p_pat[:-1]
                    clean_n = n_pat[:-1] if n_pat.endswith("$") else n_pat
                    if clean_name.endswith(clean_p):
                        candidates.append(clean_name[:-len(clean_p)] + clean_n)
                elif p_pat in clean_name:
                    candidates.append(clean_name.replace(p_pat, n_pat, 1))

            # 特殊協議補全：USB DM (相容 _DP -> _DM 與 DP -> DM)
            if re.search(r"(?i)_DP$", clean_name):
                candidates.append(re.sub(r"(?i)_DP$", "_DM", clean_name))
            if re.search(r"(?i)DP$", clean_name):
                candidates.append(re.sub(r"(?i)DP$", "DM", clean_name))
            if re.search(r"(?i)TXP(\d*)$", clean_name):
                candidates.append(re.sub(r"(?i)TXP(\d*)$", r"TXN\1", clean_name))
            if re.search(r"(?i)RXP(\d*)$", clean_name):
                candidates.append(re.sub(r"(?i)RXP(\d*)$", r"RXN\1", clean_name))
            if re.search(r"(?i)P$", clean_name) and not re.search(r"(?i)(?:EXP|VMP|TEMP|CLAMP|CHIP)$", clean_name):
                candidates.append(re.sub(r"(?i)P$", "N", clean_name))

        elif target_polarity == "P":
            for p_pat, n_pat in self.swap_rules:
                if n_pat.endswith("$"):
                    clean_n = n_pat[:-1]
                    clean_p = p_pat[:-1] if p_pat.endswith("$") else p_pat
                    if clean_name.endswith(clean_n):
                        candidates.append(clean_name[:-len(clean_n)] + clean_p)
                elif n_pat in clean_name:
                    candidates.append(clean_name.replace(n_pat, p_pat, 1))

            # 特殊協議補全：USB DM -> DP
            if re.search(r"(?i)_DM$", clean_name):
                candidates.append(re.sub(r"(?i)_DM$", "_DP", clean_name))
            if re.search(r"(?i)DM$", clean_name):
                candidates.append(re.sub(r"(?i)DM$", "DP", clean_name))
            if re.search(r"(?i)TXN(\d*)$", clean_name):
                candidates.append(re.sub(r"(?i)TXN(\d*)$", r"TXP\1", clean_name))
            if re.search(r"(?i)RXN(\d*)$", clean_name):
                candidates.append(re.sub(r"(?i)RXN(\d*)$", r"RXP\1", clean_name))
            if re.search(r"(?i)N$", clean_name) and not re.search(r"(?i)(?:CONN|PIN|MAIN)$", clean_name):
                candidates.append(re.sub(r"(?i)N$", "P", clean_name))

        return list(dict.fromkeys(candidates))

    def resolve_partner_name(
        self,
        net_name: str,
        target_polarity: Optional[str] = None
    ) -> Optional[str]:
        """
        推導互補夥伴網路名稱 (支援雙向互推: P -> N 與 N -> P)

        Args:
            net_name: 當前網路名稱 (例如 "SATA0_SATA_TXP")
            target_polarity: 目標夥伴之極性 ("N" 代表尋找負極夥伴, "P" 代表尋找正極夥伴)；
                             若為 None，則由自身極性自動反轉。

        Returns:
            Optional[str]: 互補夥伴網路名稱，若無法推導則回傳 None
        """
        cands = self.resolve_partner_candidates(net_name, target_polarity)
        return cands[0] if cands else None

    @classmethod
    def from_yaml_derivation(cls, pair_derivation: Dict[str, Any]) -> "DifferentialPairResolver":
        """
        由 YAML 中的 pair_derivation 字典建構專屬推導器

        Args:
            pair_derivation: YAML 中定義的 pair_derivation 字典

        Returns:
            DifferentialPairResolver: 初始化後的推導器實例
        """
        swap_rules = []
        raw_rules = pair_derivation.get("partner_swap_rules", [])
        for r in raw_rules:
            if isinstance(r, (list, tuple)) and len(r) == 2:
                swap_rules.append((str(r[0]), str(r[1])))

        pos_pat = pair_derivation.get("positive_pattern")
        neg_pat = pair_derivation.get("negative_pattern")

        return cls(
            swap_rules=swap_rules if swap_rules else None,
            positive_pattern=pos_pat,
            negative_pattern=neg_pat
        )


# ==============================================================================
# 全域預設單例與快捷函式 (Default Singleton & Convenience Functions)
# ==============================================================================
_default_resolver = DifferentialPairResolver()


def determine_diff_polarity(net_name: str) -> Optional[str]:
    """
    判定網路名稱差分極性之標準全域函式

    @param {str} net_name - 網路名稱 (例如 "SATA0_SATA_TXP", "USB20_D-")
    @returns {Optional[str]} "P" (正極), "N" (負極), 或 None
    """
    return _default_resolver.determine_polarity(net_name)


def resolve_diff_pair_partner(
    net_name: str,
    target_polarity: Optional[str] = None
) -> Optional[str]:
    """
    推導互補差分夥伴名稱之標準全域函式

    @param {str} net_name - 網路名稱 (例如 "SATA0_SATA_TXP", "TCP0_RX1_N")
    @param {Optional[str]} target_polarity - 目標極性 ("N" 或 "P")，若省略則由自身極性自動反轉
    @returns {Optional[str]} 互補夥伴網路名稱，無法解析時回傳 None
    """
    return _default_resolver.resolve_partner_name(net_name, target_polarity)


def resolve_diff_pair_candidates(
    net_name: str,
    target_polarity: Optional[str] = None
) -> List[str]:
    """
    推導互補差分夥伴名稱所有候選之標準全域函式

    @param {str} net_name - 網路名稱 (例如 "USB_DP")
    @param {Optional[str]} target_polarity - 目標極性 ("N" 或 "P")，若省略則由自身極性自動反轉
    @returns {List[str]} 所有候選網路名稱清單
    """
    return _default_resolver.resolve_partner_candidates(net_name, target_polarity)
