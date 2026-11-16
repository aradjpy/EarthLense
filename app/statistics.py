"""Trend statistics: NumPy for arithmetic, SciPy only for t probabilities.

OLS, Pearson correlation, SSE, MSE, R^2, standard errors and test statistic
are implemented directly using their formulas, not regression libraries.
"""

import numpy as np
from scipy.stats import t


class TrendError(ValueError):
    """Raised when annual measurements cannot support trend inference."""


def fit_annual_trend(years: list[int], values: list[float]) -> dict:
    # Keep the API name and response structure used by app/main.py.
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)

    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) < 10:
        raise TrendError("At least 10 paired annual observations are required")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise TrendError("All years and measurement values must be finite")
    if len(np.unique(x)) != len(x):
        raise TrendError("Duplicate years detected")

    # Sort by year, and shift x so the intercept belongs to the first year.
    order = np.argsort(x)
    years_sorted = x[order].astype(int)
    y = y[order]
    x = x[order] - x[order][0]
    n = len(x)

    # Calculate means and the sums used by Pearson's r and OLS.
    xMean = np.mean(x)
    yMean = np.mean(y)
    numerator = np.sum((x - xMean) * (y - yMean))
    sxx = np.sum((x - xMean)**2)
    syy = np.sum((y - yMean)**2)

    if sxx == 0 or syy == 0:
        raise TrendError("Cannot fit a trend to constant years or measurements")

    # Pearson's correlation coefficient.
    r = numerator / np.sqrt(sxx * syy)

    # Ordinary least squares: slope and intercept.
    b1 = numerator / sxx
    b0 = yMean - b1 * xMean

    # Predictions, residuals and their squared errors.
    yP = b0 + b1 * x
    errors = y - yP
    SSE = np.sum(errors**2)
    MSE = SSE / n
    r2 = float(np.clip(r**2, 0, 1))

    # Estimate the error variance with n - 2 degrees of freedom.
    df = n - 2
    residualVariance = SSE / df
    SE = np.sqrt(residualVariance / sxx)

    # Two-sided test of H0: slope = 0.
    if SE <= np.finfo(float).eps * max(1.0, abs(float(b1))):
        t1 = None
        pValue = 0.0 if abs(float(b1)) > 0 else 1.0
    else:
        t1 = float(b1 / SE)
        pValue = float(2 * t.sf(abs(t1), df))

    # 95% confidence interval, using only SciPy's probability distribution.
    tCritical = t.ppf(0.975, df)
    low = b1 - tCritical * SE
    high = b1 + tCritical * SE
    significant = pValue < 0.05
    estimatedChange = b1 * (np.max(x) - np.min(x))

    if significant and b1 > 0:
        direction = "increasing"
    elif significant and b1 < 0:
        direction = "decreasing"
    else:
        direction = "no statistically significant trend detected"

    return {
        "method": "OLS on complete-year annual means; two-sided Student t-test",
        "n_years": int(n),
        "slope_per_year": float(b1),
        "slope_per_decade": float(b1 * 10),
        "slope_95pct_ci_per_decade": [float(low * 10), float(high * 10)],
        "p_value": float(pValue),
        "r_squared": float(r2),
        "mse_units_squared": float(MSE),
        # Preserve the original temperature-specific field for compatibility.
        "mse_celsius_squared": float(MSE),
        "residual_mean_square": float(residualVariance),
        "slope_standard_error": float(SE),
        "t_statistic": t1,
        "degrees_of_freedom": int(df),
        "estimated_change_over_period": float(estimatedChange),
        "statistically_significant_at_0_05": bool(significant),
        "interpretation": direction,
        "fitted_annual_series": [
            {"year": int(year), "value": float(value)}
            for year, value in zip(years_sorted, yP)
        ],
        "caveat": (
            "Classical OLS p-values and confidence intervals assume independent, "
            "constant-variance residuals; temporal autocorrelation can affect significance."
        ),
    }
