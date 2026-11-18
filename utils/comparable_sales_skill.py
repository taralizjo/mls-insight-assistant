"""Conversational comparable-sales helpers."""

import re

import pandas as pd

from utils.listings import find_comparable_sales, get_listing_results


COMPARABLE_REQUEST_PHRASES = (
    "find sales",
    "find homes",
    "find listings",
    "similar sales",
    "show me sales",
    "recent sales",
    "what sold",
    "homes sold",
    "sold homes",
    "sales data",
)
WATERFRONT_NO_PREFERENCE_ANSWERS = (
    "doesn't matter",
    "doesnt matter",
    "does not matter",
    "don't care",
    "dont care",
    "do not care",
    "no preference",
    "either",
    "any",
    "all",
)
WATERFRONT_NO_ANSWERS = (
    "non waterfront",
    "not waterfront",
    "no thanks",
    "nope",
    "no",
    "n",
)
WATERFRONT_YES_ANSWERS = (
    "waterfront only",
    "yes please",
    "waterfront",
    "yeah",
    "yep",
    "sure",
    "please",
    "yes",
    "y",
)


def is_comparable_sales_request(question: str) -> bool:
    """Return whether a question asks to find comparable sales."""
    question = question.lower()
    return bool(
        re.search(r"\bcomparables?\b|\bcomps?\b", question)
        or any(phrase in question for phrase in COMPARABLE_REQUEST_PHRASES)
    )


def extract_comparable_criteria(question: str, reference_date: pd.Timestamp) -> dict:
    """Extract supported comparable-sale criteria from natural language."""
    question_lower = question.lower()
    criteria = {}

    price_match = re.search(
        r"(?:between\s+)?\$?\s*([\d,.]+\s*[km]?)\s*(?:to|through|and|–|-)\s*\$?\s*([\d,.]+\s*[km]?)",
        question_lower,
    )
    if price_match:
        criteria["minimum_price"] = _parse_money(price_match.group(1))
        criteria["maximum_price"] = _parse_money(price_match.group(2))

    month_match = re.search(r"(?:last|past)\s+(\d+)\s+months?", question_lower)
    if month_match:
        months = int(month_match.group(1))
        criteria["start_date"] = reference_date - pd.DateOffset(months=months)
        criteria["end_date"] = reference_date
        criteria["date_label"] = f"the last {months} months of available data"
    elif "last year" in question_lower or "past year" in question_lower:
        criteria["start_date"] = reference_date - pd.DateOffset(years=1)
        criteria["end_date"] = reference_date
        criteria["date_label"] = "the last year of available data"

    if "non-waterfront" in question_lower or "not waterfront" in question_lower:
        criteria["waterfront"] = False
    elif "waterfront" in question_lower:
        criteria["waterfront"] = True

    return criteria


def update_comparable_criteria(
    criteria: dict,
    question: str,
    reference_date: pd.Timestamp,
    missing_field: str | None,
) -> dict:
    """Merge newly supplied criteria into a pending comparable-sales request."""
    updated_criteria = {**criteria, **extract_comparable_criteria(question, reference_date)}

    if missing_field == "waterfront" and "waterfront" not in updated_criteria:
        waterfront_preference = interpret_waterfront_answer(question)
        if waterfront_preference is not None:
            updated_criteria["waterfront"] = waterfront_preference

    return updated_criteria


def interpret_waterfront_answer(answer: str) -> bool | None:
    """Interpret a natural waterfront answer, returning None when no preference is given."""
    normalized = answer.lower().replace("’", "'")
    normalized = re.sub(r"[^a-z' ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if _contains_answer(normalized, WATERFRONT_NO_PREFERENCE_ANSWERS):
        return None
    if _contains_answer(normalized, WATERFRONT_NO_ANSWERS):
        return False
    if _contains_answer(normalized, WATERFRONT_YES_ANSWERS):
        return True

    return None


def _contains_answer(normalized_answer: str, phrases: tuple[str, ...]) -> bool:
    """Return whether a normalized answer contains any of the given whole-word phrases."""
    return any(
        re.search(rf"\b{re.escape(phrase)}\b", normalized_answer) for phrase in phrases
    )


def get_missing_comparable_field(criteria: dict) -> str | None:
    """Return the next minimum criterion needed for a useful comparable search."""
    if "start_date" not in criteria or "end_date" not in criteria:
        return "date_range"
    if "minimum_price" not in criteria or "maximum_price" not in criteria:
        return "price_range"
    return None


def get_comparable_prompt(missing_field: str) -> str:
    """Return a concise follow-up question for the missing criterion."""
    prompts = {
        "date_range": "What sale date range should I use? For example, “last 6 months.”",
        "price_range": "What sale price range should I use? For example, “$800k to $1.2M.”",
        "waterfront": "Should I limit the search to waterfront properties?",
    }
    return prompts[missing_field]


def run_comparable_sales_search(df: pd.DataFrame, criteria: dict) -> tuple[str, pd.DataFrame]:
    """Run a completed comparable-sales search and return a compact result table."""
    waterfront = criteria.get("waterfront")
    matches = find_comparable_sales(
        df,
        start_date=criteria["start_date"],
        end_date=criteria["end_date"],
        minimum_price=criteria["minimum_price"],
        maximum_price=criteria["maximum_price"],
        waterfront=waterfront,
    )

    price_range_label = (
        f"priced between ${criteria['minimum_price']:,.0f} "
        f"and ${criteria['maximum_price']:,.0f}"
    )
    if waterfront is None:
        summary = (
            f"I found {len(matches):,} comparable sales from "
            f"{criteria['date_label']} {price_range_label}, showing all homes "
            "(waterfront and non-waterfront)."
        )
    else:
        waterfront_label = "waterfront" if waterfront else "non-waterfront"
        summary = (
            f"I found {len(matches):,} {waterfront_label} comparable sales from "
            f"{criteria['date_label']} {price_range_label}."
        )

    results = get_listing_results(matches, sort_by="Most recent sale date")
    table_columns = [
        "Sale Price",
        "Sale Date",
        "Bedrooms",
        "Bathrooms",
        "Living Area (sq ft)",
        "Waterfront",
        "ZIP Code",
    ]
    return summary, results[table_columns]


def _parse_money(value: str) -> int:
    """Convert values such as 800k or 1.2m to whole dollars."""
    normalized = value.replace("$", "").replace(",", "").replace(" ", "")
    multiplier = 1
    if normalized.endswith("k"):
        multiplier = 1_000
        normalized = normalized[:-1]
    elif normalized.endswith("m"):
        multiplier = 1_000_000
        normalized = normalized[:-1]

    return int(float(normalized) * multiplier)
