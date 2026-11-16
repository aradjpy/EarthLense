"""Translate the existing scientific trend result into approachable, honest language.

No new statistical claims are made here. Significance still comes from the OLS
analysis in app/statistics.py; this module only explains those results.
"""

VARIABLE_LANGUAGE = {
    "T2M": {
        "subject": "average air temperature",
        "rising": "getting warmer",
        "falling": "getting cooler",
        "rise_noun": "warming",
        "fall_noun": "cooling",
        "unit_words": "degrees Celsius",
        "emoji_rise": "☀️",
        "emoji_fall": "🧊",
        "explanation": "Temperature tells us how warm or cool the air is.",
    },
    "RH2M": {
        "subject": "average relative humidity",
        "rising": "getting more humid",
        "falling": "getting less humid",
        "rise_noun": "an increase in relative humidity",
        "fall_noun": "a decrease in relative humidity",
        "unit_words": "percentage points",
        "emoji_rise": "💧",
        "emoji_fall": "🌵",
        "explanation": "Relative humidity tells us how close the air is to being full of water vapor.",
    },
    "CLOUD_AMT": {
        "subject": "average cloud cover",
        "rising": "seeing more cloud cover",
        "falling": "seeing less cloud cover",
        "rise_noun": "an increase in average cloud cover",
        "fall_noun": "a decrease in average cloud cover",
        "unit_words": "percentage points",
        "emoji_rise": "☁️",
        "emoji_fall": "🌤️",
        "explanation": "Cloud cover means the percentage of the sky covered by clouds, averaged across the area.",
    },
    "AOD_55": {
        "subject": "aerosol optical depth",
        "rising": "showing a higher aerosol reading",
        "falling": "showing a lower aerosol reading",
        "rise_noun": "an increase in aerosol optical depth",
        "fall_noun": "a decrease in aerosol optical depth",
        "unit_words": "AOD units",
        "emoji_rise": "🌫️",
        "emoji_fall": "🌤️",
        "explanation": "Aerosol optical depth measures how much tiny atmospheric particles block or scatter sunlight. It isn't a direct measure of air quality at street level.",
    },
    "WS2M": {
        "subject": "average wind speed",
        "rising": "getting windier",
        "falling": "getting calmer",
        "rise_noun": "an increase in wind speed",
        "fall_noun": "a decrease in wind speed",
        "unit_words": "meters per second",
        "emoji_rise": "💨",
        "emoji_fall": "🍃",
        "explanation": "Wind speed tells us how quickly the air is moving.",
    },
}


def explain_trend(variable_id: str, trend: dict, period: dict) -> dict:
    """Construct child-friendly copy from the original statistical results."""
    language = VARIABLE_LANGUAGE[variable_id]
    significant = bool(trend["statistically_significant_at_0_05"])
    slope = float(trend["slope_per_decade"])
    change = float(trend["estimated_change_over_period"])
    rising = slope > 0
    direction = language["rising"] if rising else language["falling"]
    movement = language["rise_noun"] if rising else language["fall_noun"]
    amount = f"{abs(slope):.2f} {language['unit_words']}"
    total = f"{abs(change):.2f} {language['unit_words']}"
    start = period["start_year"]
    end = period["end_year"]

    if significant:
        headline = f"The data suggests this area is {direction}!"
        explanation = (
            f"Looking at {start} to {end}, NASA's data shows a clear long-term "
            f"direction in {language['subject']}. The trend works out to about "
            f"{amount} every 10 years."
        )
        confidence = "A clear pattern"
        confidence_description = (
            "The evidence supports a long-term trend in this dataset. "
            "That doesn't tell us what caused it."
        )
        emoji = language["emoji_rise"] if rising else language["emoji_fall"]
    else:
        headline = "It's hard to tell if there's a lasting change."
        explanation = (
            f"NASA's {language['subject']} readings go up and down from year to year. "
            "The trend line leans one way, but the evidence isn't strong enough "
            "to say there's a clear long-term trend."
        )
        confidence = "Still a mystery"
        confidence_description = (
            "We can't confidently tell whether there's a lasting upward or downward "
            "trend from these years of data. That does not mean nothing changed."
        )
        emoji = "🔎"

    return {
        "headline": headline,
        "description": explanation,
        "emoji": emoji,
        "evidence_label": confidence,
        "evidence_description": confidence_description,
        "change_explanation": (
            f"The fitted trend suggests about {total} of {movement} "
            f"over {start}–{end}. This isn't the difference between two single days."
        ) if significant else (
            f"The fitted line gives an estimated change of {total} across {start}–{end}, "
            "but the direction is too uncertain to call a clear trend."
        ),
        "variable_explanation": language["explanation"],
        "data_note": (
            "These are NASA gridded estimates for an area, not readings from "
            "a thermometer or sensor on your street."
        ),
    }
