from getpass import getpass

from sqlalchemy import create_engine, URL, text


# STEP 1: Get MySQL credentials
username = input("MySQL username [root]: ").strip() or "root"
password = getpass("MySQL password: ")


# STEP 2: Configure the database connection
connection_url = URL.create(
    drivername="mysql+mysqlconnector",
    username=username,
    password=password,
    host="localhost",
    port=3306,
    database="sales_db"
)

engine = create_engine(connection_url)


try:
    with engine.connect() as connection:
        print("\nConnected to MySQL successfully!")

        # CHECK 1: Total records
        total_records = connection.execute(
            text("SELECT COUNT(*) FROM cleaned_sales")
        ).scalar_one()

        print(f"\nTotal records: {total_records}")

        # CHECK 2: Missing values in important columns
        result = connection.execute(
            text("""
                SELECT
                    COALESCE(
                        SUM(CASE WHEN Sales IS NULL THEN 1 ELSE 0 END),
                        0
                    ),
                    COALESCE(
                        SUM(CASE WHEN Quantity IS NULL THEN 1 ELSE 0 END),
                        0
                    ),
                    COALESCE(
                        SUM(CASE WHEN Profit IS NULL THEN 1 ELSE 0 END),
                        0
                    )
                FROM cleaned_sales
            """)
        ).one()

        missing_sales = result[0]
        missing_quantity = result[1]
        missing_profit = result[2]

        print("\nMissing-value checks:")
        print(f"Sales: {missing_sales}")
        print(f"Quantity: {missing_quantity}")
        print(f"Profit: {missing_profit}")

        # CHECK 3: Invalid numeric values
        invalid_records = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM cleaned_sales
                WHERE Quantity <= 0
                   OR Sales < 0
            """)
        ).scalar_one()

        print(
            "\nRecords with invalid quantity or sales: "
            f"{invalid_records}"
        )

        # CHECK 4: Overall validation result
        if (
            total_records > 0
            and missing_sales == 0
            and missing_quantity == 0
            and missing_profit == 0
            and invalid_records == 0
        ):
            print("\nRESULT: All data-quality checks passed!")
        else:
            print(
                "\nRESULT: Data-quality issues found. "
                "Review the results."
            )

except Exception as error:
    print("\nValidation failed:", error)

finally:
    engine.dispose()