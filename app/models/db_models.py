"""
SQLAlchemy ORM models for Azure SQL tables.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ViewBase(DeclarativeBase):
    """Separate base for read-only view mappings — excluded from create_all."""
    pass


class WorkOrder(Base):
    __tablename__ = "spot_work_orders"

    id = Column(Integer, primary_key=True, index=True)
    work_order_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    asset_id = Column(String(100), index=True)
    site = Column(String(100))
    zone = Column(String(100))
    priority = Column(String(20))         # low / medium / high / critical
    status = Column(String(50))           # open / in_progress / completed / cancelled
    assigned_to = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    failure_code = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)


class Asset(Base):
    __tablename__ = "spot_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(100))
    site = Column(String(100))
    zone = Column(String(100))
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    install_date = Column(DateTime, nullable=True)
    last_maintenance = Column(DateTime, nullable=True)
    next_maintenance = Column(DateTime, nullable=True)
    criticality = Column(String(20))      # low / medium / high / critical
    is_active = Column(Boolean, default=True)


class InspectionRun(Base):
    __tablename__ = "spot_inspection_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid4()))
    robot_id = Column(String(50), nullable=False)
    site_name = Column(String(100))
    zone = Column(String(100))
    asset_id = Column(String(100), nullable=True)
    captured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    overall_severity = Column(String(20))
    summary = Column(Text, nullable=True)
    insight_payload = Column(JSON, nullable=True)  # full InspectionInsight JSON

    workflow_items = relationship("WorkflowItem", back_populates="inspection_run")


class WorkflowItem(Base):
    __tablename__ = "spot_workflow_items"

    id = Column(Integer, primary_key=True, index=True)
    workflow_item_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid4()))
    run_id = Column(String(36), ForeignKey("spot_inspection_runs.run_id"), nullable=False)
    action_payload = Column(JSON, nullable=False)  # ProposedAction JSON
    status = Column(String(30), default="pending_review")
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_id = Column(String(100), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    inspection_run = relationship("InspectionRun", back_populates="workflow_items")


class InspectionTask(ViewBase):
    """Read-only ORM mapping for dbo.v_inspection_tasks (SQL view)."""
    __tablename__ = "v_inspection_tasks"
    __table_args__ = {"schema": "dbo"}

    Id = Column(Integer, primary_key=True)
    task_no = Column(String(100))
    workorder_no = Column(String(50), index=True)
    category = Column(String(100))
    frequency = Column(String(100))
    TaskType = Column(Integer)
    TaskTypeName = Column(String(100))
    permit_no = Column(Integer)
    robot_id = Column(String(50))
    asset_id = Column(String(100))
    schedule_date = Column(String(50))
    scheduled_time = Column(String(50))
    cancel_flag = Column(Boolean)
    created_time = Column(DateTime)
    status = Column(String(50))
    inspection_data = Column(Text)
    inspection_report = Column(Text)
    created_by = Column(String(100))
    imageId = Column(String(100))
    Notes = Column(Text)
    source = Column(String(255))
