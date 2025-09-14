import os
import psycopg2
from dotenv import load_dotenv, find_dotenv
import logging
import sys

from opencensus.ext.azure.log_exporter import AzureLogHandler
load_dotenv(find_dotenv())

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Always log to console (local + Azure Log Stream)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console_handler)

# Add Azure Application Insights handler only if connection string is present
app_insights_conn = os.getenv("APP_INSIGHTS_CONNECTION_STRING")
if app_insights_conn:
    azure_handler = AzureLogHandler(connection_string=app_insights_conn)
    azure_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(azure_handler)
def connect_to_db():
    try:
        # Connect to your postgres DB
        connection = psycopg2.connect(user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"), database=os.getenv("DB_NAME"))
        
        # logger.info(connection)
        
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        # logger.info(f"Connected to database: {db_version[0]}")
        return cursor, connection
    except Exception as e:
        logger.info(f"Error connecting to database: {e}")
        return None
 