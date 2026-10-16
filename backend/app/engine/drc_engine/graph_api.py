"""
Level 3 DRC GraphAPI 輔助類別 (GraphAPI SDK Adapter & Unified Export)

全系統統一採用 designshield.sdk.GraphAPI 為唯一真相來源，
本模組提供別名與適配，確保相容舊版存取 (如 self.G)。
"""

from typing import Dict, List, Any, Optional
import networkx as nx
from designshield.sdk.graph_api import GraphAPI as SdkGraphAPI


class GraphAPI(SdkGraphAPI):
    """
    Level 3 DRC 圖譜查詢介面 (繼承自核心 designshield.sdk.GraphAPI)
    """

    def __init__(self, G: nx.Graph):
        super().__init__(G)
        self.G = G

    @property
    def graph(self) -> nx.Graph:
        """取得底層 NetworkX 圖譜物件"""
        return self._G
