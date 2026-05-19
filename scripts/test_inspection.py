"""
Manual test script — simulates a Spot inspection push to the running API.
Place test images in data/sample_images/ then run:

    python scripts/test_inspection.py

The API server must be running on localhost:8000.
"""
import sys
from pathlib import Path
import httpx

API_URL = "http://localhost:8000/api/v1/inspection/analyze"

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample_images"

# Edit these to match your test scenario
PAYLOAD = {
    "site_name": "Choa Chu Kang Waterworks",
    "zone":      "Intake Structure",
    "asset_id":  "PMP-RAW-001",
    "robot_id":  "spot-001",
    "notes":     "Manual test run via test_inspection.py",
}


def main():
    images = [f for f in SAMPLE_DIR.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not images:
        print(f"No images found in {SAMPLE_DIR}")
        print("Drop some .jpg / .png files there and re-run.")
        sys.exit(1)

    print(f"Found {len(images)} image(s): {[f.name for f in images]}")
    print(f"Sending to {API_URL} ...")

    files = [("images", (img.name, open(img, "rb"), "image/jpeg")) for img in images]

    with httpx.Client(timeout=120) as client:
        response = client.post(API_URL, data=PAYLOAD, files=files)

    if response.status_code == 200:
        insight = response.json()
        print("\n── Inspection Insight ──────────────────────────────────")
        print(f"Run ID   : {insight['run_id']}")
        print(f"Severity : {insight['overall_severity'].upper()}")
        print(f"Summary  : {insight['summary']}")
        print(f"\nObservations ({len(insight['observations'])}):")
        for obs in insight["observations"]:
            print(f"  [{obs['severity'].upper()}] {obs['description']} (conf {obs['confidence']:.0%})")
        print(f"\nProposed Actions ({len(insight['proposed_actions'])}):")
        for act in insight["proposed_actions"]:
            shutdown = " ⚠ SHUTDOWN REQUIRED" if act["requires_shutdown"] else ""
            print(f"  P{act['priority']}. {act['description']}{shutdown}")
            if act.get("reference_standard"):
                print(f"      Ref: {act['reference_standard']}")
        print(f"\nApplicable Standards: {', '.join(insight['applicable_standards']) or 'None identified'}")
        print(f"\nWorkflow items created — check: GET /api/v1/workflow/{insight['run_id']}")
    else:
        print(f"Error {response.status_code}: {response.text}")


if __name__ == "__main__":
    main()
