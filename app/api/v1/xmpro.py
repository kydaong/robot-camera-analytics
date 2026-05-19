"""
XMPro Data Stream integration endpoints.

Full patrol lifecycle:
  1. POST /xmpro/patrol          — XMPro sends work order + Spot images → AI analysis
  2. GET  /xmpro/patrol/{run_id} — Full patrol report + workflow status (Spot audit trail)
  3. GET  /xmpro/approvals/pending — Poll for items awaiting human sign-off
  4. POST /xmpro/approvals/{id}/approve — Operator approves or rejects an action
  5. POST /xmpro/workflow/{id}/complete — Crew marks action as done
  6. GET  /xmpro/history          — Full patrol history across all runs
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import InspectionRun, WorkflowItem as DBWorkflowItem
from app.models.schemas import (
    InspectionInsight, InspectionLocation, InspectionRequest,
    WorkflowItem, WorkflowStatus, ApprovalRequest,
)
from app.services.insight_service import generate_insight
from app.services.vision_service import analyze_image
from app.services.workflow_service import (
    persist_inspection, get_workflow_summary,
    process_approval, mark_completed,
)

router = APIRouter(prefix="/xmpro", tags=["XMPro – Patrol Workflow"])


# ── Request / Response schemas ─────────────────────────────────────────────────

class PatrolRequest(BaseModel):
    """
    Sent by XMPro Data Stream (REST API Agent) when a patrol work order fires.
    No images in the payload — the API auto-loads sample images from
    data/sample_images/{asset_id}/ on the server.
    XMPro only needs to send work order metadata.
    """
    work_order_number: str = Field(..., description="CMMS work order that triggered this patrol")
    site_name: str
    zone: str
    asset_id: Optional[str] = None
    robot_id: str = "spot-001"
    patrol_type: str = "routine"          # routine | triggered | emergency
    notes: Optional[str] = None


class PatrolResult(BaseModel):
    """Returned immediately to XMPro after patrol submission."""
    run_id: str
    work_order_number: str
    has_findings: bool
    overall_severity: Optional[str]       # None when no findings
    observation_count: int
    action_count: int                     # workflow items pending human approval
    summary: str
    insight: Optional[InspectionInsight]  # full detail when findings exist
    message: str                          # human-readable status for XMPro App Designer


class PendingApprovalItem(BaseModel):
    """One action awaiting operator sign-off — shown in XMPro App Designer."""
    workflow_item_id: str
    run_id: str
    work_order_number: Optional[str]
    site_name: str
    zone: str
    asset_id: Optional[str]
    severity: str
    action_description: str
    priority: int
    requires_shutdown: bool
    reference_standard: Optional[str]
    created_at: datetime


class ApproveRequest(BaseModel):
    approved: bool
    reviewer_id: str
    reviewer_notes: Optional[str] = None


class PatrolHistoryItem(BaseModel):
    run_id: str
    work_order_number: Optional[str]
    robot_id: str
    site_name: str
    zone: str
    captured_at: datetime
    overall_severity: Optional[str]
    has_findings: bool
    total_actions: int
    completed_actions: int
    pending_actions: int
    summary: Optional[str]


# ── 1. Submit patrol ───────────────────────────────────────────────────────────

SAMPLE_IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "sample_images"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _load_sample_images(asset_id: Optional[str]) -> list[Path]:
    """
    Load pre-staged sample images for this asset.
    Falls back to 'default' folder if no asset-specific images exist.
    """
    if asset_id:
        asset_dir = SAMPLE_IMAGES_DIR / asset_id
        if asset_dir.exists():
            images = [f for f in asset_dir.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]
            if images:
                return images

    default_dir = SAMPLE_IMAGES_DIR / "default"
    if default_dir.exists():
        return [f for f in default_dir.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    return []


@router.post("/patrol", response_model=PatrolResult)
async def submit_patrol(
    payload: PatrolRequest,
    db: Session = Depends(get_db),
):
    """
    XMPro calls this when a patrol work order fires.
    Only needs work order metadata — images are auto-loaded from
    data/sample_images/{asset_id}/ on the server.
    """
    request = InspectionRequest(
        location=InspectionLocation(
            site_name=payload.site_name,
            zone=payload.zone,
            asset_id=payload.asset_id,
        ),
        robot_id=payload.robot_id,
        notes=f"WO: {payload.work_order_number} | Type: {payload.patrol_type}"
              + (f" | {payload.notes}" if payload.notes else ""),
    )

    # ── Load sample images from disk for this asset ───────────────────────────
    image_files = _load_sample_images(payload.asset_id)
    all_observations = []
    for img_path in image_files:
        obs = analyze_image(img_path, asset_context=payload.asset_id or "")
        all_observations.extend(obs)

    # ── No findings path ──────────────────────────────────────────────────────
    if not all_observations:
        # Still persist the run so the audit trail is complete
        from app.models.db_models import InspectionRun as DBRun
        no_finding_run = DBRun(
            run_id=request.run_id,
            robot_id=payload.robot_id,
            site_name=payload.site_name,
            zone=payload.zone,
            asset_id=payload.asset_id,
            captured_at=request.captured_at,
            overall_severity="none",
            summary="Routine patrol completed. No anomalies detected.",
            insight_payload={"work_order_number": payload.work_order_number},
        )
        db.add(no_finding_run)
        db.commit()

        return PatrolResult(
            run_id=request.run_id,
            work_order_number=payload.work_order_number,
            has_findings=False,
            overall_severity=None,
            observation_count=0,
            action_count=0,
            summary="Routine patrol completed. No anomalies detected.",
            insight=None,
            message="✓ Patrol complete — no anomalies found. No human action required.",
        )

    # ── Findings path ─────────────────────────────────────────────────────────
    insight = generate_insight(request, all_observations)
    persist_inspection(db, insight)          # saves run + creates workflow items

    action_count = len(insight.proposed_actions)
    return PatrolResult(
        run_id=insight.run_id,
        work_order_number=payload.work_order_number,
        has_findings=True,
        overall_severity=insight.overall_severity.value,
        observation_count=len(insight.observations),
        action_count=action_count,
        summary=insight.summary,
        insight=insight,
        message=(
            f"⚠ {len(insight.observations)} observation(s) found — severity: "
            f"{insight.overall_severity.value.upper()}. "
            f"{action_count} action(s) require human approval before proceeding."
        ),
    )


# ── 2. Get patrol status (full audit trail) ────────────────────────────────────

@router.get("/patrol/{run_id}", response_model=dict)
def get_patrol_status(run_id: str, db: Session = Depends(get_db)):
    """
    Full patrol report including what was found, what actions were approved/rejected,
    and what has been completed. Spot and operators both use this for situational awareness.
    """
    run = db.query(InspectionRun).filter(InspectionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Patrol run not found")

    summary = get_workflow_summary(db, run_id)
    items_by_status: dict[str, list] = {s.value: [] for s in WorkflowStatus}

    if summary:
        for item in summary.items:
            items_by_status[item.status.value].append({
                "workflow_item_id": item.workflow_item_id,
                "action": item.action.description,
                "priority": item.action.priority,
                "requires_shutdown": item.action.requires_shutdown,
                "reference_standard": item.action.reference_standard,
                "status": item.status.value,
                "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
                "reviewer_id": item.reviewer_id,
                "reviewer_notes": item.reviewer_notes,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            })

    return {
        "run_id": run_id,
        "robot_id": run.robot_id,
        "site": run.site_name,
        "zone": run.zone,
        "asset_id": run.asset_id,
        "captured_at": run.captured_at.isoformat(),
        "overall_severity": run.overall_severity,
        "has_findings": run.overall_severity not in (None, "none"),
        "summary": run.summary,
        "work_order_number": (run.insight_payload or {}).get("work_order_number"),
        "workflow": {
            "total": sum(len(v) for v in items_by_status.values()),
            "by_status": {k: len(v) for k, v in items_by_status.items()},
            "items": items_by_status,
        },
    }


# ── 3. Poll pending approvals ──────────────────────────────────────────────────

@router.get("/approvals/pending", response_model=list[PendingApprovalItem])
def get_pending_approvals(db: Session = Depends(get_db)):
    """
    XMPro polls this to show operators what actions are waiting for their sign-off.
    Wire into XMPro App Designer as an approval inbox or Recommendation alert.
    """
    pending_db = (
        db.query(DBWorkflowItem)
        .filter(DBWorkflowItem.status == WorkflowStatus.pending_review.value)
        .order_by(DBWorkflowItem.created_at.asc())
        .all()
    )

    results = []
    for item in pending_db:
        run = db.query(InspectionRun).filter(
            InspectionRun.run_id == item.run_id
        ).first()
        action = item.action_payload or {}
        results.append(PendingApprovalItem(
            workflow_item_id=item.workflow_item_id,
            run_id=item.run_id,
            work_order_number=(run.insight_payload or {}).get("work_order_number") if run else None,
            site_name=run.site_name if run else "",
            zone=run.zone if run else "",
            asset_id=run.asset_id if run else None,
            severity=run.overall_severity if run else "unknown",
            action_description=action.get("description", ""),
            priority=action.get("priority", 5),
            requires_shutdown=action.get("requires_shutdown", False),
            reference_standard=action.get("reference_standard"),
            created_at=item.created_at,
        ))
    return results


# ── 4. Approve / reject an action ─────────────────────────────────────────────

@router.post("/approvals/{workflow_item_id}/approve", response_model=WorkflowItem)
def approve_action(
    workflow_item_id: str,
    body: ApproveRequest,
    db: Session = Depends(get_db),
):
    """
    Operator approves or rejects a proposed action.
    Approved items are queued for execution by maintenance crew.
    Rejected items are closed with the reviewer's reason.
    """
    result = process_approval(
        db,
        ApprovalRequest(
            workflow_item_id=workflow_item_id,
            approved=body.approved,
            reviewer_id=body.reviewer_id,
            reviewer_notes=body.reviewer_notes,
        ),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workflow item not found")
    return result


# ── 5. Mark action completed ───────────────────────────────────────────────────

@router.post("/workflow/{workflow_item_id}/complete", response_model=WorkflowItem)
def complete_action(workflow_item_id: str, db: Session = Depends(get_db)):
    """
    Maintenance crew (or Spot) calls this once an approved action is done.
    Updates the audit trail so everyone knows what has been performed.
    """
    result = mark_completed(db, workflow_item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow item not found")
    return result


# ── 6. Patrol history ──────────────────────────────────────────────────────────

@router.get("/history", response_model=list[PatrolHistoryItem])
def patrol_history(
    site_name: Optional[str] = None,
    asset_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Full history of all patrol runs. XMPro can display this as a timeline.
    Filter by site or asset to narrow down.
    """
    query = db.query(InspectionRun).order_by(InspectionRun.captured_at.desc())
    if site_name:
        query = query.filter(InspectionRun.site_name.ilike(f"%{site_name}%"))
    if asset_id:
        query = query.filter(InspectionRun.asset_id == asset_id)
    runs = query.limit(limit).all()

    results = []
    for run in runs:
        items = db.query(DBWorkflowItem).filter(DBWorkflowItem.run_id == run.run_id).all()
        completed = sum(1 for i in items if i.status == WorkflowStatus.completed.value)
        pending = sum(1 for i in items if i.status == WorkflowStatus.pending_review.value)
        results.append(PatrolHistoryItem(
            run_id=run.run_id,
            work_order_number=(run.insight_payload or {}).get("work_order_number"),
            robot_id=run.robot_id,
            site_name=run.site_name or "",
            zone=run.zone or "",
            captured_at=run.captured_at,
            overall_severity=run.overall_severity,
            has_findings=run.overall_severity not in (None, "none"),
            total_actions=len(items),
            completed_actions=completed,
            pending_actions=pending,
            summary=run.summary,
        ))
    return results
