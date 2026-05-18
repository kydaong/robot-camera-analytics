"""
Workflow management — persists and tracks human-approval items for inspection actions.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.db_models import InspectionRun, WorkflowItem as DBWorkflowItem
from app.models.schemas import (
    ApprovalRequest, InspectionInsight, WorkflowItem, WorkflowStatus, WorkflowSummary,
)


def persist_inspection(db: Session, insight: InspectionInsight) -> None:
    """Save the inspection run and create pending workflow items for each action."""
    run = InspectionRun(
        run_id=insight.run_id,
        robot_id=insight.robot_id,
        site_name=insight.location.site_name,
        zone=insight.location.zone,
        asset_id=insight.location.asset_id,
        captured_at=insight.captured_at,
        overall_severity=insight.overall_severity.value,
        summary=insight.summary,
        insight_payload=insight.model_dump(mode="json"),
    )
    db.add(run)

    for action in insight.proposed_actions:
        item = DBWorkflowItem(
            run_id=insight.run_id,
            action_payload=action.model_dump(mode="json"),
            status=WorkflowStatus.pending_review.value,
        )
        db.add(item)

    db.commit()


def get_workflow_summary(db: Session, run_id: str) -> WorkflowSummary | None:
    run = db.query(InspectionRun).filter(InspectionRun.run_id == run_id).first()
    if not run:
        return None

    items_db = db.query(DBWorkflowItem).filter(DBWorkflowItem.run_id == run_id).all()
    items = [_to_schema(i) for i in items_db]

    status_counts = {s: 0 for s in WorkflowStatus}
    for item in items:
        status_counts[item.status] += 1

    from app.models.schemas import InspectionLocation
    location = InspectionLocation(
        site_name=run.site_name or "",
        zone=run.zone or "",
        asset_id=run.asset_id,
    )
    return WorkflowSummary(
        run_id=run_id,
        robot_id=run.robot_id,
        location=location,
        total_actions=len(items),
        completed=status_counts[WorkflowStatus.completed],
        in_progress=status_counts[WorkflowStatus.in_progress],
        pending_review=status_counts[WorkflowStatus.pending_review],
        rejected=status_counts[WorkflowStatus.rejected],
        items=items,
    )


def process_approval(db: Session, approval: ApprovalRequest) -> WorkflowItem | None:
    item_db = db.query(DBWorkflowItem).filter(
        DBWorkflowItem.workflow_item_id == approval.workflow_item_id
    ).first()
    if not item_db:
        return None

    new_status = WorkflowStatus.approved if approval.approved else WorkflowStatus.rejected
    item_db.status = new_status.value
    item_db.reviewed_at = datetime.utcnow()
    item_db.reviewer_id = approval.reviewer_id
    item_db.reviewer_notes = approval.reviewer_notes
    db.commit()
    db.refresh(item_db)
    return _to_schema(item_db)


def mark_completed(db: Session, workflow_item_id: str) -> WorkflowItem | None:
    item_db = db.query(DBWorkflowItem).filter(
        DBWorkflowItem.workflow_item_id == workflow_item_id
    ).first()
    if not item_db:
        return None
    item_db.status = WorkflowStatus.completed.value
    item_db.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(item_db)
    return _to_schema(item_db)


def _to_schema(item_db: DBWorkflowItem) -> WorkflowItem:
    from app.models.schemas import ProposedAction
    return WorkflowItem(
        workflow_item_id=item_db.workflow_item_id,
        run_id=item_db.run_id,
        action=ProposedAction(**item_db.action_payload),
        status=WorkflowStatus(item_db.status),
        created_at=item_db.created_at,
        reviewed_at=item_db.reviewed_at,
        reviewer_id=item_db.reviewer_id,
        reviewer_notes=item_db.reviewer_notes,
        completed_at=item_db.completed_at,
    )
