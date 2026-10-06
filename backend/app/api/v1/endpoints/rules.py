"""
規則庫管理 API 端點 (Rule Library Endpoints)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.rule import DrcRule
from backend.app.schemas.rule import RuleCreate, RuleUpdate, RuleResponse

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
        
    return query.order_by(DrcRule.category, DrcRule.id).all()


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(
    rule_id: str,
    db: Session = Depends(get_db)
) -> RuleResponse:
    """取得單一規則詳情"""
    rule = db.query(DrcRule).filter(DrcRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


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


@router.put("/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: str,
    payload: RuleUpdate,
    db: Session = Depends(get_db)
) -> RuleResponse:
    """修改規則"""
    rule = db.query(DrcRule).filter(DrcRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if payload.name is not None:
        rule.name = payload.name
    if payload.category is not None:
        rule.category = payload.category
    if payload.check_type is not None:
        rule.check_type = payload.check_type
    if payload.is_active is not None:
        rule.is_active = payload.is_active
    if payload.parameters is not None:
        rule.parameters = payload.parameters
    if payload.prompt_template is not None:
        rule.prompt_template = payload.prompt_template
    if payload.context_extractor is not None:
        rule.context_extractor = payload.context_extractor

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_200_OK)
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """刪除規則"""
    rule = db.query(DrcRule).filter(DrcRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
    return {"success": True, "message": f"Rule {rule_id} deleted successfully", "id": rule_id}

