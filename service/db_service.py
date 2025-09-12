import os
import psycopg2
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
def connect_to_db():
    try:
        # Connect to your postgres DB
        connection = psycopg2.connect(user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"), database=os.getenv("DB_NAME"))
        
        print(connection)
        
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"Connected to database: {db_version[0]}")
        return cursor, connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
 