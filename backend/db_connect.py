import os
import urllib.parse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "15433")
DB_NAME = os.environ.get("DB_NAME", "Medishopdb")
DB_USER = os.environ.get("DB_USER", "readonly_sanjay")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "readonly@123")

connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={DB_HOST},{DB_PORT};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=30;"
)

connection_url = (
    "mssql+pyodbc:///?odbc_connect="
    + urllib.parse.quote_plus(connection_string)
)

engine = create_engine(
    connection_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=40,
    pool_timeout=60,
)

# Test connection at startup
try:
    with engine.connect():
        print("[INFO] Successfully connected to SQL Server")
except Exception as e:
    print(f"[ERROR] SQL Server connection failed: {e}")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
