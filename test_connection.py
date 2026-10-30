import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

try:
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT"))
    )

    if connection.is_connected():
        print("SUCCESS: Connected to MySQL!")
        print("Database: sales_db")

    connection.close()

except mysql.connector.Error as error:
    print("MySQL connection failed:", error)