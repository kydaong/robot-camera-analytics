"""Tests for the workflow approval endpoints."""
from datetime import datetime

from app.models.db_models import InspectionRun, WorkflowItem as DBWorkflowItem
from app.models.schemas import WorkflowStatus


def _seed_run(db_session):
    run = InspectionRun(
        run_id="test-run-001",
        robot_id="spot-001",
        site_name="Tuas Power",
        zone="Zone A",
        captured_at=datetime.utcnow(),
        overall_severity="medium",
        summary="Test inspection",
        insight_payload={},
    )
    db_session.add(run)
    item = DBWorkflowItem(
        workflow_item_id="item-001",
        run_id="test-run-001",
        action_payload={
            "action_id": "act-001",
            "description": "Lubricate bearing",
            "priority": 2,
            "requires_shutdown": False,
        },
        status=WorkflowStatus.pending_review.value,
    )
    db_session.add(item)
    db_session.commit()


def test_get_workflow(client, db_session):
    _seed_run(db_session)
    r = client.get("/api/v1/workflow/test-run-001")
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == "test-run-001"
    assert data["total_actions"] == 1
    assert data["pending_review"] == 1


def test_approve_action(client, db_session):
    r = client.post("/api/v1/workflow/approve", json={
        "workflow_item_id": "item-001",
        "approved": True,
        "reviewer_id": "engineer-42",
        "reviewer_notes": "Looks good",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_workflow_not_found(client):
    r = client.get("/api/v1/workflow/does-not-exist")
    assert r.status_code == 404
