import pandas as pd
from pathlib import Path

# File paths
data_folder = Path("data")
input_file = data_folder / "sales.csv"
output_file = data_folder / "cleaned_sales.csv"


def run_etl():
    print("=" * 50)
    print("AUTOMATED SALES ETL PIPELINE")
    print("=" * 50)

    # STEP 1: EXTRACT
    print("\nSTEP 1: Extracting data...")

    df = pd.read_csv(input_file, encoding="cp1252")

    original_rows = len(df)
    print(f"Original rows: {original_rows}")

    # STEP 2: TRANSFORM
    print("\nSTEP 2: Cleaning and transforming data...")

    # Remove duplicate records
    duplicates = df.duplicated().sum()
    df = df.drop_duplicates()

    print(f"Duplicate rows removed: {duplicates}")

    # Handle missing values
    missing_before = df.isnull().sum().sum()
    print(f"Missing values before cleaning: {missing_before}")

    # Remove rows where essential fields are missing
    essential_columns = [
        "Order ID",
        "Order Date",
        "Sales",
        "Quantity"
    ]

    available_columns = [
        col for col in essential_columns if col in df.columns
    ]

    df = df.dropna(subset=available_columns)

    # Fill remaining missing text values
    text_columns = df.select_dtypes(
        include=["object", "str"]
    ).columns

    for column in text_columns:
        df[column] = df[column].fillna("Unknown")

    # Convert Order Date to a proper date type
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(
            df["Order Date"],
            errors="coerce"
        )

        df = df.dropna(subset=["Order Date"])

    # Ensure numerical columns contain valid numbers
    for column in ["Sales", "Quantity", "Profit", "Discount"]:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # Remove rows with invalid essential numeric values
    numeric_essential = [
        col for col in ["Sales", "Quantity"]
        if col in df.columns
    ]

    df = df.dropna(subset=numeric_essential)

    # Create a sales category
    if "Sales" in df.columns:
        df["Sales_Category"] = df["Sales"].apply(
            lambda value: (
                "High" if value >= 500
                else "Medium" if value >= 100
                else "Low"
            )
        )

    print(f"Cleaned rows: {len(df)}")
    print(f"Rows removed: {original_rows - len(df)}")

    # STEP 3: LOAD
    print("\nSTEP 3: Saving cleaned data...")

    df.to_csv(output_file, index=False)

    print(f"Cleaned dataset saved to: {output_file}")
    print(f"Final dataset dimensions: {df.shape}")

    print("\nFirst five cleaned rows:")
    print(df.head())

    print("\nETL pipeline completed successfully!")


if __name__ == "__main__":
    run_etl()