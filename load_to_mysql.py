import logging
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text


# =====================================================
# STEP 1: CONFIGURE LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("etl_pipeline.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# =====================================================
# STEP 2: LOAD ENVIRONMENT VARIABLES
# =====================================================

load_dotenv()


# =====================================================
# STEP 3: MAIN ETL PIPELINE
# =====================================================

def run_pipeline():

    start_time = time.perf_counter()
    engine = None

    logger.info("=" * 60)
    logger.info("AUTOMATED SALES ETL PIPELINE STARTED")
    logger.info("=" * 60)

    print("\nAUTOMATED SALES ETL PIPELINE")

    try:

        # -------------------------------------------------
        # STEP 1: FIND CLEANED CSV FILE
        # -------------------------------------------------

        logger.info("Step 1: Checking cleaned CSV file")

        input_file = Path("data/cleaned_sales.csv")

        if not input_file.exists():
            raise FileNotFoundError(
                "cleaned_sales.csv not found. Run python etl.py first."
            )

        logger.info("CSV file found: %s", input_file)

        # -------------------------------------------------
        # STEP 2: READ CLEANED DATASET
        # -------------------------------------------------

        logger.info("Step 2: Reading cleaned sales dataset")

        df = pd.read_csv(input_file, encoding="utf-8-sig")

        total_csv_records = len(df)

        logger.info("CSV records loaded: %s", total_csv_records)

        print(f"\nLoaded {total_csv_records} records from CSV.")

        # -------------------------------------------------
        # STEP 3: GET DATABASE CREDENTIALS
        # -------------------------------------------------

        logger.info("Step 3: Reading database configuration")

        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        database = os.getenv("DB_NAME")

        if not all([username, password, host, port, database]):
            raise ValueError(
                "Missing database settings in .env file."
            )

        logger.info("Database configuration loaded")

        # -------------------------------------------------
        # STEP 4: CREATE MYSQL CONNECTION
        # -------------------------------------------------

        logger.info("Step 4: Creating MySQL connection")

        connection_url = URL.create(
            drivername="mysql+mysqlconnector",
            username=username,
            password=password,
            host=host,
            port=int(port),
            database=database
        )

        engine = create_engine(connection_url)

        # -------------------------------------------------
        # STEP 5: TEST DATABASE CONNECTION
        # -------------------------------------------------

        logger.info("Step 5: Testing MySQL connection")

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        logger.info("MySQL connection successful")
        logger.info("Connected database: %s", database)

        print("\nConnected to MySQL successfully!")
        print(f"Database: {database}")

        # -------------------------------------------------
        # STEP 6: CHECK EXISTING FACT RECORDS
        # -------------------------------------------------

        logger.info("Checking existing fact records")

        with engine.connect() as connection:

            existing_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM fact_sales_corrected
                """)
            ).scalar()

        logger.info("Existing fact records: %s", existing_count)

        print(f"Existing fact records: {existing_count}")

        # -------------------------------------------------
        # STEP 7: LOAD DATA INTO STAGING TABLE
        # -------------------------------------------------

        logger.info("Step 7: Loading data into staging table")

        df.to_sql(
            name="cleaned_sales_staging",
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=500
        )

        logger.info("Staging table loaded successfully")

        print("\nStaging table loaded successfully!")

        # -------------------------------------------------
        # STEP 8: VALIDATE DIMENSION MAPPINGS
        # -------------------------------------------------

        logger.info("Step 8: Validating dimension mappings")

        validation_sql = text("""
            SELECT COUNT(*)
            FROM cleaned_sales_staging s

            LEFT JOIN dim_customer dc
                ON s.`Customer ID` = dc.customer_id

            LEFT JOIN dim_product dp
                ON s.`Product ID` = dp.product_id

            LEFT JOIN dim_date dd
                ON DATE(s.`Order Date`) = dd.full_date

            WHERE dc.customer_key IS NULL
               OR dp.product_key IS NULL
               OR dd.date_key IS NULL
        """)

        with engine.connect() as connection:

            unmatched_records = connection.execute(
                validation_sql
            ).scalar()

        logger.info(
            "Unmatched dimension records: %s",
            unmatched_records
        )

        print(f"Unmatched dimension records: {unmatched_records}")

        if unmatched_records > 0:

            raise ValueError(
                "Some records have missing dimension mappings. "
                "Incremental loading stopped."
            )

        logger.info("Dimension mapping validation successful")

        # -------------------------------------------------
        # STEP 9: INCREMENTAL LOADING
        # -------------------------------------------------

        logger.info("Step 9: Starting incremental loading")

        print("\nStarting incremental loading...")

        incremental_sql = text("""
            INSERT INTO fact_sales_corrected (
                row_id,
                order_id,
                customer_key,
                product_key,
                order_date_key,
                sales,
                quantity,
                discount,
                profit
            )

            SELECT
                s.`Row ID`,
                s.`Order ID`,
                dc.customer_key,
                dp.product_key,
                dd.date_key,
                s.Sales,
                s.Quantity,
                s.Discount,
                s.Profit

            FROM cleaned_sales_staging s

            JOIN dim_customer dc
                ON s.`Customer ID` = dc.customer_id

            JOIN dim_product dp
                ON s.`Product ID` = dp.product_id

            JOIN dim_date dd
                ON DATE(s.`Order Date`) = dd.full_date

            LEFT JOIN fact_sales_corrected f
                ON s.`Row ID` = f.row_id

            WHERE f.row_id IS NULL
        """)

        with engine.begin() as connection:

            result = connection.execute(incremental_sql)

            inserted_records = result.rowcount

        logger.info(
            "New fact records inserted: %s",
            inserted_records
        )

        print(f"New fact records inserted: {inserted_records}")

        # -------------------------------------------------
        # STEP 10: VERIFY FINAL RECORDS
        # -------------------------------------------------

        logger.info("Step 10: Verifying final fact records")

        with engine.connect() as connection:

            staging_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM cleaned_sales_staging
                """)
            ).scalar()

            final_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM fact_sales_corrected
                """)
            ).scalar()

            unique_count = connection.execute(
                text("""
                    SELECT COUNT(DISTINCT row_id)
                    FROM fact_sales_corrected
                """)
            ).scalar()

        logger.info("Staging records: %s", staging_count)
        logger.info("Total fact records: %s", final_count)
        logger.info("Unique fact records: %s", unique_count)

        # -------------------------------------------------
        # STEP 11: FINAL REPORT
        # -------------------------------------------------

        execution_time = round(
            time.perf_counter() - start_time, 2
        )

        print("\n========== FINAL REPORT ==========")

        print(f"Staging records: {staging_count}")
        print(f"New records inserted: {inserted_records}")
        print(f"Total fact records: {final_count}")
        print(f"Unique fact records: {unique_count}")
        print(f"Execution time: {execution_time} seconds")

        print("\nETL PIPELINE COMPLETED SUCCESSFULLY!")

        logger.info("ETL pipeline completed successfully")
        logger.info("Execution time: %s seconds", execution_time)

    except Exception:

        logger.exception("ETL PIPELINE FAILED")

        print("\nETL PIPELINE FAILED!")
        print("Check etl_pipeline.log for detailed error information.")

        raise

    finally:

        if engine is not None:
            engine.dispose()
            logger.info("Database engine disposed")

        logger.info("=" * 60)
        logger.info("ETL PIPELINE EXECUTION FINISHED")
        logger.info("=" * 60)


# =====================================================
# STEP 12: EXECUTE PIPELINE
# =====================================================

if __name__ == "__main__":
    run_pipeline()