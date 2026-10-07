from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class AssignData(BaseModel):
    category: str
    sub_category: str
    functional_role: str
    is_electrical: bool
    confidence: float

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
