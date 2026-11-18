import pandas as pd


def load_data(path="data/kc_house_data.csv"):
    df = pd.read_csv(path)
    return _clean_and_enrich(df)


def _clean_and_enrich(df):
    # Convert the date column
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%dT%H%M%S")
    # Extract sale year
    df["sale_year"] = df["date"].dt.year
    # Extract sale month
    df["sale_month"] = df["date"].dt.month
    # Create price per square foot
    df["price_per_sq_foot"] = df["price"] / df["sqft_living"]
    # Calculate house age
    df["house_age"] = df["sale_year"] - df["yr_built"]
    # Create renovation flag
    df["is_renovated"] = df["yr_renovated"] > 0

    # Remove invalid records: rows that are either impossible
    # (zero living space/price) or known bad data (the 33-bedroom outlier)
    df = df[
        (df["price"] > 0)
        & (df["sqft_living"] > 0)
        & (df["bedrooms"] > 0)
        & (df["bedrooms"] <= 10)
        & (df["bathrooms"] > 0)
        & (df["house_age"] >= 0)
    ]

    return df.reset_index(drop=True)