"""Calculated market-analysis helpers for chat responses."""

import pandas as pd


def get_market_intent(question: str) -> str:
    """Classify a market question into a supported analysis category."""
    question = question.lower()

    if "san francisco" in question or "sf market" in question:
        return "unsupported_location"
    if any(term in question for term in ("inventory", "currently on the market", "active listing")):
        return "inventory_unavailable"
    if any(term in question for term in ("buyers or sellers", "buyer", "seller leverage")):
        return "buyer_seller_unavailable"
    if any(term in question for term in ("selling faster", "days on market", "faster than last year")):
        return "days_on_market_unavailable"
    if any(term in question for term in ("softer", "stronger", "cooling", "heating up")):
        return "market_strength"
    if any(
        term in question
        for term in (
            "same month last year",
            "this month compare",
            "compared with last year",
            "compare with last year",
        )
    ):
        return "time_comparison"
    if "chart" in question or "graph" in question:
        return "price_trend_chart"
    if any(term in question for term in ("going up", "going down", "prices falling", "price trend", "home prices")):
        return "price_trend"
    return "market_overview"


def calculate_market_analysis(df: pd.DataFrame, intent: str) -> dict:
    """Calculate the factual data needed for a market-analysis response."""
    limitations = {
        "unsupported_location": (
            "I can only analyze the historical King County sales in this dataset, not the San Francisco market."
        ),
        "inventory_unavailable": (
            "This dataset contains completed historical sales, not active listings, so it cannot determine current inventory."
        ),
        "buyer_seller_unavailable": (
            "This dataset does not include buyer or seller counts, so it cannot measure current buyer-seller balance directly."
        ),
        "days_on_market_unavailable": (
            "This dataset does not include days-on-market data, so it cannot determine whether homes are selling faster or slower."
        ),
    }
    if intent in limitations:
        return {"kind": "limitation", "summary": limitations[intent]}

    monthly = _get_monthly_market_summary(df)
    latest = monthly.iloc[-1]

    if intent == "market_overview":
        return {
            "kind": "analysis",
            "summary": (
                f"The latest available month is {latest['month_label']}: {latest['sales_count']:,} sales, "
                f"a median sale price of ${latest['median_price']:,.0f}, and an average of "
                f"${latest['average_price_per_sqft']:,.0f} per square foot."
            ),
            "monthly_data": monthly,
            "show_chart": False,
        }

    prior_year = monthly[
        (monthly["sale_year"] == latest["sale_year"] - 1)
        & (monthly["sale_month"] == latest["sale_month"])
    ]

    if prior_year.empty:
        return {
            "kind": "limitation",
            "summary": "The available historical data does not include an equivalent month from the prior year for this comparison.",
        }

    prior = prior_year.iloc[0]
    price_change = _percent_change(latest["median_price"], prior["median_price"])
    sales_change = _percent_change(latest["sales_count"], prior["sales_count"])
    comparison_label = f"{latest['month_label']} compared with {prior['month_label']}"

    if intent in {"price_trend", "price_trend_chart", "time_comparison"}:
        direction = "increased" if price_change >= 0 else "decreased"
        summary = (
            f"Median sale price {direction} {abs(price_change):.1f}% in {comparison_label} "
            f"(${prior['median_price']:,.0f} to ${latest['median_price']:,.0f})."
        )
    else:  # market_strength
        price_direction = "up" if price_change >= 0 else "down"
        sales_direction = "up" if sales_change >= 0 else "down"
        summary = (
            f"Based on available sales data only, median price is {price_direction} "
            f"{abs(price_change):.1f}% and sales activity is {sales_direction} "
            f"{abs(sales_change):.1f}% in {comparison_label}. "
            "Inventory and days-on-market data are unavailable, so this is not a complete market-strength assessment."
        )

    return {
        "kind": "analysis",
        "summary": summary,
        "monthly_data": monthly,
        "show_chart": intent == "price_trend_chart",
    }


def _get_monthly_market_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return monthly sales, median price, and average price-per-square-foot metrics."""
    monthly = (
        df.groupby(["sale_year", "sale_month"], as_index=False)
        .agg(
            sales_count=("price", "size"),
            median_price=("price", "median"),
            average_price_per_sqft=("price_per_sq_foot", "mean"),
        )
        .sort_values(["sale_year", "sale_month"])
    )
    monthly["month_label"] = pd.to_datetime(
        dict(year=monthly["sale_year"], month=monthly["sale_month"], day=1)
    ).dt.strftime("%b %Y")
    return monthly


def _percent_change(current: float, previous: float) -> float:
    """Return a percent change from a nonzero earlier value."""
    return (current - previous) / previous * 100
