"""All tests use synthetic observations and NEVER imply real NASA measurements."""

import math
from fastapi.testclient import TestClient

from app import main
from app.preprocessing import annual_temperature, parse_monthly_temperature
from app.statistics import fit_annual_trend


def sample_payload():
    data = {}
    for year in range(2001, 2021):
        for month in range(1, 13):
            # 0.20 C/year + an unchanged repeating seasonal cycle
            data[f"{year}{month:02d}"] = 9.0 + 0.2 * (year - 2001) + 0.04 * month
    data["2020"] = 123.0  # ignore POWER annual-style keys
    return {"properties": {"parameter": {"T2M": data}}}


def test_regression_and_confidence_interval():
    # Perfect straight line; regression has known slope.
    years = list(range(2001, 2021))
    temps = [10.0 + 0.2 * (y - 2001) for y in years]
    trend = fit_annual_trend(years, temps)
    assert math.isclose(trend["slope_per_year"], 0.2, abs_tol=1e-10)
    assert math.isclose(trend["slope_per_decade"], 2.0, abs_tol=1e-10)
    assert trend["statistically_significant_at_0_05"]
    assert trend["slope_95pct_ci_per_decade"][0] <= 2.0 <= trend["slope_95pct_ci_per_decade"][1]
    assert len(trend["fitted_annual_series"]) == 20


def test_preprocessing_excludes_incomplete_year():
    payload = sample_payload()
    payload["properties"]["parameter"]["T2M"]["200507"] = -999
    monthly = parse_monthly_temperature(payload)
    annual = annual_temperature(monthly, 2001, 2020)
    assert len(monthly) == 239
    assert 2005 not in annual["year"].tolist()
    assert len(annual) == 19


def test_api_with_mocked_nasa_response(monkeypatch):
    # Never contact NASA from an automated test.
    monkeypatch.setattr(main, "fetch_monthly_variable",
                        lambda lat, lon, start, end, variable: (sample_payload(), "cache"))
    client = TestClient(main.app)
    assert client.get("/health").json() == {"status": "ok"}
    result = client.post("/api/analyze", json={
        "latitude": 43.7, "longitude": -79.4,
        "start_year": 2001, "end_year": 2020, "variables": ["T2M"]
    })
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["data_quality"]["complete_years"] == 20
    assert abs(body["trend"]["slope_per_decade"] - 2.0) < 0.01
    assert body["data_source"]["retrieval"] == "cache"


def test_non_significant_trend_is_not_called_no_change():
    years = list(range(2001, 2021))
    # Constant long-run level with alternating values and no convincing trend.
    values = [10.0 + (0.2 if i % 2 == 0 else -0.2) for i in range(len(years))]
    trend = fit_annual_trend(years, values)
    assert not trend["statistically_significant_at_0_05"]
    assert trend["slope_95pct_ci_per_decade"][0] < 0 < trend["slope_95pct_ci_per_decade"][1]
    assert trend["interpretation"] == "no statistically significant trend detected"


def test_manual_ols_known_noisy_series():
    years = list(range(2001, 2013))
    values = [3.4, 4.2, 4.5, 3.8, 5.7, 5.4, 6.5, 6.1, 7.2, 7.4, 8.3, 7.9]
    trend = fit_annual_trend(years, values)
    assert trend["mse_celsius_squared"] > 0
    assert 0 < trend["p_value"] < 1
    assert trend["slope_95pct_ci_per_decade"][0] < trend["slope_per_decade"] < trend["slope_95pct_ci_per_decade"][1]
    assert 0 < trend["r_squared"] < 1


def test_frontend_and_saved_demo():
    client = TestClient(main.app)
    page = client.get("/")
    assert page.status_code == 200
    assert "EARTH" in page.text and "analysis-form" in page.text
    assert client.get("/static/app.js").status_code == 200
    demo = client.get("/api/demo")
    assert demo.status_code == 200
    assert demo.json()["data_source"]["retrieval"] == "saved demo"
    assert len(demo.json()["observed_annual_series"]) == 24
    assert len(client.get("/api/variables").json()) >= 3

def test_humidity_pipeline_mock(monkeypatch):
    humidity = sample_payload()["properties"]["parameter"]["T2M"]
    monkeypatch.setattr(main, "fetch_monthly_variable",
                        lambda lat, lon, start, end, variable: ({"properties":{"parameter":{"RH2M":humidity}}}, "cache"))
    client = TestClient(main.app)
    result = client.post("/api/analyze", json={"latitude": 43.7, "longitude":-79.4,
                        "start_year":2001,"end_year":2020,"variables":["RH2M"]})
    assert result.status_code == 200, result.text
    assert result.json()["variable"]["unit"] == "%"
    assert abs(result.json()["trend"]["slope_per_decade"] - 2.0) < 0.01

def test_short_period_rejected():
    client = TestClient(main.app)
    result = client.post("/api/analyze", json={"latitude":43.7,"longitude":-79.4,
                        "start_year":2020,"end_year":2024,"variables":["T2M"]})
    assert result.status_code == 422

# Child-friendly storytelling is generated from the same real statistical result.
def test_demo_includes_understandable_story():
    client = TestClient(main.app)
    data = client.get('/api/demo').json()
    assert data['story']['headline'] == 'The data suggests this area is getting warmer!'
    assert 'every 10 years' in data['story']['description']
    assert 'gridded' in data['story']['data_note']
    assert data['trend']['statistically_significant_at_0_05']


def test_uncertain_trend_not_described_as_no_change():
    from app.storytelling import explain_trend
    trend = {
        'statistically_significant_at_0_05': False,
        'slope_per_decade': -0.3,
        'estimated_change_over_period': -0.75,
    }
    story = explain_trend('RH2M', trend, {'start_year': 2001, 'end_year': 2024})
    assert 'hard to tell' in story['headline']
    assert 'does not mean nothing changed' in story['evidence_description']
    assert 'percentage points' in story['change_explanation']


def test_live_analysis_and_explorer_controls(monkeypatch):
    monkeypatch.setattr(main, 'fetch_monthly_variable',
                        lambda lat, lon, start, end, variable: (sample_payload(), 'cache'))
    client = TestClient(main.app)
    result = client.post('/api/analyze', json={
        'latitude': 43.7, 'longitude': -79.4,
        'start_year': 2001, 'end_year': 2020,
        'variables': ['T2M']
    })
    assert result.status_code == 200, result.text
    body = result.json()
    assert body['story']['evidence_label'] == 'A clear pattern'
    assert body['trend']['slope_per_decade'] > 0
    html = client.get('/').text
    assert 'LIVE NASA ANALYSIS' in html
    assert 'compare-a' in html and 'atmosphere-button' in html
    assert 'compare-a-lat' in html and 'compare-b-lon' in html
    assert 'Coming next' not in html
    assert client.get('/api/compare').status_code == 405


def test_atmospheric_variables_with_mocked_nasa(monkeypatch):
    client = TestClient(main.app)
    for variable in ("CLOUD_AMT", "AOD_55"):
        series = sample_payload()["properties"]["parameter"]["T2M"]
        monkeypatch.setattr(main, "fetch_monthly_variable",
            lambda lat, lon, start, end, var, v=variable, s=series:
                ({"properties":{"parameter":{v:s}}}, "cache"))
        response = client.post("/api/analyze", json={
            "latitude": 43.7, "longitude": -79.4,
            "start_year": 2001, "end_year": 2020, "variables": [variable]})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["data_source"]["underlying_product"] == "CERES SYN1deg"
        assert data["variable"]["id"] == variable
        assert data["trend"]["n_years"] == 20


def test_two_location_comparison_with_mocked_nasa(monkeypatch):
    client = TestClient(main.app)
    def fake_fetch(lat, lon, start, end, var):
        payload = sample_payload()
        for k in payload["properties"]["parameter"]["T2M"]:
            if len(k) == 6:
                payload["properties"]["parameter"]["T2M"][k] *= 1 if lat > 42 else 2
        return payload, "cache"
    monkeypatch.setattr(main, 'fetch_monthly_variable', fake_fetch)
    a = {"latitude": 43.7, "longitude": -79.4, "start_year": 2001, "end_year": 2020, "variables": ["T2M"]}
    b = {**a, "latitude": 40.7, "longitude": -74.0}
    response = client.post('/api/compare', json={"location_a": a, "location_b": b})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['a']['trend']['n_years'] == 20
    assert body['b']['trend']['n_years'] == 20
    assert body['a']['trend']['slope_per_decade'] < body['b']['trend']['slope_per_decade']
    assert 'not tested' in body['note'].lower()
    assert client.post('/api/compare', json={"location_a": a, "location_b": a}).status_code == 422


def test_atmospheric_ui_requests_have_supported_nasa_variables():
    client = TestClient(main.app)
    variable_ids = {v["id"] for v in client.get("/api/variables").json()}
    assert {"CLOUD_AMT", "AOD_55"} <= variable_ids
    html = client.get("/").text
    assert 'data-atmosphere="clouds"' in html
    assert 'data-atmosphere="aerosols"' in html
    assert 'data-atmosphere="ozone"' not in html
    script = client.get('/static/app.js').text
    assert 'function investigateAtmosphere()' in script or 'async function investigateAtmosphere()' in script
    assert "fetch('/api/analyze'" in script
    assert "fetch('/api/compare'" in script


def test_compare_custom_coordinate_request_with_atmospheric_variable(monkeypatch):
    def fake_fetch(lat, lon, start, end, var):
        base = sample_payload()['properties']['parameter']['T2M']
        records = {key: (v + lat/100) for key, v in base.items() if len(key) == 6}
        return {'properties': {'parameter': {var: records}}}, 'cache'
    monkeypatch.setattr(main, 'fetch_monthly_variable', fake_fetch)
    client = TestClient(main.app)
    first = {'latitude':43.65, 'longitude':-79.4,'start_year':2001,'end_year':2020,'variables':['AOD_55']}
    second = {'latitude':-33.87, 'longitude':151.2,'start_year':2001,'end_year':2020,'variables':['AOD_55']}
    response = client.post('/api/compare', json={'location_a':first, 'location_b':second})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['a']['variable']['id'] == 'AOD_55'
    assert body['b']['variable']['id'] == 'AOD_55'
    assert body['a']['location']['latitude'] == 43.65
    assert body['b']['location']['longitude'] == 151.2
    assert len(body['a']['observed_annual_series']) == 20
