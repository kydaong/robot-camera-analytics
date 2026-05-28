"""
Claude tool definitions for querying the CMMS database.
Each function is registered as a tool the Claude agent can call.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.db_models import WorkOrder, Asset, InspectionTask


# ---------------------------------------------------------------------------
# Tool: get_work_orders
# ---------------------------------------------------------------------------

TOOL_GET_WORK_ORDERS = {
    "name": "get_work_orders",
    "description": (
        "Query the CMMS for work orders. Filter by asset, site, zone, status, "
        "date range, or priority. Returns a list of matching work orders."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "asset_id": {"type": "string", "description": "Filter by asset ID"},
            "site": {"type": "string", "description": "Filter by site name"},
            "zone": {"type": "string", "description": "Filter by zone"},
            "status": {
                "type": "string",
                "enum": ["open", "in_progress", "completed", "cancelled"],
                "description": "Filter by work order status",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
            },
            "from_date": {"type": "string", "description": "ISO date string (inclusive)"},
            "to_date": {"type": "string", "description": "ISO date string (inclusive)"},
            "limit": {"type": "integer", "default": 20},
        },
    },
}


def _inspection_task_to_dict(r: InspectionTask) -> dict:
    return {
        "work_order_number": r.workorder_no,
        "task_no": r.task_no,
        "asset_id": r.asset_id,
        "robot_id": r.robot_id,
        "category": r.category,
        "frequency": r.frequency,
        "task_type_name": r.TaskTypeName,
        "permit_no": r.permit_no,
        "schedule_date": r.schedule_date,
        "scheduled_time": r.scheduled_time,
        "status": r.status,
        "created_by": r.created_by,
        "created_time": r.created_time.isoformat() if r.created_time else None,
        "inspection_data": r.inspection_data,
        "inspection_report": r.inspection_report,
        "image_id": r.imageId,
        "notes": r.Notes,
        "source": r.source,
        "data_source": "v_inspection_tasks",
    }


def execute_get_work_orders(db: Session, params: dict) -> list[dict]:
    filters = []
    if params.get("asset_id"):
        filters.append(WorkOrder.asset_id == params["asset_id"])
    if params.get("site"):
        filters.append(WorkOrder.site.ilike(f"%{params['site']}%"))
    if params.get("zone"):
        filters.append(WorkOrder.zone.ilike(f"%{params['zone']}%"))
    if params.get("status"):
        filters.append(WorkOrder.status == params["status"])
    if params.get("priority"):
        filters.append(WorkOrder.priority == params["priority"])
    if params.get("from_date"):
        filters.append(WorkOrder.created_at >= datetime.fromisoformat(params["from_date"]))
    if params.get("to_date"):
        filters.append(WorkOrder.created_at <= datetime.fromisoformat(params["to_date"]))

    limit = min(int(params.get("limit", 20)), 100)
    rows = (
        db.query(WorkOrder)
        .filter(and_(*filters) if filters else True)
        .order_by(WorkOrder.created_at.desc())
        .limit(limit)
        .all()
    )

    # For any WO numbers also present in v_inspection_tasks, prefer the view's data
    wo_numbers = [r.work_order_number for r in rows]
    view_map: dict[str, InspectionTask] = {}
    if wo_numbers:
        view_rows = (
            db.query(InspectionTask)
            .filter(InspectionTask.workorder_no.in_(wo_numbers))
            .all()
        )
        view_map = {r.workorder_no: r for r in view_rows}

    results = []
    for r in rows:
        if r.work_order_number in view_map:
            results.append(_inspection_task_to_dict(view_map[r.work_order_number]))
        else:
            results.append({
                "work_order_number": r.work_order_number,
                "title": r.title,
                "asset_id": r.asset_id,
                "site": r.site,
                "zone": r.zone,
                "status": r.status,
                "priority": r.priority,
                "assigned_to": r.assigned_to,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "cost": r.cost,
                "failure_code": r.failure_code,
                "data_source": "spot_work_orders",
            })
    return results


# ---------------------------------------------------------------------------
# Tool: get_inspection_tasks
# ---------------------------------------------------------------------------

TOOL_GET_INSPECTION_TASKS = {
    "name": "get_inspection_tasks",
    "description": (
        "Query dbo.v_inspection_tasks for scheduled or completed inspection tasks. "
        "Each row links to a work order via workorder_no and contains the full "
        "inspection_data (form fields/results), robot used, asset, schedule, status, "
        "and who created it. The 'source' field indicates what triggered the task "
        "('AI Agent', 'Job Scheduler', or 'Others'). Always show the source value as-is."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "workorder_no": {"type": "string", "description": "Filter by exact work order number, e.g. WO-2026-001"},
            "asset_id": {"type": "string", "description": "Filter by asset ID (partial match)"},
            "robot_id": {"type": "string", "description": "Filter by robot ID (partial match)"},
            "status": {"type": "string", "description": "Filter by status, e.g. Completed, Pending"},
            "created_by": {"type": "string", "description": "Filter by inspector/creator name (partial match)"},
            "source": {
                "type": "string",
                "description": "Filter by task origin: 'AI Agent', 'Job Scheduler', or 'Others'",
            },
            "limit": {"type": "integer", "default": 20},
        },
    },
}


def execute_get_inspection_tasks(db: Session, params: dict) -> list[dict]:
    filters = []
    if params.get("workorder_no"):
        filters.append(InspectionTask.workorder_no == params["workorder_no"])
    if params.get("asset_id"):
        filters.append(InspectionTask.asset_id.ilike(f"%{params['asset_id']}%"))
    if params.get("robot_id"):
        filters.append(InspectionTask.robot_id.ilike(f"%{params['robot_id']}%"))
    if params.get("status"):
        filters.append(InspectionTask.status.ilike(f"%{params['status']}%"))
    if params.get("created_by"):
        filters.append(InspectionTask.created_by.ilike(f"%{params['created_by']}%"))
    if params.get("source"):
        filters.append(InspectionTask.source.ilike(f"%{params['source']}%"))

    limit = min(int(params.get("limit", 20)), 100)
    rows = (
        db.query(InspectionTask)
        .filter(and_(*filters) if filters else True)
        .order_by(InspectionTask.created_time.desc())
        .limit(limit)
        .all()
    )
    return [_inspection_task_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Tool: get_asset_info
# ---------------------------------------------------------------------------

TOOL_GET_ASSET_INFO = {
    "name": "get_asset_info",
    "description": "Retrieve asset details including maintenance history summary from the CMMS.",
    "input_schema": {
        "type": "object",
        "required": ["asset_id"],
        "properties": {
            "asset_id": {"type": "string", "description": "The asset identifier"},
        },
    },
}


def execute_get_asset_info(db: Session, params: dict) -> dict:
    asset = db.query(Asset).filter(Asset.asset_id == params["asset_id"]).first()
    if not asset:
        return {"error": f"Asset '{params['asset_id']}' not found"}

    wo_count = db.query(func.count(WorkOrder.id)).filter(
        WorkOrder.asset_id == params["asset_id"]
    ).scalar()
    total_cost = db.query(func.sum(WorkOrder.cost)).filter(
        WorkOrder.asset_id == params["asset_id"],
        WorkOrder.cost.isnot(None),
    ).scalar() or 0.0

    return {
        "asset_id": asset.asset_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "site": asset.site,
        "zone": asset.zone,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "install_date": asset.install_date.isoformat() if asset.install_date else None,
        "last_maintenance": asset.last_maintenance.isoformat() if asset.last_maintenance else None,
        "next_maintenance": asset.next_maintenance.isoformat() if asset.next_maintenance else None,
        "criticality": asset.criticality,
        "total_work_orders": wo_count,
        "total_maintenance_cost": round(total_cost, 2),
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_CMMS_TOOLS = [TOOL_GET_WORK_ORDERS, TOOL_GET_INSPECTION_TASKS, TOOL_GET_ASSET_INFO]

CMMS_TOOL_EXECUTORS = {
    "get_work_orders": execute_get_work_orders,
    "get_inspection_tasks": execute_get_inspection_tasks,
    "get_asset_info": execute_get_asset_info,
}
