"""FastAPI application for Aadhirai Mart."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, SessionLocal, seed_db
from app_db import init_app_db
from routes import products, customers, offers, analytics, broadcasts, posters, activity, images, insights, pipeline, ai, impact, admin_analytics, admin

# Create FastAPI app
app = FastAPI(
    title="Aadhirai Mart API",
    description="Backend API for Aadhirai Mart inventory and donation management system",
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(offers.router)
app.include_router(broadcasts.router)
app.include_router(analytics.router)
app.include_router(posters.router)
app.include_router(activity.router)
app.include_router(admin_analytics.router)
app.include_router(images.router)
app.include_router(insights.router)
app.include_router(pipeline.router)
app.include_router(ai.router)
app.include_router(impact.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup_event():
    init_db()
    db = SessionLocal()

    try:
        seed_db(db)
    finally:
        db.close()
    init_app_db()


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Aadhirai Mart API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Backend is running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
