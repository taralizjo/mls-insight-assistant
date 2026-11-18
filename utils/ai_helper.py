"""Helpers for grounded Claude market insights."""

import json
import re

import pandas as pd


DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """
You are a helpful real-estate market assistant for brokers and realtors.
Answer only from the supplied historical King County sale-data summary.
The data covers 2014-2015 and is not current market data.
Use clear, non-technical language and concise bullet points when useful.
Do not invent facts, property details, or trends not in the summary.
If the question cannot be answered from the summary, say so plainly.
Do not provide legal, investment, lending, or appraisal advice.
Use plain text only: do not use Markdown headings, bold, italics, tables, asterisks,
underscores, backticks, HTML, or LaTex. Use short hyphen bullets if needed.
Write currency as USD 765,475 rather than using a dollar sign.
""".strip()


def build_market_context(
    df: pd.DataFrame,
    active_filters: dict[str, str],
    zipcode_comparison: pd.DataFrame | None = None,
) -> str:
    """Build a compact, factual market brief for Claude."""
    bedroom_summary = (
        df.groupby("bedrooms", as_index=False)
        .agg(
            homes_sold=("price", "size"),
            typical_sale_price=("price", "median"),
            average_price_per_sqft=("price_per_sq_foot", "mean"),
        )
        .round(2)
    )

    context = {
        "data_scope": "Historical King County home sales from 2014-2015.",
        "app_controls": {
            "available_filters": (
                "The app has a Refine the Market View panel at the top of the page "
                "with filters for ZIP code, bedrooms, bathrooms, sale price range, "
                "and waterfront."
            ),
            "already_applied": (
                "The active_filters values below are already applied to every number "
                "in this summary."
            ),
            "how_to_answer_filter_requests": (
                "If the broker asks to filter or narrow the market, such as showing "
                "waterfront homes only, point them to the matching filter in that "
                "panel. Never say the app cannot filter that way."
            ),
        },
        "active_filters": active_filters,
        "market_summary": {
            "matching_sales": len(df),
            "typical_sale_price": round(df["price"].median(), 2),
            "average_price_per_sqft": round(df["price_per_sq_foot"].mean(), 2),
            "average_home_age": round(df["house_age"].mean(), 1),
            "sale_price_range": {
                "minimum": int(df["price"].min()),
                "maximum": int(df["price"].max()),
            },
        },
        "price_by_bedrooms": json.loads(bedroom_summary.to_json(orient="records")),
    }

    if zipcode_comparison is not None and not zipcode_comparison.empty:
        comparison_columns = [
            "ZIP Code",
            "Typical Sale Price",
            "Average Price per Sq. Ft.",
            "Homes Sold",
            "Compared with County",
        ]
        context["selected_zipcode_comparison"] = json.loads(
            zipcode_comparison[comparison_columns].to_json(orient="records")
        )

    return json.dumps(context, indent=2)


def ask_claude(
    question: str,
    market_context: str,
    api_key: str,
    model: str = DEFAULT_CLAUDE_MODEL,
    conversation_history: list[dict[str, str]] | None = None,
    calculated_analysis: str | None = None,
) -> str:
    """Ask Claude a grounded follow-up question about the current market view."""
    if not question.strip():
        raise ValueError("Enter a question before requesting an AI insight.")

    try:
        from anthropic import Anthropic
    except ImportError as error:
        raise RuntimeError(
            "The Anthropic package is not installed. Run pip install -r requirements.txt."
        ) from error

    recent_history = (conversation_history or [])[-8:]
    messages = [
        {"role": message["role"], "content": message["content"]}
        for message in recent_history
        if message.get("role") in {"user", "assistant"} and message.get("content")
    ]
    messages.append(
        {
            "role": "user",
            "content": (
                "Current market data summary:\n"
                f"{market_context}\n\n"
                "Calculated analysis (use these numbers; do not recalculate or invent values):\n"
                f"{calculated_analysis or 'No additional calculation was requested.'}\n\n"
                f"Current broker question: {question.strip()}"
            ),
        }
    )

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()


def escape_currency_for_streamlit(text: str) -> str:
    """Escape currency symbols so Streamlit never interprets them as LaTex."""
    return re.sub(r"(?<!\\)\$(?=\s*\d)", r"\\$", text)
