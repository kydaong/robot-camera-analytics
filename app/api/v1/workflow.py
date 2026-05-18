"""
Mode 2 – Human-in-the-loop workflow endpoints.
Operators review, approve or reject proposed actions; Spot checks what's been done.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import ApprovalRequest, WorkflowItem, WorkflowSummary
from app.services.workflow_service import (
    get_workflow_summary,
    mark_completed,
    process_approval,
)

router = APIRouter(prefix="/workflow", tags=["Workflow – Human Approval"])


@router.get("/{run_id}", response_model=WorkflowSummary)
def get_workflow(run_id: str, db: Session = Depends(get_db)):
    """
    Get the full workflow summary for an inspection run.
    Shows what actions are pending, approved, in-progress, or completed.
    Used by both operators and Spot to know what has been actioned.
    """
    summary = get_workflow_summary(db, run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Inspection run not found")
    return summary


@router.post("/approve", response_model=WorkflowItem)
def approve_action(approval: ApprovalRequest, db: Session = Depends(get_db)):
    """
    Operator approves or rejects a proposed action.
    Approved items can then be actioned by maintenance crew.
    """
    item = process_approval(db, approval)
    if not item:
        raise HTTPException(status_code=404, detail="Workflow item not found")
    return item


@router.post("/{workflow_item_id}/complete", response_model=WorkflowItem)
def complete_action(workflow_item_id: str, db: Session = Depends(get_db)):
    """
    Mark an approved workflow item as completed once the work is done.
    This keeps the audit trail of what the robot triggered and humans performed.
    """
    item = mark_completed(db, workflow_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Workflow item not found")
    return item
