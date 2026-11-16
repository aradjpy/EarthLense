"""NASA POWER monthly API with per-request disk caching."""

import json
import os
from pathlib import Path

import requests

BASE_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"

VARIABLES = {
    "T2M": {"id": "T2M", "name": "2 m air temperature", "unit": "°C", "source": "NASA POWER / MERRA-2", "available": True},
    "RH2M": {"id": "RH2M", "name": "2 m relative humidity", "unit": "%", "source": "NASA POWER / MERRA-2", "available": True},
    "WS2M": {"id": "WS2M", "name": "2 m wind speed", "unit": "m/s", "source": "NASA POWER / MERRA-2", "available": True},
    "CLOUD_AMT": {"id": "CLOUD_AMT", "name": "Cloud cover", "unit": "%", "source": "NASA POWER / CERES SYN1deg", "available": True},
    "AOD_55": {"id": "AOD_55", "name": "Aerosol optical depth", "unit": "unitless", "source": "NASA POWER / CERES SYN1deg", "available": True},
}


class NASADataError(Exception):
    pass


def fetch_monthly_variable(latitude: float, longitude: float, start_year: int,
                           end_year: int, variable: str) -> tuple[dict, str]:
    """Return (POWER JSON, 'live' or 'cache'); allow only known parameter IDs."""
    if variable not in VARIABLES:
        raise NASADataError(f"Unsupported NASA parameter: {variable}")

    # Hosted systems may have ephemeral/read-only storage; caching is best-effort.
    cache_enabled = True
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache_enabled = False
    key = f"{variable.lower()}_{latitude:.4f}_{longitude:.4f}_{start_year}_{end_year}.json"
    cache_file = CACHE_DIR / key
    params = {
        "parameters": variable,
        "community": "SB",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_year,
        "end": end_year,
        "format": "JSON",
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=float(os.getenv("NASA_POWER_TIMEOUT", "25")))
        response.raise_for_status()
        payload = response.json()
        if variable not in payload["properties"]["parameter"]:
            raise NASADataError(f"NASA response did not contain {variable}")
        if cache_enabled:
            try:
                cache_file.write_text(json.dumps(payload), encoding="utf-8")
            except OSError:
                pass
        return payload, "live"
    except (requests.RequestException, ValueError, KeyError, TypeError, NASADataError) as error:
        if cache_enabled and cache_file.is_file():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8")), "cache"
            except (OSError, ValueError):
                pass
        raise NASADataError(f"NASA POWER unavailable or invalid response: {error}") from error


def fetch_monthly_temperature(latitude: float, longitude: float,
                              start_year: int, end_year: int) -> tuple[dict, str]:
    """Backwards-compatible wrapper for the original temperature-only backend."""
    return fetch_monthly_variable(latitude, longitude, start_year, end_year, "T2M")
