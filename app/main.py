"""EarthLense: FastAPI JSON backend and same-origin frontend."""

import json
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.nasa_power import NASADataError, VARIABLES, fetch_monthly_variable
from app.preprocessing import DataQualityError, annual_mean, parse_monthly_variable
from app.statistics import TrendError, fit_annual_trend
from app.storytelling import explain_trend

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="EarthLense API", version="1.0.0",
              description="Explore environmental trends using NASA POWER observations and OLS inference.")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class AnalyzeRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_year: int = Field(default=2001, ge=1981)
    end_year: int = Field(default=2024, ge=1981)
    variables: list[str] = Field(default_factory=lambda: ["T2M"], min_length=1)


class CompareRequest(BaseModel):
    location_a: AnalyzeRequest
    location_b: AnalyzeRequest


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/variables")
def variables():
    return list(VARIABLES.values())


@app.get("/api/demo")
def demo():
    """Saved response from a real earlier Toronto NASA POWER run (not live)."""
    file = ROOT / "data" / "demo" / "toronto_2001_2024.json"
    if not file.is_file():
        raise HTTPException(404, "Saved Toronto demo is not available")
    result = json.loads(file.read_text(encoding="utf-8"))
    result["story"] = explain_trend(result["variable"]["id"], result["trend"], result["period"])
    result["data_source"]["retrieval"] = "saved demo"
    result["data_source"]["note"] += "; saved from an earlier NASA POWER analysis"
    return result


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if req.end_year < req.start_year:
        raise HTTPException(422, "End year must be after or equal to start year")
    if req.end_year >= date.today().year:
        raise HTTPException(422, "Please use complete past calendar years")
    if req.end_year - req.start_year + 1 < 10:
        raise HTTPException(422, "At least 10 complete years are required")
    if any(v in {"CLOUD_AMT", "AOD_55"} for v in req.variables) and req.start_year < 2001:
        raise HTTPException(422, "Cloud and aerosol data are available here from 2001 onward")
    if len(req.variables) != 1 or req.variables[0] not in VARIABLES:
        raise HTTPException(422, "Choose one supported environmental variable")

    variable_id = req.variables[0]
    variable = VARIABLES[variable_id]
    try:
        payload, retrieval = fetch_monthly_variable(
            req.latitude, req.longitude, req.start_year, req.end_year, variable_id
        )
        monthly = parse_monthly_variable(payload, variable_id)
        annual = annual_mean(monthly, req.start_year, req.end_year)
        trend = fit_annual_trend(annual["year"].tolist(), annual["value"].tolist())
        if variable_id != "T2M":
            trend.pop("mse_celsius_squared", None)  # Legacy temperature-only key.
    except NASADataError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (DataQualityError, TrendError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return {
        "location": {"latitude": req.latitude, "longitude": req.longitude},
        "period": {"start_year": req.start_year, "end_year": req.end_year},
        "variable": {"id": variable_id, "name": variable["name"], "unit": variable["unit"]},
        "data_source": {
            "provider": "NASA POWER",
            "underlying_product": "CERES SYN1deg" if variable_id in {"CLOUD_AMT", "AOD_55"} else "MERRA-2",
            "temporal_resolution": "monthly", "retrieval": retrieval,
            "note": "Gridded NASA estimates for this area, not a local street sensor",
        },
        "data_quality": {
            "valid_months": len(monthly), "complete_years": len(annual),
            "requested_years": req.end_year - req.start_year + 1,
            "excluded_incomplete_years": req.end_year - req.start_year + 1 - len(annual),
        },
        "observed_monthly_series": [
            {"date": row.date.strftime("%Y-%m"), "value": float(row.value)}
            for row in monthly.itertuples()
        ],
        "observed_annual_series": [
            {"year": int(row.year), "value": float(row.value)}
            for row in annual.itertuples()
        ],
        "trend": trend,
        "story": explain_trend(variable_id, trend, {"start_year": req.start_year, "end_year": req.end_year}),
    }


@app.post("/api/compare")
def compare(req: CompareRequest):
    """Run the SAME variable and dates at two places; no inferential test of the difference."""
    a, b = req.location_a, req.location_b
    if a.variables != b.variables or a.start_year != b.start_year or a.end_year != b.end_year:
        raise HTTPException(422, "Both places must use the same variable and years")
    if abs(a.latitude - b.latitude) < 1e-9 and abs(a.longitude - b.longitude) < 1e-9:
        raise HTTPException(422, "Choose two different places")
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(analyze, a)
        second = pool.submit(analyze, b)
        result_a = first.result()
        result_b = second.result()
    slope_a = result_a["trend"]["slope_per_decade"]
    slope_b = result_b["trend"]["slope_per_decade"]
    return {
        "a": result_a, "b": result_b,
        "slope_difference_a_minus_b_per_decade": slope_a - slope_b,
        "note": "This compares fitted trend estimates only. We have not tested whether the difference between locations is statistically significant.",
    }
