import os
import psycopg2
from dotenv import load_dotenv, find_dotenv
import logging
import sys

# Configure logging once in your app startup
logging.basicConfig(
    level=logging.INFO,  # you can use DEBUG, WARNING, ERROR too
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # works for local + Azure
    ]
)

logger = logging.getLogger(__name__)
load_dotenv(find_dotenv())
def connect_to_db():
    try:
        # Connect to your postgres DB
        connection = psycopg2.connect(user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"), database=os.getenv("DB_NAME"))
        
        logger.info(connection)
        
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        logger.info(f"Connected to database: {db_version[0]}")
        return cursor, connection
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None
 