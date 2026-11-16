"""Run the pipeline from NASA directly, before starting the API server."""

import json

from app.nasa_power import fetch_monthly_temperature
from app.preprocessing import annual_temperature, parse_monthly_temperature
from app.statistics import fit_annual_trend


if __name__ == "__main__":
    payload, retrieval = fetch_monthly_temperature(43.7, -79.4, 2001, 2024)
    monthly = parse_monthly_temperature(payload)
    annual = annual_temperature(monthly, 2001, 2024)
    trend = fit_annual_trend(annual["year"].tolist(), annual["temperature_c"].tolist())
    print(f"NASA data from {retrieval}: {len(monthly)} valid months, {len(annual)} complete years")
    print(json.dumps({k: v for k, v in trend.items() if k != "fitted_annual_series"}, indent=2))
