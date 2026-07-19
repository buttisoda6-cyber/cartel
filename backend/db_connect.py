import os
from sqlalchemy.engine import URL, create_engine
from sqlalchemy.orm import sessionmaker

connection_url = URL.create(
    "mssql+pyodbc",
    username=os.environ.get("DB_USER", "admin_readonly"),
    password=os.environ.get("DB_PASSWORD", "readonly@123"),
    host=os.environ.get("DB_HOST", "127.0.0.1"),
    port=os.environ.get("DB_PORT"),
    database=os.environ.get("DB_NAME", "aadhirai_mart"),
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


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
