"""
Pydantic schemas for request/response validation.
Mode 1: Chat / CMMS coworker
Mode 2: Spot inspection insights & workflow
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class SeverityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class WorkflowStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    in_progress = "in_progress"
    completed = "completed"


# ---------------------------------------------------------------------------
# Mode 1 – Chat / CMMS coworker
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query in natural language")
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    history: list[ChatMessage] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    tool_name: str
    input: dict[str, Any]
    output: Any


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Mode 2 – Spot inspection insights
# ---------------------------------------------------------------------------

class InspectionLocation(BaseModel):
    site_name: str
    zone: str
    asset_id: Optional[str] = None
    coordinates: Optional[dict[str, float]] = None  # {"lat": ..., "lng": ...}


class InspectionRequest(BaseModel):
    """Metadata attached when Spot pushes an inspection run."""
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    location: InspectionLocation
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    robot_id: str = Field(default="spot-001")
    notes: Optional[str] = None


class Observation(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid4()))
    image_filename: str
    description: str
    severity: SeverityLevel
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[dict[str, float]] = None


class ProposedAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    priority: int = Field(ge=1, le=5, description="1=highest priority")
    estimated_duration_hours: Optional[float] = None
    requires_shutdown: bool = False
    reference_standard: Optional[str] = None  # e.g. "SS 531:2019 clause 4.3"


class InspectionInsight(BaseModel):
    """Full AI-generated report for one inspection run."""
    run_id: str
    location: InspectionLocation
    captured_at: datetime
    robot_id: str
    observations: list[Observation]
    overall_severity: SeverityLevel
    summary: str
    proposed_actions: list[ProposedAction]
    similar_past_incidents: list[str] = Field(default_factory=list)
    applicable_standards: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Mode 2 – Human-in-the-loop approval workflow
# ---------------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    workflow_item_id: str
    approved: bool
    reviewer_id: str
    reviewer_notes: Optional[str] = None


class WorkflowItem(BaseModel):
    workflow_item_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    action: ProposedAction
    status: WorkflowStatus = WorkflowStatus.pending_review
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    completed_at: Optional[datetime] = None


class WorkflowSummary(BaseModel):
    """What the robot has done so far — pushed to operators."""
    run_id: str
    robot_id: str
    location: InspectionLocation
    total_actions: int
    completed: int
    in_progress: int
    pending_review: int
    rejected: int
    items: list[WorkflowItem]
