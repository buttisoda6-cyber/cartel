import os
from sqlalchemy.engine import URL, create_engine
from sqlalchemy.orm import sessionmaker

connection_url = URL.create(
    "mssql+pyodbc",
    username=os.environ.get("DB_USER", "readonly_sanjay"),
    password=os.environ.get("DB_PASSWORD", "readonly@123"),
    host=os.environ.get("DB_HOST", "100.107.143.8\GFT"),
    port=os.environ.get("DB_PORT"),
    database=os.environ.get("DB_NAME", "Medishopdb"),
    query={
        "driver": "ODBC Driver 17 for SQL Server",
        "TrustServerCertificate": "yes",
        "Connection Timeout": "30",
    },
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
with engine.connect():
    print("[INFO] Successfully connected to SQL Server")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
