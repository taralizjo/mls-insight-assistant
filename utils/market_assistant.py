"""Chat-driven market assistant: renders the conversation UI and routes each
turn to either the comparable-sales conversation or the grounded market-
analysis flow."""

import re

import streamlit as st

from utils.ai_helper import (
    DEFAULT_CLAUDE_MODEL,
    ask_claude,
    build_market_context,
    escape_currency_for_streamlit,
)
from utils.charts import create_monthly_price_trend_chart
from utils.comparable_sales_skill import (
    extract_comparable_criteria,
    get_comparable_prompt,
    get_missing_comparable_field,
    is_comparable_sales_request,
    run_comparable_sales_search,
    update_comparable_criteria,
)
from utils.market_analysis_skill import calculate_market_analysis, get_market_intent


EXIT_SIGNAL_PATTERN = re.compile(
    r"\b(?:stop|cancel|break|never\s*mind|forget\s+it|start\s+over|exit|quit|reset)\b",
    re.IGNORECASE,
)


def is_exit_signal(question: str) -> bool:
    """Return whether a message asks to leave the comparable-sales flow."""
    return bool(EXIT_SIGNAL_PATTERN.search(question))


def is_comparable_answer(question, pending_criteria, updated_criteria) -> bool:
    """Return whether a mid-flow message answers the pending comparable-sales question."""
    if is_comparable_sales_request(question):
        return True
    # An answer always supplies at least one new criterion.
    if updated_criteria == pending_criteria:
        return False
    # A message can mention a date or price and still be a market question
    # ("show a chart of prices over the last year"), so a specific market
    # intent means the user changed the subject rather than answered.
    return get_market_intent(question) == "market_overview"


def render_chat_message(message):
    """Render text plus any result table or chart stored with a chat response."""
    with st.chat_message(message["role"]):
        st.markdown(escape_currency_for_streamlit(message["content"]))
        if "table" in message:
            st.dataframe(
                message["table"],
                column_config={
                    "Sale Price": st.column_config.NumberColumn(format="$%d"),
                    "Living Area (sq ft)": st.column_config.NumberColumn(format="%d sq ft"),
                },
                hide_index=True,
                use_container_width=True,
            )
        if "monthly_data" in message:
            st.plotly_chart(
                create_monthly_price_trend_chart(message["monthly_data"]),
                use_container_width=True,
            )


def render_market_assistant(
    df,
    filtered_df,
    zipcode_comparison,
    selected_zipcodes,
    selected_bedrooms,
    selected_bathrooms,
    minimum_price,
    maximum_price,
    waterfront_filter,
):
    """Render the chat assistant and handle one question/answer turn.

    `df` is the full cleaned dataset (used for reference dates and the
    comparable-sales search); `filtered_df` and `zipcode_comparison` reflect
    the sidebar filters currently applied.
    """
    st.divider()
    st.header("Market Assistant")
    st.caption(
        "Ask follow-up questions about this historical filtered market without repeating your earlier question."
    )
    filter_signature = (
        tuple(selected_zipcodes),
        tuple(selected_bedrooms),
        tuple(selected_bathrooms),
        minimum_price,
        maximum_price,
        waterfront_filter,
    )

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
        st.session_state["chat_filter_signature"] = filter_signature
        st.session_state["pending_comparable_criteria"] = None
    else:
        st.session_state.setdefault("pending_comparable_criteria", None)
        if st.session_state["chat_filter_signature"] != filter_signature:
            st.session_state["chat_messages"] = []
            st.session_state["chat_filter_signature"] = filter_signature
            st.session_state["pending_comparable_criteria"] = None
            st.info("Market filters changed, so a new conversation has started for this market view.")

    if st.button("Clear conversation"):
        st.session_state["chat_messages"] = []
        st.session_state["pending_comparable_criteria"] = None
        st.rerun()

    if not st.session_state["chat_messages"]:
        st.info(
            "Try asking: “Summarize this market for a broker,” “Are prices going up or down?”, "
            "or “Find waterfront homes sold between $800k and $1.2M in the last 6 months.”"
        )

    for message in st.session_state["chat_messages"]:
        render_chat_message(message)

    starter_columns = st.columns(4)
    starter_questions = [
        "Summarize this market for a broker.",
        "Find comparable sales.",
        "Are prices going up or down?",
        "Show a chart of home prices over the last year.",
    ]
    starter_labels = [
        "Summarize market",
        "Find comparable sales",
        "Price direction",
        "Show price chart",
    ]
    starter_question = None
    for column, label, prompt in zip(starter_columns, starter_labels, starter_questions):
        if column.button(label, use_container_width=True):
            starter_question = prompt

    question = st.chat_input("Ask about this market...") or starter_question
    if not question:
        return

    user_message = {"role": "user", "content": question}
    st.session_state["chat_messages"].append(user_message)
    render_chat_message(user_message)

    pending_criteria = st.session_state["pending_comparable_criteria"]
    if is_exit_signal(question):
        st.session_state["pending_comparable_criteria"] = None
        criteria = None
    elif pending_criteria is not None:
        updated_criteria = update_comparable_criteria(
            pending_criteria,
            question,
            df["date"].max(),
            get_missing_comparable_field(pending_criteria),
        )
        if is_comparable_answer(question, pending_criteria, updated_criteria):
            criteria = updated_criteria
        else:
            # The user changed the subject, so drop the pending comparable
            # search and let the market assistant handle the question.
            st.session_state["pending_comparable_criteria"] = None
            criteria = None
    elif is_comparable_sales_request(question):
        criteria = extract_comparable_criteria(question, df["date"].max())
    else:
        criteria = None

    if criteria is not None:
        missing_field = get_missing_comparable_field(criteria)
        if missing_field:
            st.session_state["pending_comparable_criteria"] = criteria
            assistant_message = {
                "role": "assistant",
                "content": get_comparable_prompt(missing_field),
            }
        else:
            st.session_state["pending_comparable_criteria"] = None
            summary, comparable_table = run_comparable_sales_search(df, criteria)
            assistant_message = {
                "role": "assistant",
                "content": summary,
                "table": comparable_table,
            }
    else:
        active_filters = {
            "ZIP codes": ", ".join(selected_zipcodes) if selected_zipcodes else "All ZIP codes",
            "bedrooms": ", ".join(map(str, selected_bedrooms)) if selected_bedrooms else "All bedroom counts",
            "bathrooms": ", ".join(map(str, selected_bathrooms)) if selected_bathrooms else "All bathroom counts",
            "sale price range": f"${minimum_price:,.0f} to ${maximum_price:,.0f}",
            "waterfront": waterfront_filter,
        }
        market_context = build_market_context(
            filtered_df,
            active_filters,
            zipcode_comparison,
        )
        intent = get_market_intent(question)
        analysis = calculate_market_analysis(filtered_df, intent)

        if analysis["kind"] == "limitation":
            assistant_message = {"role": "assistant", "content": analysis["summary"]}
        else:
            api_key = st.secrets.get("ANTHROPIC_API_KEY")
            if not api_key:
                assistant_message = {
                    "role": "assistant",
                    "content": "I need a valid Anthropic API key to explain this calculated market result.",
                }
            else:
                try:
                    with st.spinner("Thinking about this market..."):
                        ai_response = ask_claude(
                            question=question,
                            market_context=market_context,
                            api_key=api_key,
                            model=st.secrets.get("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL),
                            conversation_history=st.session_state["chat_messages"][:-1],
                            calculated_analysis=analysis["summary"],
                        )
                except Exception as error:
                    assistant_message = {
                        "role": "assistant",
                        "content": "Claude could not generate an insight. Please try again.",
                        "error": f"{type(error).__name__}: {error}",
                    }
                else:
                    assistant_message = {"role": "assistant", "content": ai_response}
                    if analysis["show_chart"]:
                        assistant_message["monthly_data"] = analysis["monthly_data"]

    st.session_state["chat_messages"].append(assistant_message)
    render_chat_message(assistant_message)
    if "error" in assistant_message:
        with st.expander("Technical details"):
            st.code(assistant_message["error"])
