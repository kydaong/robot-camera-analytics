"""
Ingest historical inspection incidents from the CMMS into Qdrant for RAG.

Usage:
    python scripts/ingest_incidents.py

Reads completed work orders from Azure SQL, formats them as incident summaries,
and upserts into the QDRANT_COLLECTION_INCIDENTS collection.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.database import SessionLocal
from app.core.vector_store import ensure_collections
from app.models.db_models import WorkOrder
from app.services.vector_service import upsert_document


def format_incident(wo: WorkOrder) -> str:
    return (
        f"Work order {wo.work_order_number}: {wo.title}. "
        f"Asset: {wo.asset_id} at {wo.site}/{wo.zone}. "
        f"Status: {wo.status}. Priority: {wo.priority}. "
        f"Failure code: {wo.failure_code or 'N/A'}. "
        f"Notes: {wo.notes or 'None'}. "
        f"Cost: SGD {wo.cost or 0:.2f}. "
        f"Duration: {wo.actual_hours or 0:.1f} hours."
    )


def main():
    ensure_collections()
    db = SessionLocal()
    try:
        completed = db.query(WorkOrder).filter(WorkOrder.status == "completed").all()
        print(f"Found {len(completed)} completed work orders")

        for wo in completed:
            text = format_incident(wo)
            upsert_document(
                collection=settings.QDRANT_COLLECTION_INCIDENTS,
                text=text,
                metadata={
                    "work_order_number": wo.work_order_number,
                    "asset_id": wo.asset_id,
                    "site": wo.site,
                    "zone": wo.zone,
                    "failure_code": wo.failure_code,
                    "cost": wo.cost,
                },
                doc_id=str(wo.id),
            )
            print(f"  Ingested WO {wo.work_order_number}")

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
