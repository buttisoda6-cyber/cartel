"""Database utilities and session management."""
print("reacehd databse.py")
from sqlalchemy.orm import sessionmaker, Session
print("DATABASE: importing db_connect")
from db_connect import engine
print("DATABASE: db_connect imported")

print("DATABASE: importing models")
from models import Base
print("DATABASE: models imported")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables.
    
    Note: Skips table creation since you already have existing tables in SQL Server.
    If you need to create tables, run this separately with a user that has CREATE TABLE permission.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables initialized")
    except Exception as e:
        if "permission denied" in str(e).lower() or "CREATE TABLE" in str(e):
            print("[INFO] Skipping table creation - your user doesn't have CREATE TABLE permission")
            print("[INFO] This is fine! Your existing tables will be used as-is")
        else:
            print(f"[WARN] Database initialization warning: {str(e)}")


def seed_db(db: Session):
    """Skip seeding since you already have existing data in SQL Server.
    
    This function is kept for future use if needed, but won't be called
    since the database already has production data.
    """
    try:
        from models import Product
        
        # Just check if tables are accessible
        product_count = db.query(Product).count()
        print(f"[OK] Database connected successfully! Found {product_count} products")
        return
    except Exception as e:
        print(f"[WARN] Warning checking database: {str(e)}")
