"""
DesignShield SDK PartDB 零件規格庫查詢介面 (PartDB Interface)

提供唯讀查表方法，依據晶片料號 (Part Number, PN) 檢索硬體介面特規 (例如 I2C, USB 等) 及原廠手冊溯源證據。
"""

import os
import yaml
from typing import Dict, Any, Optional


class PartDB:
    """
    PartDB 零件規格庫安全查詢介面

    支援單一 IC 特規查詢，自動載入 patterns/partdb/data/ 之結構化 YAML 數據。
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self._data_dir = data_dir
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self._data_dir = os.path.join(base_dir, "patterns", "partdb", "data")

    def query(
        self,
        pn: str,
        interface: Optional[str] = None,
        mfg: Optional[str] = None,
        supplier: Optional[str] = None,
        vendor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        查詢特定晶片之硬體特規資料 (支援雙層檢索: Mfg + 料號)

        Args:
            pn: 晶片完整或部分型號 (例如 "STM32F405", "SHT40")
            interface: 可選的介面名稱 (例如 "I2C", "USB")
            mfg: 可選的原廠製造商簡稱或代碼 (例如 "TI", "ST", "TDK"，對齊 XML 之 Mfg 屬性)
            supplier: 相容參數 (同 mfg)
            vendor: 舊版相容參數 (同 mfg)

        Returns:
            Optional[Dict[str, Any]]: 規格字典 (若指定 interface 則回傳該介面字典並含 _meta)，若未查得則回傳 None
        """
        if not pn:
            return None

        # 優先嘗試透過 PatternService 快取查表
        try:
            from backend.app.services.pattern_service import PatternService
            svc = PatternService.get_instance()
            res = svc.query_partdb(pn, interface, mfg=mfg, supplier=supplier, vendor=vendor)
            if res is not None:
                return res
        except Exception:
            pass

        # 若無 PatternService 快取，退回直接讀取 YAML
        clean_pn = pn.strip().upper()
        target_mfg = mfg or supplier or vendor
        clean_mfg = target_mfg.strip().upper() if target_mfg else None
        if not os.path.exists(self._data_dir):
            return None

        candidates = []
        for root, _, files in os.walk(self._data_dir):
            for fname in files:
                if fname.startswith("_"):
                    continue
                if fname.endswith(".yaml") or fname.endswith(".yml"):
                    base_name = os.path.splitext(fname)[0].upper()
                    # 檔名格式為 <MFG>_<PN>
                    parts = base_name.split("_", 1)
                    file_pn = parts[1] if len(parts) > 1 else parts[0]
                    if file_pn in clean_pn or clean_pn in file_pn:
                        filepath = os.path.join(root, fname)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                data = yaml.safe_load(f)
                            if data:
                                candidates.append(data)
                        except Exception:
                            continue

        matched = None
        if clean_mfg:
            for c in candidates:
                c_mfg_val = c.get("mfg", "").upper()
                c_sup = c.get("supplier", "").upper()
                c_code = c.get("vendor_code", "").upper()
                c_legacy_mfg = c.get("manufacturer", "").upper()
                if (c_mfg_val == clean_mfg or clean_mfg in c_mfg_val or c_mfg_val in clean_mfg or
                    c_sup == clean_mfg or clean_mfg in c_sup or
                    c_code == clean_mfg or clean_mfg in c_legacy_mfg or c_legacy_mfg in clean_mfg):
                    matched = c
                    break

        if not matched and candidates:
            matched = candidates[0]

        if not matched:
            return None

        if interface:
            return matched.get("interfaces", {}).get(interface)
        return matched
