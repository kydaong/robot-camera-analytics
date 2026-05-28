"""
Ingest inspection tasks from dbo.v_inspection_tasks into Qdrant for RAG.

Usage:
    python scripts/ingest_inspection_tasks.py

Reads all rows from v_inspection_tasks, formats them as searchable prose
(including parsed inspection_data form fields), and upserts into the
QDRANT_COLLECTION_INSPECTION_TASKS collection.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.database import SessionLocal
from app.core.vector_store import ensure_collections
from app.models.db_models import InspectionTask
from app.services.vector_service import upsert_document


def _parse_inspection_data(raw: str | None) -> str:
    """Convert inspection_data JSON array into a readable key: value string."""
    if not raw:
        return "None"
    try:
        fields = json.loads(raw)
        return ", ".join(
            f"{f.get('field', '')}: {f.get('value', '')}"
            for f in fields
            if f.get("field")
        )
    except (json.JSONDecodeError, TypeError):
        return raw[:300] if raw else "None"


def format_inspection_task(t: InspectionTask) -> str:
    findings = _parse_inspection_data(t.inspection_data)
    return (
        f"Inspection task {t.task_no} (Work order {t.workorder_no}): {t.TaskTypeName or 'N/A'}. "
        f"Asset: {t.asset_id or 'N/A'}, Robot: {t.robot_id or 'N/A'}. "
        f"Category: {t.category or 'N/A'}, Frequency: {t.frequency or 'N/A'}. "
        f"Scheduled: {t.schedule_date or 'N/A'} {t.scheduled_time or ''}. "
        f"Status: {t.status or 'N/A'}. Performed by: {t.created_by or 'N/A'}. "
        f"Inspection findings: {findings}. "
        f"Source: {t.source or 'N/A'}. "
        f"Notes: {t.Notes or 'None'}."
    )


def main():
    ensure_collections()
    db = SessionLocal()
    try:
        tasks = db.query(InspectionTask).all()
        print(f"Found {len(tasks)} inspection tasks")

        for t in tasks:
            text = format_inspection_task(t)
            upsert_document(
                collection=settings.QDRANT_COLLECTION_INSPECTION_TASKS,
                text=text,
                metadata={
                    "workorder_no": t.workorder_no,
                    "task_no": t.task_no,
                    "asset_id": t.asset_id,
                    "robot_id": t.robot_id,
                    "status": t.status,
                    "created_by": t.created_by,
                    "schedule_date": t.schedule_date,
                    "category": t.category,
                    "source": t.source,
                },
                doc_id=str(t.Id),
            )
            print(f"  Ingested task {t.task_no} ({t.workorder_no})")

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
