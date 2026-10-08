"""
Level 3 DRC PartDB SDK 封裝類別
"""

from typing import Dict, Any, Optional
from backend.app.services.pattern_service import PatternService


class PartDB:
    def __init__(self):
        self.svc = PatternService.get_instance()

    def query(self, pn: str, interface: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """查詢特定晶片之硬體特規資料"""
        if not pn:
            return None
        return self.svc.query_partdb(pn, interface)
