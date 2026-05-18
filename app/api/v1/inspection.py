"""
Mode 2 – Spot inspection insight endpoints.
Receives images + metadata from Spot, returns AI-generated insight report.
"""
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.models.schemas import InspectionInsight, InspectionLocation, InspectionRequest
from app.services.insight_service import generate_insight
from app.services.vision_service import analyze_image
from app.services.workflow_service import persist_inspection

router = APIRouter(prefix="/inspection", tags=["Inspection – Spot Insights"])

IMAGE_DIR = Path(settings.IMAGE_UPLOAD_DIR)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


@router.post("/analyze", response_model=InspectionInsight)
async def analyze_inspection(
    site_name: str = Form(...),
    zone: str = Form(...),
    asset_id: str = Form(None),
    robot_id: str = Form("spot-001"),
    notes: str = Form(None),
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Accept one or more images from Spot plus location metadata.
    Returns a structured InspectionInsight with observations, severity,
    proposed actions, and relevant standards.
    The insight is persisted and workflow items created (pending human approval).
    """
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")

    request = InspectionRequest(
        location=InspectionLocation(site_name=site_name, zone=zone, asset_id=asset_id),
        robot_id=robot_id,
        notes=notes,
    )

    saved_paths: list[Path] = []
    run_dir = IMAGE_DIR / request.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    for upload in images:
        content = await upload.read()
        if len(content) > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Image {upload.filename} exceeds {settings.MAX_IMAGE_SIZE_MB} MB limit",
            )
        dest = run_dir / upload.filename
        dest.write_bytes(content)
        saved_paths.append(dest)

    all_observations = []
    for path in saved_paths:
        observations = analyze_image(path, asset_context=asset_id or "")
        all_observations.extend(observations)

    insight = generate_insight(request, all_observations)
    persist_inspection(db, insight)

    return insight
