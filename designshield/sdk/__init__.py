"""
DesignShield 核心規則引擎 SDK (DesignShield Rule Engine SDK)

提供標準合約與型別物件，供 Level 3 DRC 伴生動態腳本開發與執行期沙盒防護使用。
"""

from designshield.sdk.models import (
    RuleResult,
    RuleViolation,
    RuleContext,
    ComponentNode,
    NetNode,
)
from designshield.sdk.graph_api import GraphAPI
from designshield.sdk.part_db import PartDB
from designshield.sdk.sandbox import (
    ASTSecurityValidator,
    SandboxedScriptRunner,
    SecurityViolationError,
    ScriptTimeoutError,
)

__all__ = [
    "RuleResult",
    "RuleViolation",
    "RuleContext",
    "ComponentNode",
    "NetNode",
    "GraphAPI",
    "PartDB",
    "ASTSecurityValidator",
    "SandboxedScriptRunner",
    "SecurityViolationError",
    "ScriptTimeoutError",
]
