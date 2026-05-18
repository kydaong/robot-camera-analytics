"""
Claude tool definitions for engineering calculations used in CMMS queries.
"""
import math

# ---------------------------------------------------------------------------
# Tool: calculate_mtbf
# ---------------------------------------------------------------------------

TOOL_CALCULATE_MTBF = {
    "name": "calculate_mtbf",
    "description": (
        "Calculate Mean Time Between Failures (MTBF) given total operating hours "
        "and number of failures."
    ),
    "input_schema": {
        "type": "object",
        "required": ["total_operating_hours", "number_of_failures"],
        "properties": {
            "total_operating_hours": {"type": "number"},
            "number_of_failures": {"type": "integer"},
        },
    },
}


def execute_calculate_mtbf(params: dict) -> dict:
    hours = float(params["total_operating_hours"])
    failures = int(params["number_of_failures"])
    if failures == 0:
        return {"error": "Cannot calculate MTBF with zero failures"}
    mtbf = hours / failures
    return {
        "mtbf_hours": round(mtbf, 2),
        "mtbf_days": round(mtbf / 24, 2),
        "interpretation": f"On average, one failure every {mtbf:.1f} hours",
    }


# ---------------------------------------------------------------------------
# Tool: calculate_maintenance_cost_rate
# ---------------------------------------------------------------------------

TOOL_CALCULATE_COST_RATE = {
    "name": "calculate_maintenance_cost_rate",
    "description": "Calculate annualised maintenance cost rate for an asset.",
    "input_schema": {
        "type": "object",
        "required": ["total_cost", "period_days"],
        "properties": {
            "total_cost": {"type": "number", "description": "Total maintenance cost (SGD)"},
            "period_days": {"type": "integer", "description": "Period in days"},
        },
    },
}


def execute_calculate_cost_rate(params: dict) -> dict:
    total = float(params["total_cost"])
    days = int(params["period_days"])
    if days == 0:
        return {"error": "Period cannot be zero"}
    daily = total / days
    annual = daily * 365
    return {
        "daily_cost_sgd": round(daily, 2),
        "monthly_cost_sgd": round(daily * 30, 2),
        "annual_cost_sgd": round(annual, 2),
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_CALC_TOOLS = [TOOL_CALCULATE_MTBF, TOOL_CALCULATE_COST_RATE]

CALC_TOOL_EXECUTORS = {
    "calculate_mtbf": execute_calculate_mtbf,
    "calculate_maintenance_cost_rate": execute_calculate_cost_rate,
}
