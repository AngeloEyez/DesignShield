"""
規則庫管理 API 端點 (Rule Library Endpoints)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.rule import DrcRule
from backend.app.schemas.rule import RuleCreate, RuleResponse

router = APIRouter()


@router.get("", response_model=List[RuleResponse])
def list_rules(
    category: str = None,
    check_type: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db)
) -> List[RuleResponse]:
    """取得所有規則清單"""
    query = db.query(DrcRule)
    if category:
        query = query.filter(DrcRule.category == category)
    if check_type:
        query = query.filter(DrcRule.check_type == check_type)
    if is_active is not None:
        query = query.filter(DrcRule.is_active == is_active)
        
    return query.all()


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db)
) -> RuleResponse:
    """新增規則"""
    existing = db.query(DrcRule).filter(DrcRule.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Rule ID already exists")
        
    rule = DrcRule(
        id=payload.id,
        name=payload.name,
        category=payload.category,
        check_type=payload.check_type,
        is_active=payload.is_active,
        parameters=payload.parameters,
        prompt_template=payload.prompt_template,
        context_extractor=payload.context_extractor
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
