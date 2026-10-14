from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class AssignData(BaseModel):
    category: str
    sub_category: str
    component_role: Optional[str] = "None"
    functional_role: Optional[str] = "None"
    is_electrical: bool
    confidence: float

    def __init__(self, **data):
        super().__init__(**data)
        # 雙向同步 component_role 與 functional_role
        if self.component_role == "None" and self.functional_role != "None":
            self.component_role = self.functional_role
        elif self.functional_role == "None" and self.component_role != "None":
            self.functional_role = self.component_role

class MatchCondition(BaseModel):
    match_any: Optional[List[Union['MatchCondition', Dict[str, Any]]]] = None
    match_all: Optional[List[Union['MatchCondition', Dict[str, Any]]]] = None
    
    ref_prefix: Optional[str] = None
    ref_prefix_regex: Optional[str] = None
    description_prefix: Optional[str] = None
    description_regex: Optional[str] = None
    value_regex: Optional[str] = None
    package_regex: Optional[str] = None
    any_text_regex: Optional[str] = None
    
    pin_count_min: Optional[int] = None
    pin_count_max: Optional[int] = None

MatchCondition.update_forward_refs()

class ComponentRule(BaseModel):
    name: str
    description: Optional[str] = ""
    priority: int
    matches: MatchCondition
    assigns: AssignData
    type: Optional[str] = "pattern_match"
    script_path: Optional[str] = None
    enabled: bool = True

# --- Level 2: Topology Engine Models ---

class SignalMatchCondition(BaseModel):
    match_any: Optional[List['SignalMatchBlock']] = None
    match_all: Optional[List['SignalMatchCondition']] = None

    net_name_regex: Optional[str] = None
    pin_name_regex: Optional[str] = None
    symbol_name_regex: Optional[str] = None
    is_power_symbol_connected: Optional[bool] = None
    is_ground_symbol_connected: Optional[bool] = None

class SignalMatchBlock(BaseModel):
    match_all: List['SignalMatchCondition']
    confidence_contribution: float = 0.0

class SignalPattern(BaseModel):
    role: str
    required: bool = False
    group_key: bool = False
    matches: SignalMatchCondition

class ComponentRoleOverride(BaseModel):
    original_sub_category: str
    connected_to: str
    new_role: str

class RoleOverride(ComponentRoleOverride):
    """向後相容別名"""
    pass

class PairDerivation(BaseModel):
    positive_pattern: str
    negative_pattern: str
    partner_swap_rules: List[List[str]] = []

class ExtraField(BaseModel):
    type: str
    source: str
    value: Optional[Any] = None
    infer_strategy: Optional[str] = None

class TopologyRule(BaseModel):
    name: str
    category: str
    priority: int
    signals: List[SignalPattern]
    component_role_overrides: Optional[List[ComponentRoleOverride]] = []
    role_overrides: Optional[List[ComponentRoleOverride]] = []  # 向後相容支援
    pair_derivation: Optional[PairDerivation] = None
    extra_fields: Optional[Dict[str, ExtraField]] = {}
    type: Optional[str] = "topology_match"
    script_path: Optional[str] = None
    enabled: bool = True

SignalMatchCondition.update_forward_refs()
SignalMatchBlock.update_forward_refs()
