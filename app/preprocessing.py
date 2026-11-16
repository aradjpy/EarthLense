"""Parse monthly NASA POWER observations and average complete calendar years."""

import calendar
import math
import re

import pandas as pd


class DataQualityError(ValueError):
    pass


def parse_monthly_variable(payload: dict, variable: str) -> pd.DataFrame:
    try:
        raw = payload["properties"]["parameter"][variable]
    except (KeyError, TypeError) as error:
        raise DataQualityError(f"Expected NASA properties.parameter.{variable}") from error

    records = []
    for key, value in raw.items():
        if not re.fullmatch(r"\d{6}", str(key)):
            continue
        year, month = int(str(key)[:4]), int(str(key)[4:])
        if not 1 <= month <= 12:
            continue
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric) or not math.isfinite(float(numeric)) or float(numeric) == -999.0:
            continue
        records.append({"date": pd.Timestamp(year, month, 1), "year": year,
                        "month": month, "value": float(numeric)})

    if not records:
        raise DataQualityError(f"No valid monthly {variable} observations found")
    df = pd.DataFrame(records).drop_duplicates(subset="date", keep="first")
    return df.sort_values("date").reset_index(drop=True)


def annual_mean(monthly: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    """Days-weighted annual mean for monthly-mean intensive variables.

    Suitable for T2M, RH2M and WS2M (means); not for accumulated precipitation.
    """
    df = monthly.loc[monthly["year"].between(start_year, end_year)].copy()
    if df.empty:
        raise DataQualityError("No observations in the requested period")

    df["days"] = [calendar.monthrange(int(y), int(m))[1]
                  for y, m in zip(df["year"], df["month"])]
    results = []
    for year, group in df.groupby("year"):
        if set(group["month"].tolist()) != set(range(1, 13)) or len(group) != 12:
            continue
        value = sum(float(v) * int(d) for v, d in zip(group["value"], group["days"])) / sum(group["days"])
        results.append({"year": int(year), "value": float(value)})

    if not results:
        raise DataQualityError("No complete years (12 valid months per year)")
    return pd.DataFrame(results).sort_values("year").reset_index(drop=True)


def parse_monthly_temperature(payload: dict) -> pd.DataFrame:
    return parse_monthly_variable(payload, "T2M").rename(columns={"value": "temperature_c"})


def annual_temperature(monthly: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return annual_mean(monthly.rename(columns={"temperature_c": "value"}),
                       start_year, end_year).rename(columns={"value": "temperature_c"})
