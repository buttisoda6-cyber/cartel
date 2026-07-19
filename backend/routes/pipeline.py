from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app_db import get_app_db
from app_models import MLModelMeta, MLForecast
from pipeline.data_pipeline import run_pipeline
from pipeline.ml_pipeline import run_ml_pipeline

router = APIRouter(
    prefix="/api/pipeline",
    tags=["Pipeline"]
)


def _execute_pipeline():
    try:
        run_pipeline()
    except Exception as e:
        print(f"Data pipeline error: {e}")


def _execute_ml_pipeline():
    try:
        run_ml_pipeline()
    except Exception as e:
        print(f"ML pipeline error: {e}")


@router.post("/run")
def trigger_pipeline(background_tasks: BackgroundTasks):
    """Trigger the Phase 1 data engineering pipeline (background)."""
    try:
        background_tasks.add_task(_execute_pipeline)
        return {"status": "success", "message": "Data engineering pipeline started in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/train")
def trigger_ml_training(background_tasks: BackgroundTasks):
    """Trigger the Phase 2 ML training pipeline (background)."""
    try:
        background_tasks.add_task(_execute_ml_pipeline)
        return {"status": "success", "message": "ML training pipeline started in background. This may take several minutes."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-all")
def trigger_full_pipeline(background_tasks: BackgroundTasks):
    """Trigger Phase 1 data pipeline + Phase 2 ML training sequentially (background)."""
    def _run_all():
        _execute_pipeline()
        _execute_ml_pipeline()
    try:
        background_tasks.add_task(_run_all)
        return {"status": "success", "message": "Full pipeline (data engineering + ML training) started in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/status")
def get_ml_status(app_db: Session = Depends(get_app_db)):
    """Get status of the active ML model and forecast coverage."""
    active_model = app_db.query(MLModelMeta).filter(MLModelMeta.is_active == True).first()
    forecast_count = app_db.query(MLForecast).count()

    if not active_model:
        return {
            "status": "not_trained",
            "message": "No ML model has been trained yet. Use POST /api/pipeline/ml/train to start.",
            "forecast_count": 0
        }

    return {
        "status": "active",
        "model_name": active_model.model_name,
        "mae": active_model.mae,
        "rmse": active_model.rmse,
        "mape": active_model.mape,
        "trained_at": active_model.trained_at,
        "training_rows": active_model.training_rows,
        "feature_count": active_model.feature_count,
        "forecast_count": forecast_count,
    }


@router.get("/ml/forecasts/{product_id}")
def get_product_forecast(product_id: int, app_db: Session = Depends(get_app_db)):
    """Get the ML demand forecast for a specific product."""
    forecast = app_db.query(MLForecast).filter(MLForecast.product_id == product_id).first()
    if not forecast:
        raise HTTPException(status_code=404, detail=f"No forecast found for product {product_id}. Run ML training first.")
    return {
        "product_id": forecast.product_id,
        "forecast_7d": forecast.forecast_7d,
        "forecast_30d": forecast.forecast_30d,
        "confidence": forecast.confidence,
        "model_used": forecast.model_used,
        "mae": forecast.mae,
        "rmse": forecast.rmse,
        "mape": forecast.mape,
        "predicted_at": forecast.predicted_at,
    }

