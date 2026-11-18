import pandas as pd


def get_listing_results(
    df: pd.DataFrame,
    sort_by: str = "Lowest sale price",
) -> pd.DataFrame:
    """Return filtered homes in a broker-friendly table format."""
    listings = df[
        [
            "id",
            "date",
            "price",
            "price_per_sq_foot",
            "bedrooms",
            "bathrooms",
            "sqft_living",
            "zipcode",
            "waterfront",
        ]
    ].copy()

    sort_options = {
        "Lowest sale price": ("price", True),
        "Highest sale price": ("price", False),
        "Largest living area": ("sqft_living", False),
        "Lowest price per sq. ft.": ("price_per_sq_foot", True),
        "Highest price per sq. ft.": ("price_per_sq_foot", False),
        "Most recent sale date": ("date", False),
    }
    sort_column, ascending = sort_options[sort_by]
    listings = listings.sort_values(sort_column, ascending=ascending)

    listings["date"] = listings["date"].dt.strftime("%b %d, %Y")
    listings["id"] = listings["id"].astype(str)
    listings["waterfront"] = listings["waterfront"].map({1: "Yes", 0: "No"})

    return listings.rename(
        columns={
            "id": "Listing ID",
            "date": "Sale Date",
            "price": "Sale Price",
            "price_per_sq_foot": "Price per Sq. Ft.",
            "bedrooms": "Bedrooms",
            "bathrooms": "Bathrooms",
            "sqft_living": "Living Area (sq ft)",
            "zipcode": "ZIP Code",
            "waterfront": "Waterfront",
        }
    )


def get_listing_details(df: pd.DataFrame, sale_record_id: int) -> pd.Series:
    """Return details for one specific historical sale record."""
    return df.loc[
        sale_record_id,
        [
            "id",
            "date",
            "price",
            "price_per_sq_foot",
            "bedrooms",
            "bathrooms",
            "sqft_living",
            "zipcode",
            "yr_built",
            "house_age",
            "is_renovated",
            "waterfront",
        ],
    ]


def find_comparable_sales(
    df: pd.DataFrame,
    listing_id: str = "",
    sale_date=None,
    sale_price: int | None = None,
    start_date=None,
    end_date=None,
    minimum_price: int | None = None,
    maximum_price: int | None = None,
    waterfront: bool | None = None,
) -> pd.DataFrame:
    """Return sales matching optional listing and comparable-search criteria."""
    matches = df.copy()

    if listing_id:
        matches = matches[matches["id"].astype(str) == listing_id.strip()]

    if sale_date is not None:
        matches = matches[matches["date"].dt.date == sale_date]

    if sale_price is not None:
        matches = matches[matches["price"] == sale_price]

    if start_date is not None:
        matches = matches[matches["date"] >= pd.Timestamp(start_date)]

    if end_date is not None:
        matches = matches[matches["date"] <= pd.Timestamp(end_date)]

    if minimum_price is not None:
        matches = matches[matches["price"] >= minimum_price]

    if maximum_price is not None:
        matches = matches[matches["price"] <= maximum_price]

    if waterfront is not None:
        matches = matches[matches["waterfront"] == int(waterfront)]

    return matches


def get_sale_selection_labels(df: pd.DataFrame) -> dict[int, str]:
    """Return short labels for choosing a specific sale record."""
    return {
        record_id: f"Listing ID {row['id']} — {row['date']:%b %d, %Y}"
        for record_id, row in df.iterrows()
    }
