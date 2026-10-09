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

    def query(self, pn: str, interface: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        查詢特定晶片之硬體特規資料

        Args:
            pn: 晶片完整或部分型號 (例如 "STM32F405", "SHT40")
            interface: 可選的介面名稱 (例如 "I2C", "USB")

        Returns:
            Optional[Dict[str, Any]]: 規格字典 (若指定 interface 則回傳該介面字典並含 _meta)，若未查得則回傳 None
        """
        if not pn:
            return None

        # 優先嘗試透過 PatternService 快取查表
        try:
            from backend.app.services.pattern_service import PatternService
            svc = PatternService.get_instance()
            res = svc.query_partdb(pn, interface)
            if res is not None:
                return res
        except Exception:
            pass

        # 若無 PatternService 快取，退回直接讀取 YAML
        clean_pn = pn.strip().upper()
        if not os.path.exists(self._data_dir):
            return None

        for fname in os.listdir(self._data_dir):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                base_name = os.path.splitext(fname)[0].upper()
                if base_name in clean_pn or clean_pn in base_name:
                    filepath = os.path.join(self._data_dir, fname)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        if not data:
                            continue
                        if interface:
                            interfaces = data.get("interfaces", {})
                            return interfaces.get(interface)
                        return data
                    except Exception:
                        continue
        return None
