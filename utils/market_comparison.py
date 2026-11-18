import pandas as pd


def get_zipcode_market_comparison(
    selected_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare selected ZIP codes with the matching King County market."""
    county_median_price = market_df["price"].median()
    county_average_price_per_sqft = market_df["price_per_sq_foot"].mean()

    comparison = (
        selected_df.groupby("zipcode", as_index=False)
        .agg(
            typical_sale_price=("price", "median"),
            average_price_per_sqft=("price_per_sq_foot", "mean"),
            homes_sold=("price", "size"),
        )
        .sort_values("typical_sale_price", ascending=False)
    )

    comparison["price_difference"] = (
        comparison["typical_sale_price"] - county_median_price
    )
    comparison["price_difference_percent"] = (
        comparison["price_difference"] / county_median_price * 100
    )
    comparison["price_per_sqft_difference_percent"] = (
        (comparison["average_price_per_sqft"] - county_average_price_per_sqft)
        / county_average_price_per_sqft
        * 100
    )
    comparison["compared_with_county"] = comparison.apply(
        lambda row: _describe_market_position(
            row["price_difference_percent"], "county"
        ),
        axis=1,
    )
    comparison["price_per_sqft_compared_with_county"] = comparison.apply(
        lambda row: _describe_market_position(
            row["price_per_sqft_difference_percent"], "county"
        ),
        axis=1,
    )
    comparison["zipcode"] = comparison["zipcode"].astype(str)

    return comparison.rename(
        columns={
            "zipcode": "ZIP Code",
            "typical_sale_price": "Typical Sale Price",
            "average_price_per_sqft": "Average Price per Sq. Ft.",
            "homes_sold": "Homes Sold",
            "price_difference": "Price Difference",
            "price_difference_percent": "Price Difference (%)",
            "price_per_sqft_difference_percent": "Price per Sq. Ft. Difference (%)",
            "compared_with_county": "Compared with County",
            "price_per_sqft_compared_with_county": "Price per Sq. Ft. Compared with County",
        }
    )


def _describe_market_position(difference_percent: float, benchmark: str) -> str:
    """Return a plain-English description of a percentage difference."""
    if difference_percent == 0:
        return f"In line with {benchmark}"

    arrow = "↑" if difference_percent > 0 else "↓"
    direction = "higher" if difference_percent > 0 else "lower"
    return f"{arrow} {abs(difference_percent):.0f}% {direction} than {benchmark}"
