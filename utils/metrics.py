import pandas as pd


def get_median_price(df: pd.DataFrame) -> float:
    """Return the median sale price."""
    return df["price"].median()


def get_average_price_per_sqft(df: pd.DataFrame) -> float:
    """Return the average sale price per square foot."""
    return df["price_per_sq_foot"].mean()


def get_total_listings(df: pd.DataFrame) -> int:
    """Return the number of listings in the dataset."""
    return len(df)


def get_average_house_age(df: pd.DataFrame) -> float:
    """Return the average age of homes at the time of sale."""
    return df["house_age"].mean()


def get_percent_renovated(df: pd.DataFrame) -> float:
    """Return the percentage of homes that have been renovated."""
    return df["is_renovated"].mean() * 100
