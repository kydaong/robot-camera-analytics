"""
Seed the Azure SQL database with sample assets and work orders for development.

Usage:
    python scripts/seed_db.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, create_tables
from app.models.db_models import Asset, WorkOrder


SITE = "Choa Chu Kang Waterworks"

ASSETS = [
    # ── Pumps ─────────────────────────────────────────────────────────────
    {
        "asset_id": "PMP-RAW-001", "name": "Raw Water Intake Pump 1",
        "asset_type": "Centrifugal Pump", "site": SITE, "zone": "Intake Structure",
        "manufacturer": "Grundfos", "model": "NB 100-200/219",
        "install_date": datetime(2018, 3, 15),
        "last_maintenance": datetime(2024, 10, 5),
        "next_maintenance": datetime(2025, 4, 5),
        "criticality": "critical",
    },
    {
        "asset_id": "PMP-RAW-002", "name": "Raw Water Intake Pump 2",
        "asset_type": "Centrifugal Pump", "site": SITE, "zone": "Intake Structure",
        "manufacturer": "Grundfos", "model": "NB 100-200/219",
        "install_date": datetime(2018, 3, 15),
        "last_maintenance": datetime(2024, 11, 20),
        "next_maintenance": datetime(2025, 5, 20),
        "criticality": "critical",
    },
    {
        "asset_id": "PMP-FILT-001", "name": "Filtered Water Transfer Pump A",
        "asset_type": "Centrifugal Pump", "site": SITE, "zone": "Filtration Building",
        "manufacturer": "KSB", "model": "Etanorm 080-065-160",
        "install_date": datetime(2019, 6, 1),
        "last_maintenance": datetime(2024, 9, 12),
        "next_maintenance": datetime(2025, 3, 12),
        "criticality": "high",
    },
    {
        "asset_id": "PMP-FILT-002", "name": "Filtered Water Transfer Pump B",
        "asset_type": "Centrifugal Pump", "site": SITE, "zone": "Filtration Building",
        "manufacturer": "KSB", "model": "Etanorm 080-065-160",
        "install_date": datetime(2019, 6, 1),
        "last_maintenance": datetime(2024, 12, 3),
        "next_maintenance": datetime(2025, 6, 3),
        "criticality": "high",
    },
    {
        "asset_id": "PMP-CHEM-CL2", "name": "Chlorine Dosing Pump",
        "asset_type": "Metering Pump", "site": SITE, "zone": "Chemical Dosing Room",
        "manufacturer": "ProMinent", "model": "Sigma S2Ba",
        "install_date": datetime(2021, 1, 10),
        "last_maintenance": datetime(2025, 1, 8),
        "next_maintenance": datetime(2025, 7, 8),
        "criticality": "critical",
    },
    {
        "asset_id": "PMP-CHEM-ALUM", "name": "Alum Dosing Pump",
        "asset_type": "Metering Pump", "site": SITE, "zone": "Chemical Dosing Room",
        "manufacturer": "ProMinent", "model": "Sigma S2Ba",
        "install_date": datetime(2021, 1, 10),
        "last_maintenance": datetime(2025, 1, 8),
        "next_maintenance": datetime(2025, 7, 8),
        "criticality": "high",
    },
    {
        "asset_id": "PMP-SLUDGE-001", "name": "Sludge Withdrawal Pump",
        "asset_type": "Submersible Pump", "site": SITE, "zone": "Sedimentation Basin",
        "manufacturer": "Flygt", "model": "N 3127",
        "install_date": datetime(2020, 8, 22),
        "last_maintenance": datetime(2024, 8, 14),
        "next_maintenance": datetime(2025, 2, 14),
        "criticality": "medium",
    },
    {
        "asset_id": "PMP-BACKWASH-001", "name": "Filter Backwash Pump",
        "asset_type": "Centrifugal Pump", "site": SITE, "zone": "Filtration Building",
        "manufacturer": "Sulzer", "model": "ABS XFP 150G",
        "install_date": datetime(2017, 11, 5),
        "last_maintenance": datetime(2024, 7, 30),
        "next_maintenance": datetime(2025, 1, 30),
        "criticality": "high",
    },

    # ── Valves ────────────────────────────────────────────────────────────
    {
        "asset_id": "VLV-GATE-001", "name": "Raw Water Inlet Gate Valve DN400",
        "asset_type": "Gate Valve", "site": SITE, "zone": "Intake Structure",
        "manufacturer": "AVK", "model": "Series 45",
        "install_date": datetime(2018, 3, 15),
        "last_maintenance": datetime(2023, 10, 1),
        "next_maintenance": datetime(2025, 10, 1),
        "criticality": "critical",
    },
    {
        "asset_id": "VLV-BFLY-001", "name": "Treated Water Outlet Butterfly Valve DN600",
        "asset_type": "Butterfly Valve", "site": SITE, "zone": "Clear Water Reservoir",
        "manufacturer": "Crane", "model": "Duo-Chek II",
        "install_date": datetime(2019, 4, 20),
        "last_maintenance": datetime(2024, 4, 20),
        "next_maintenance": datetime(2025, 4, 20),
        "criticality": "high",
    },
    {
        "asset_id": "VLV-CHECK-001", "name": "Pump Discharge Check Valve – PMP-RAW-001",
        "asset_type": "Check Valve", "site": SITE, "zone": "Intake Structure",
        "manufacturer": "Crane", "model": "Duo-Chek II",
        "install_date": datetime(2018, 3, 15),
        "last_maintenance": datetime(2024, 3, 22),
        "next_maintenance": datetime(2025, 3, 22),
        "criticality": "high",
    },
    {
        "asset_id": "VLV-PRV-001", "name": "Pressure Reducing Valve – Distribution Header",
        "asset_type": "Pressure Reducing Valve", "site": SITE, "zone": "Distribution Chamber",
        "manufacturer": "Bermad", "model": "700 Series",
        "install_date": datetime(2020, 2, 14),
        "last_maintenance": datetime(2024, 6, 18),
        "next_maintenance": datetime(2025, 6, 18),
        "criticality": "high",
    },
    {
        "asset_id": "VLV-SOLENOID-CL2", "name": "Chlorine Feed Solenoid Valve",
        "asset_type": "Solenoid Valve", "site": SITE, "zone": "Chemical Dosing Room",
        "manufacturer": "ASCO", "model": "Series 8210",
        "install_date": datetime(2021, 1, 10),
        "last_maintenance": datetime(2025, 1, 8),
        "next_maintenance": datetime(2025, 7, 8),
        "criticality": "critical",
    },
    {
        "asset_id": "VLV-GATE-DRAIN-001", "name": "Sedimentation Basin Drain Valve DN200",
        "asset_type": "Gate Valve", "site": SITE, "zone": "Sedimentation Basin",
        "manufacturer": "AVK", "model": "Series 45",
        "install_date": datetime(2018, 6, 5),
        "last_maintenance": datetime(2023, 6, 5),
        "next_maintenance": datetime(2025, 6, 5),
        "criticality": "medium",
    },

    # ── Pipework ──────────────────────────────────────────────────────────
    {
        "asset_id": "PIPE-RAW-001", "name": "Raw Water Rising Main DN500 – Intake to Mixing",
        "asset_type": "Pipework", "site": SITE, "zone": "Intake to Mixing Basin",
        "manufacturer": "Tata Steel", "model": "Ductile Iron DN500 PN16",
        "install_date": datetime(2018, 3, 15),
        "last_maintenance": datetime(2023, 3, 15),
        "next_maintenance": datetime(2025, 3, 15),
        "criticality": "critical",
    },
    {
        "asset_id": "PIPE-FILT-001", "name": "Filtered Water Header DN300",
        "asset_type": "Pipework", "site": SITE, "zone": "Filtration Building",
        "manufacturer": "Wavin", "model": "PVC-U DN300 PN10",
        "install_date": datetime(2019, 6, 1),
        "last_maintenance": datetime(2024, 6, 1),
        "next_maintenance": datetime(2026, 6, 1),
        "criticality": "high",
    },
    {
        "asset_id": "PIPE-CHEM-CL2", "name": "Chlorine Dosing Line DN25 – HDPE",
        "asset_type": "Pipework", "site": SITE, "zone": "Chemical Dosing Room",
        "manufacturer": "Georg Fischer", "model": "HDPE SDR11 DN25",
        "install_date": datetime(2021, 1, 10),
        "last_maintenance": datetime(2025, 1, 8),
        "next_maintenance": datetime(2026, 1, 8),
        "criticality": "critical",
    },
    {
        "asset_id": "PIPE-SLUDGE-001", "name": "Sludge Return Line DN150",
        "asset_type": "Pipework", "site": SITE, "zone": "Sedimentation Basin",
        "manufacturer": "Tata Steel", "model": "Ductile Iron DN150 PN10",
        "install_date": datetime(2018, 6, 5),
        "last_maintenance": datetime(2023, 12, 10),
        "next_maintenance": datetime(2025, 12, 10),
        "criticality": "medium",
    },
]

WORK_ORDERS = [
    # ── Completed ─────────────────────────────────────────────────────────
    {
        "work_order_number": "WO-2024-001",
        "title": "Impeller erosion – PMP-RAW-001",
        "asset_id": "PMP-RAW-001", "site": SITE, "zone": "Intake Structure",
        "status": "completed", "priority": "high",
        "assigned_to": "Ahmad Fadzillah",
        "failure_code": "EROSION",
        "estimated_hours": 8.0, "actual_hours": 9.5, "cost": 4200.0,
        "created_at": datetime.utcnow() - timedelta(days=90),
        "completed_at": datetime.utcnow() - timedelta(days=86),
        "notes": "Impeller eroded due to high suspended solids. Replaced with hardened alloy impeller.",
    },
    {
        "work_order_number": "WO-2024-002",
        "title": "Gate valve stem corrosion – VLV-GATE-001",
        "asset_id": "VLV-GATE-001", "site": SITE, "zone": "Intake Structure",
        "status": "completed", "priority": "critical",
        "assigned_to": "Lim Chee Wai",
        "failure_code": "CORROSION",
        "estimated_hours": 12.0, "actual_hours": 14.0, "cost": 6800.0,
        "created_at": datetime.utcnow() - timedelta(days=75),
        "completed_at": datetime.utcnow() - timedelta(days=71),
        "notes": "Stem seized due to external corrosion. Full valve assembly replaced. Protective coating applied.",
    },
    {
        "work_order_number": "WO-2024-003",
        "title": "Chlorine dosing pump diaphragm failure – PMP-CHEM-CL2",
        "asset_id": "PMP-CHEM-CL2", "site": SITE, "zone": "Chemical Dosing Room",
        "status": "completed", "priority": "critical",
        "assigned_to": "Tan Boon Kiat",
        "failure_code": "DIAPHRAGM_FAIL",
        "estimated_hours": 4.0, "actual_hours": 3.5, "cost": 1100.0,
        "created_at": datetime.utcnow() - timedelta(days=60),
        "completed_at": datetime.utcnow() - timedelta(days=59),
        "notes": "Diaphragm cracked causing chlorine dosing undershoot. Replaced diaphragm and O-rings with OEM kit.",
    },
    {
        "work_order_number": "WO-2024-004",
        "title": "Leaking flange joint – PIPE-RAW-001 at 45m mark",
        "asset_id": "PIPE-RAW-001", "site": SITE, "zone": "Intake to Mixing Basin",
        "status": "completed", "priority": "high",
        "assigned_to": "Rajendran S.",
        "failure_code": "LEAKAGE",
        "estimated_hours": 6.0, "actual_hours": 7.0, "cost": 980.0,
        "created_at": datetime.utcnow() - timedelta(days=45),
        "completed_at": datetime.utcnow() - timedelta(days=43),
        "notes": "Flange gasket deteriorated. Replaced with EPDM gasket, re-torqued bolts to spec. Hydro-tested at 1.5× PN16.",
    },
    {
        "work_order_number": "WO-2024-005",
        "title": "Backwash pump cavitation – PMP-BACKWASH-001",
        "asset_id": "PMP-BACKWASH-001", "site": SITE, "zone": "Filtration Building",
        "status": "completed", "priority": "high",
        "assigned_to": "Ahmad Fadzillah",
        "failure_code": "CAVITATION",
        "estimated_hours": 5.0, "actual_hours": 6.0, "cost": 2300.0,
        "created_at": datetime.utcnow() - timedelta(days=30),
        "completed_at": datetime.utcnow() - timedelta(days=27),
        "notes": "Cavitation damage on pump casing. Root cause: suction strainer 80% blocked. Cleaned strainer and replaced wear ring.",
    },
    {
        "work_order_number": "WO-2024-006",
        "title": "PRV hunting / pressure instability – VLV-PRV-001",
        "asset_id": "VLV-PRV-001", "site": SITE, "zone": "Distribution Chamber",
        "status": "completed", "priority": "medium",
        "assigned_to": "Lim Chee Wai",
        "failure_code": "INSTABILITY",
        "estimated_hours": 3.0, "actual_hours": 2.5, "cost": 650.0,
        "created_at": datetime.utcnow() - timedelta(days=20),
        "completed_at": datetime.utcnow() - timedelta(days=19),
        "notes": "Pilot valve spring fatigued. Replaced pilot valve assembly. Set pressure re-calibrated to 3.5 bar.",
    },
    {
        "work_order_number": "WO-2024-007",
        "title": "Sludge pump seal leakage – PMP-SLUDGE-001",
        "asset_id": "PMP-SLUDGE-001", "site": SITE, "zone": "Sedimentation Basin",
        "status": "completed", "priority": "medium",
        "assigned_to": "Tan Boon Kiat",
        "failure_code": "SEAL_FAIL",
        "estimated_hours": 4.0, "actual_hours": 4.0, "cost": 760.0,
        "created_at": datetime.utcnow() - timedelta(days=10),
        "completed_at": datetime.utcnow() - timedelta(days=9),
        "notes": "Mechanical seal worn. Replaced seal kit. Pump reinstalled and tested at full load.",
    },

    # ── Open / In Progress ─────────────────────────────────────────────────
    {
        "work_order_number": "WO-2025-001",
        "title": "Abnormal vibration – PMP-FILT-001",
        "asset_id": "PMP-FILT-001", "site": SITE, "zone": "Filtration Building",
        "status": "in_progress", "priority": "high",
        "assigned_to": "Ahmad Fadzillah",
        "failure_code": "VIBRATION",
        "estimated_hours": 6.0, "actual_hours": None, "cost": None,
        "notes": "Vibration readings at 12 mm/s (threshold 7 mm/s). Bearing inspection underway. Possible impeller imbalance.",
    },
    {
        "work_order_number": "WO-2025-002",
        "title": "Routine PM – PMP-RAW-002 quarterly service",
        "asset_id": "PMP-RAW-002", "site": SITE, "zone": "Intake Structure",
        "status": "open", "priority": "medium",
        "assigned_to": None,
        "failure_code": None,
        "estimated_hours": 4.0, "actual_hours": None, "cost": None,
        "notes": "Scheduled quarterly PM. Check impeller clearance, grease bearings, inspect mechanical seal.",
    },
    {
        "work_order_number": "WO-2025-003",
        "title": "External coating degradation – PIPE-RAW-001",
        "asset_id": "PIPE-RAW-001", "site": SITE, "zone": "Intake to Mixing Basin",
        "status": "open", "priority": "medium",
        "assigned_to": None,
        "failure_code": "CORROSION",
        "estimated_hours": 16.0, "actual_hours": None, "cost": None,
        "notes": "Spot inspection by Spot robot detected blistering and delamination of external epoxy coating over 3 m section. Recoating required.",
    },
    {
        "work_order_number": "WO-2025-004",
        "title": "Check valve chatter – VLV-CHECK-001",
        "asset_id": "VLV-CHECK-001", "site": SITE, "zone": "Intake Structure",
        "status": "open", "priority": "high",
        "assigned_to": "Lim Chee Wai",
        "failure_code": "CHATTER",
        "estimated_hours": 5.0, "actual_hours": None, "cost": None,
        "notes": "Audible chatter under low-flow conditions. Likely worn hinge pin. Isolation and inspection scheduled.",
    },
]


def main():
    create_tables()
    db = SessionLocal()
    try:
        for a in ASSETS:
            if not db.query(Asset).filter(Asset.asset_id == a["asset_id"]).first():
                db.add(Asset(**a))

        for wo in WORK_ORDERS:
            if not db.query(WorkOrder).filter(
                WorkOrder.work_order_number == wo["work_order_number"]
            ).first():
                db.add(WorkOrder(**wo))

        db.commit()
        print(f"Seeded {len(ASSETS)} assets and {len(WORK_ORDERS)} work orders.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
