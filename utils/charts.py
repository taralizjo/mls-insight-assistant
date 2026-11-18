import plotly.express as px
import pandas as pd


def create_price_distribution_chart(df: pd.DataFrame):
    """Create a histogram showing where most homes sold."""
    median_price = df["price"].median()
    fig = px.histogram(
        df,
        x="price",
        nbins=40,
        title="Where Most Homes Sold",
        labels={"price": "Sale Price ($)", "count": "Homes Sold"},
    )
    fig.add_vline(
        x=median_price,
        line_dash="dash",
        line_color="#1f77b4",
        annotation_text=f"Typical price: ${median_price:,.0f}",
        annotation_position="top right",
    )
    fig.update_xaxes(tickprefix="$", tickformat=",")
    fig.update_layout(height=400, bargap=0.05)

    return fig


def create_median_price_by_bedrooms_chart(df: pd.DataFrame):
    """Create a comparison of typical sale price by bedroom count."""
    bedroom_prices = (
        df.groupby("bedrooms", as_index=False)
        .agg(median_price=("price", "median"), listings=("price", "size"))
        .sort_values("bedrooms")
    )
    bedroom_prices["bedrooms"] = bedroom_prices["bedrooms"].astype(str)

    fig = px.bar(
        bedroom_prices,
        x="bedrooms",
        y="median_price",
        title="Typical Sale Price by Bedrooms",
        labels={
            "bedrooms": "Bedrooms",
            "median_price": "Typical Sale Price ($)",
            "listings": "Homes Sold",
        },
        hover_data={"listings": True, "median_price": ":$,.0f"},
        text="median_price",
    )
    fig.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_yaxes(showticklabels=False, title=None)
    fig.update_layout(height=400, margin={"l": 20, "r": 20, "t": 60, "b": 20})

    return fig


def create_monthly_price_trend_chart(monthly_data: pd.DataFrame):
    """Create a monthly median sale-price trend chart for chat responses."""
    fig = px.line(
        monthly_data,
        x="month_label",
        y="median_price",
        markers=True,
        title="Monthly Median Sale Price",
        labels={
            "month_label": "Sale Month",
            "median_price": "Median Sale Price ($)",
        },
    )
    fig.update_yaxes(tickprefix="$", tickformat=",")
    fig.update_layout(height=360, margin={"l": 20, "r": 20, "t": 60, "b": 20})

    return fig
