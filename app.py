import streamlit as st

from utils.data_loader import load_data
from utils.market_assistant import render_market_assistant
from utils.market_comparison import get_zipcode_market_comparison
from utils.metrics import (
    get_average_house_age,
    get_average_price_per_sqft,
    get_median_price,
    get_total_listings,
)


st.set_page_config(
    page_title="MLS Insight Assistant",
    page_icon="🏠",
    layout="wide",
)

st.markdown(
    """
    <style>
    [data-testid="stDecoration"] {
        display: none;
    }

    .stApp {
        background-color: #F5F6FA;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica,
            Arial, sans-serif;
        color: #1F2937;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("MLS Insight Assistant")
st.caption("Historical King County home-sale data (2014–2015)")

df = load_data()

minimum_dataset_price = int(df["price"].min())
maximum_dataset_price = int(df["price"].max())

if st.session_state.get("minimum_price", minimum_dataset_price) < minimum_dataset_price:
    st.session_state["minimum_price"] = minimum_dataset_price
if st.session_state.get("maximum_price", maximum_dataset_price) < minimum_dataset_price:
    st.session_state["maximum_price"] = maximum_dataset_price


def reset_filters():
    """Restore the sidebar filters to the full-market view."""
    st.session_state["selected_zipcodes"] = []
    st.session_state["selected_bedrooms"] = []
    st.session_state["selected_bathrooms"] = []
    st.session_state["minimum_price"] = minimum_dataset_price
    st.session_state["maximum_price"] = maximum_dataset_price
    st.session_state["waterfront_filter"] = "All homes"


zipcodes = sorted(df["zipcode"].astype(str).unique())
with st.expander("Refine the Market View", expanded=True):
    st.caption("Update the market summary, ZIP comparison, and assistant context.")
    location_column, bedroom_column, bathroom_column, waterfront_column = st.columns(4)
    with location_column:
        selected_zipcodes = st.multiselect(
            "ZIP codes",
            options=zipcodes,
            key="selected_zipcodes",
        )
    with bedroom_column:
        selected_bedrooms = st.multiselect(
            "Bedrooms",
            options=sorted(df["bedrooms"].unique()),
            key="selected_bedrooms",
        )
    with bathroom_column:
        selected_bathrooms = st.multiselect(
            "Bathrooms",
            options=sorted(df["bathrooms"].unique()),
            key="selected_bathrooms",
        )
    with waterfront_column:
        waterfront_filter = st.selectbox(
            "Waterfront",
            options=["All homes", "Waterfront only", "Non-waterfront only"],
            key="waterfront_filter",
        )

    minimum_price_column, maximum_price_column, reset_column = st.columns([1, 1, 2])
    with minimum_price_column:
        minimum_price = st.number_input(
            "Minimum price ($)",
            min_value=minimum_dataset_price,
            max_value=maximum_dataset_price,
            value=minimum_dataset_price,
            step=10_000,
            format="%d",
            key="minimum_price",
        )
    with maximum_price_column:
        maximum_price = st.number_input(
            "Maximum price ($)",
            min_value=minimum_dataset_price,
            max_value=maximum_dataset_price,
            value=maximum_dataset_price,
            step=10_000,
            format="%d",
            key="maximum_price",
        )
    with reset_column:
        st.write("")
        st.button("Reset filters", on_click=reset_filters, use_container_width=True)

if minimum_price > maximum_price:
    st.error("Minimum price must be less than or equal to maximum price.")
    st.stop()

comparison_df = df[df["price"].between(minimum_price, maximum_price)].copy()

if selected_bedrooms:
    comparison_df = comparison_df[comparison_df["bedrooms"].isin(selected_bedrooms)]

if selected_bathrooms:
    comparison_df = comparison_df[comparison_df["bathrooms"].isin(selected_bathrooms)]

if waterfront_filter == "Waterfront only":
    comparison_df = comparison_df[comparison_df["waterfront"] == 1]
elif waterfront_filter == "Non-waterfront only":
    comparison_df = comparison_df[comparison_df["waterfront"] == 0]

filtered_df = comparison_df.copy()

if selected_zipcodes:
    filtered_df = filtered_df[filtered_df["zipcode"].astype(str).isin(selected_zipcodes)]

if filtered_df.empty:
    st.warning("No homes match these filters. Try widening your selection.")
    st.stop()

zipcode_comparison = None
if selected_zipcodes:
    zipcode_comparison = get_zipcode_market_comparison(filtered_df, comparison_df)

st.caption(f"{get_total_listings(filtered_df):,} homes match your filters.")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Typical Home Price", f"${get_median_price(filtered_df):,.0f}")
col2.metric(
    "Average Price per Sq. Ft.",
    f"${get_average_price_per_sqft(filtered_df):,.0f}",
)
col3.metric("Homes in This View", f"{get_total_listings(filtered_df):,}")
col4.metric("Average Home Age", f"{get_average_house_age(filtered_df):.1f} years")

st.subheader("What This Means")
st.markdown(
    f"- The typical comparable sale matching your search is "
    f"**${get_median_price(filtered_df):,.0f}**."
)
if len(selected_zipcodes) == 1:
    selected_market = zipcode_comparison.iloc[0]
    st.markdown(
        f"- In ZIP **{selected_market['ZIP Code']}**, typical sale prices are "
        f"**{selected_market['Compared with County']}**."
    )
elif len(selected_zipcodes) > 1:
    st.markdown("- Use the ZIP code comparison below to compare your selected markets.")

st.divider()

if len(selected_zipcodes) == 1:
    st.subheader(f"ZIP {selected_market['ZIP Code']} Market Snapshot")
    st.caption("Compared with the King County market after applying your other filters.")

    price_column, price_per_sqft_column, homes_sold_column = st.columns(3)
    price_column.metric(
        "Typical Sale Price",
        f"${selected_market['Typical Sale Price']:,.0f}",
        selected_market["Compared with County"],
        delta_color="off",
    )
    price_per_sqft_column.metric(
        "Average Price per Sq. Ft.",
        f"${selected_market['Average Price per Sq. Ft.']:,.0f}",
        selected_market["Price per Sq. Ft. Compared with County"],
        delta_color="off",
    )
    homes_sold_column.metric("Homes Sold", f"{selected_market['Homes Sold']:,}")
elif len(selected_zipcodes) > 1:
    st.subheader("ZIP Code Comparison")
    st.caption("Each ZIP code is compared with the King County market after applying your other filters.")
    st.dataframe(
        zipcode_comparison[
            [
                "ZIP Code",
                "Typical Sale Price",
                "Average Price per Sq. Ft.",
                "Homes Sold",
                "Compared with County",
            ]
        ],
        column_config={
            "Typical Sale Price": st.column_config.NumberColumn(format="$%d"),
            "Average Price per Sq. Ft.": st.column_config.NumberColumn(format="$%d"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info(
        "Select one ZIP code to see its market snapshot, or select multiple ZIP codes "
        "to compare them side by side."
    )

render_market_assistant(
    df,
    filtered_df,
    zipcode_comparison,
    selected_zipcodes,
    selected_bedrooms,
    selected_bathrooms,
    minimum_price,
    maximum_price,
    waterfront_filter,
)
