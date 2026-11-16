# EarthLense — See Your World Changing 🌍

Child-friendly Earth science explorer for the NASA Space Apps Challenge. Select a location and timeframe, examine real NASA POWER measurements, and see easy-to-understand long-term trends, charts, and scientific details.

**[Full hosting and custom-domain guide](docs/DEPLOYMENT.md)** — includes cPanel/shared hosting, Render, VPS + Nginx, Docker, DNS, and HTTPS.

## Local run

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 (not `static/index.html` directly).

## Implemented

- **NASA POWER/MERRA-2:** temperature (`T2M`), humidity (`RH2M`), wind speed (`WS2M`), monthly→complete annual day-weighted averages.
- **Live atmosphere explorer:** select clouds (`CLOUD_AMT`) or airborne-particle optical depth (`AOD_55`), and run a NASA POWER/CERES SYN1deg request directly from the atmosphere panel. Both are available from 2001 where NASA POWER has complete measurements.
- **Science:** OLS regression, Pearson's r, R², SSE, MSE, residual standard error, Student t-test, 95% slope confidence interval; NumPy formulas + SciPy t-distribution.
- **Storytelling:** plain-language conclusions for children and expandable technical evidence.
- **Visuals:** hand-built interactive SVG yearly/monthly charts, responsive HTML/CSS/JavaScript frontend, CSV export.
- **Compare two places:** `POST /api/compare`, same environmental variable and years, separate NASA trend analysis for two cities **or user-entered geographic coordinates**, comparable charts and fitted slope comparison. **Not** a significance test of the difference.
- **Saved demo:** verified previous Toronto temperature result is bundled to demonstrate the app if NASA POWER is temporarily unavailable. The UI labels it a saved example.

## Not yet implemented

- Ozone data / NASA TEMPO pipeline — not included; the live atmosphere explorer uses NASA POWER cloud cover and aerosol optical depth.
- Formal statistical test of the *difference* between geographic trends; the app currently reports the two separately fitted slopes.
- Autocorrelation-robust standard errors; classic OLS inferential assumptions are disclosed.

## Files

- `app/main.py` — FastAPI server and routes (`/`, `/health`, `/api/demo`, `/api/variables`, `/api/analyze`, `/api/compare`).
- `app/nasa_power.py` — NASA POWER API client, safe-listed variables, best-effort cache.
- `app/preprocessing.py` — complete-year aggregation and data quality filtering.
- `app/statistics.py` — handwritten regression formulas using NumPy and SciPy t-distribution.
- `app/storytelling.py` — child-friendly interpretation layer.
- `static/` — HTML/CSS/JS and custom SVG graph rendering. **Frontend AI-assistance comments appear in `index.html` and `app.js`.**
- `data/demo/` — original Toronto NASA example data, explicitly *saved*.
- `Dockerfile`, `render.yaml`, `passenger_wsgi.py` — alternative deployment methods.
- `requirements-cpanel.txt` — extra compatibility dependency for Passenger-based cPanel.

## Credits / data sources

- NASA POWER: https://power.larc.nasa.gov/
- POWER monthly point API: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
- Meteorological source: NASA GMAO MERRA-2, https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/
- Cloud and aerosol source: NASA CERES SYN1deg, https://power.larc.nasa.gov/docs/methodology/data/sources_clds_aerosols/
- FastAPI: https://fastapi.tiangolo.com/
- NumPy: https://numpy.org/
- SciPy: https://scipy.org/
- Pandas: https://pandas.pydata.org/
- Requests: https://requests.readthedocs.io/
- Uvicorn: https://www.uvicorn.org/

Frontend design and implementation were developed with AI assistance; comments in the frontend source disclose this. Verify deployment, DNS, and any live scientific conclusions before judging/submission.

## Live atmosphere and comparison UI

The atmosphere card sends a real `POST /api/analyze` request for `CLOUD_AMT` or `AOD_55` and plots the returned observations and fitted line in its own panel. Its data is *not* fabricated. The two-place comparison sends `POST /api/compare` for two different cities or custom coordinates and draws both datasets on a shared y-axis scale. The same year range and environmental variable selected in the main search are used in comparisons.

**Verification limit:** Automated integration tests use synthetic NASA responses; live API network connectivity must be verified on your deployment. AOD is an optical property of the atmosphere, not a direct measure of ground-level air quality.
