"""
Phase 2 — Machine Learning Pipeline
Trains XGBoost and LightGBM demand forecasting models using the preprocessed
feature dataset from Phase 1 (data_pipeline.py / ProductAnalytics table).
Automatically evaluates both models and selects the best performer.
Stores predictions (7-day, 30-day demand + confidence) in ml_forecasts table.
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app_db import SessionLocal as AppSessionLocal
from app_models import ProductAnalytics, MLForecast, MLModelMeta

# Where trained model artifacts get stored
MODEL_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(MODEL_DIR, exist_ok=True)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def build_training_dataset() -> pd.DataFrame:
    """
    Load the Detailed Time-Series CSV and build a supervised learning dataset.
    Each row represents a (product_id, reference_date) pair with features
    computed from the trailing window and a label = units sold in the next 30 days.
    """
    ts_path = os.path.join(DATA_DIR, "Detailed Time-Series Data.csv")
    print(f"Loading time-series data from {ts_path} ...")

    ts = pd.read_csv(
        ts_path,
        header=None,
        names=["date", "transaction_id", "product_id", "product_name",
               "category", "quantity", "rate", "revenue", "cost", "profit"],
        dtype={"product_id": "Int64"},
        parse_dates=["date"],
        infer_datetime_format=True,
    )

    ts["quantity"] = pd.to_numeric(ts["quantity"], errors="coerce").fillna(0)
    ts["revenue"] = pd.to_numeric(ts["revenue"], errors="coerce").fillna(0)
    ts.dropna(subset=["date", "product_id"], inplace=True)

    # Daily aggregation per product
    daily = (
        ts.groupby(["product_id", ts["date"].dt.date])
        .agg(qty=("quantity", "sum"), rev=("revenue", "sum"))
        .reset_index()
    )
    daily.rename(columns={"date": "sale_date"}, inplace=True)
    daily["sale_date"] = pd.to_datetime(daily["sale_date"])

    # Also bring category — take the mode per product
    cat_map = (
        ts.groupby("product_id")["category"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else "UNKNOWN")
        .reset_index()
        .rename(columns={"category": "category"})
    )
    daily = daily.merge(cat_map, on="product_id", how="left")

    # Rolling window features per product as of each date
    records = []
    cutoff_date = daily["sale_date"].max() - pd.Timedelta(days=30)  # need 30d label

    for pid, grp in daily.groupby("product_id"):
        grp = grp.set_index("sale_date").sort_index()

        # Complete calendar index
        idx = pd.date_range(grp.index.min(), grp.index.max(), freq="D")
        grp = grp.reindex(idx, fill_value=0)
        grp.index.name = "sale_date"

        # Rolling features
        grp["qty_7d"] = grp["qty"].rolling(7, min_periods=1).sum()
        grp["qty_30d"] = grp["qty"].rolling(30, min_periods=1).sum()
        grp["qty_90d"] = grp["qty"].rolling(90, min_periods=1).sum()
        grp["avg_daily_7d"] = grp["qty"].rolling(7, min_periods=1).mean()
        grp["avg_daily_30d"] = grp["qty"].rolling(30, min_periods=1).mean()
        grp["avg_daily_90d"] = grp["qty"].rolling(90, min_periods=1).mean()
        grp["std_7d"] = grp["qty"].rolling(7, min_periods=1).std().fillna(0)
        grp["days_since_sale"] = (grp["qty"] == 0).astype(int).groupby(
            (grp["qty"] != 0).cumsum()
        ).cumcount()

        # Day-of-week & weekend flag
        grp["dow"] = grp.index.dayofweek
        grp["is_weekend"] = (grp["dow"] >= 5).astype(int)
        grp["month"] = grp.index.month
        grp["quarter"] = grp.index.quarter

        # Category encode (simple label)
        cat_val = daily.loc[daily["product_id"] == pid, "category"].mode()
        grp["category_code"] = hash(cat_val.iloc[0]) % 1000 if len(cat_val) > 0 else 0

        # Label: total qty in next 30 days
        grp["label_30d"] = grp["qty"].shift(-30).rolling(30, min_periods=1).sum()
        grp["label_7d"] = grp["qty"].shift(-7).rolling(7, min_periods=1).sum()

        grp = grp.dropna(subset=["label_30d", "label_7d"])
        grp = grp[grp.index <= cutoff_date]  # avoid data leakage
        grp["product_id"] = pid

        records.append(grp.reset_index())

    if not records:
        return pd.DataFrame()

    dataset = pd.concat(records, ignore_index=True)
    print(f"  → Training dataset: {len(dataset):,} rows, {dataset['product_id'].nunique()} products")
    return dataset


def get_feature_cols(dataset: pd.DataFrame):
    drop = {"sale_date", "product_id", "qty", "rev", "label_30d", "label_7d", "category"}
    return [c for c in dataset.columns if c not in drop]


# ---------------------------------------------------------------------------
# Model Training & Evaluation
# ---------------------------------------------------------------------------

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute MAE, RMSE, MAPE."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mask = y_true != 0
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100) if mask.any() else 0.0
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": round(mape, 4)}


def train_and_evaluate(dataset: pd.DataFrame) -> dict:
    """Train XGBoost and LightGBM; return the best model + metrics."""
    from sklearn.model_selection import train_test_split

    feature_cols = get_feature_cols(dataset)
    X = dataset[feature_cols].fillna(0).astype(float)
    y = dataset["label_30d"].fillna(0).astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=True
    )

    results = {}

    # --- XGBoost ---
    try:
        import xgboost as xgb
        print("  Training XGBoost...")
        xgb_model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        preds = xgb_model.predict(X_test)
        metrics = compute_metrics(y_test, preds)
        results["xgboost"] = {"model": xgb_model, **metrics}
        print(f"    XGBoost → MAE={metrics['mae']}, RMSE={metrics['rmse']}, MAPE={metrics['mape']}%")
    except Exception as e:
        print(f"  XGBoost training failed: {e}")

    # --- LightGBM ---
    try:
        import lightgbm as lgb
        print("  Training LightGBM...")
        lgb_model = lgb.LGBMRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        lgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)])
        preds = lgb_model.predict(X_test)
        metrics = compute_metrics(y_test, preds)
        results["lightgbm"] = {"model": lgb_model, **metrics}
        print(f"    LightGBM → MAE={metrics['mae']}, RMSE={metrics['rmse']}, MAPE={metrics['mape']}%")
    except Exception as e:
        print(f"  LightGBM training failed: {e}")

    if not results:
        raise RuntimeError("All model training attempts failed.")

    # Select best by MAE (lower is better)
    best_name = min(results, key=lambda k: results[k]["mae"])
    best = results[best_name]
    print(f"\n  ✅ Best model: {best_name} (MAE={best['mae']})")

    # Save model artifact
    artifact_path = os.path.join(MODEL_DIR, f"{best_name}_demand.pkl")
    joblib.dump(best["model"], artifact_path)
    print(f"  Saved model artifact → {artifact_path}")

    return {
        "best_name": best_name,
        "best_model": best["model"],
        "mae": best["mae"],
        "rmse": best["rmse"],
        "mape": best["mape"],
        "feature_cols": feature_cols,
        "training_rows": len(X_train),
        "all_results": {k: {m: v for m, v in results[k].items() if m != "model"} for k in results},
    }


# ---------------------------------------------------------------------------
# Generate Per-Product Predictions
# ---------------------------------------------------------------------------

def generate_predictions(dataset: pd.DataFrame, model, feature_cols: list, model_name: str, metrics: dict) -> pd.DataFrame:
    """For each product, use the latest feature snapshot to predict demand."""
    # Latest row per product = most recent feature state
    latest = (
        dataset.sort_values("sale_date")
        .groupby("product_id")
        .last()
        .reset_index()
    )

    X_latest = latest[feature_cols].fillna(0).astype(float)

    # 30-day forecast
    forecast_30d = np.clip(model.predict(X_latest), 0, None)

    # 7-day forecast: approximate as 30d * (7/30) with slight noise reduction
    forecast_7d = forecast_30d * (7 / 30)

    # Confidence: based on inverse of normalised MAPE (capped 0.1–0.95)
    mape_val = metrics.get("mape", 50.0)
    base_confidence = max(0.1, min(0.95, 1.0 - (mape_val / 100.0)))

    forecasts = latest[["product_id"]].copy()
    forecasts["forecast_7d"] = np.round(forecast_7d, 2)
    forecasts["forecast_30d"] = np.round(forecast_30d, 2)
    forecasts["confidence"] = round(base_confidence, 4)
    forecasts["model_used"] = model_name
    forecasts["mae"] = metrics["mae"]
    forecasts["rmse"] = metrics["rmse"]
    forecasts["mape"] = metrics["mape"]

    return forecasts


# ---------------------------------------------------------------------------
# Persist Predictions to DB
# ---------------------------------------------------------------------------

def save_forecasts(forecasts: pd.DataFrame, model_meta: dict):
    """Upsert forecasts into ml_forecasts table and record model metadata."""
    db: Session = AppSessionLocal()
    try:
        now = datetime.utcnow()

        # Mark all existing model metas inactive
        db.query(MLModelMeta).update({"is_active": False})

        # Insert new model meta
        meta_record = MLModelMeta(
            model_name=model_meta["best_name"],
            mae=model_meta["mae"],
            rmse=model_meta["rmse"],
            mape=model_meta["mape"],
            is_active=True,
            trained_at=now,
            feature_count=len(model_meta["feature_cols"]),
            training_rows=model_meta["training_rows"],
        )
        db.add(meta_record)

        # Upsert forecasts
        new_count = updated_count = 0
        for _, row in forecasts.iterrows():
            rec = db.query(MLForecast).filter(MLForecast.product_id == int(row["product_id"])).first()
            if not rec:
                rec = MLForecast(product_id=int(row["product_id"]))
                db.add(rec)
                new_count += 1
            else:
                updated_count += 1

            rec.forecast_7d = float(row["forecast_7d"])
            rec.forecast_30d = float(row["forecast_30d"])
            rec.confidence = float(row["confidence"])
            rec.model_used = str(row["model_used"])
            rec.mae = float(row["mae"])
            rec.rmse = float(row["rmse"])
            rec.mape = float(row["mape"])
            rec.predicted_at = now
            rec.last_updated = now

        db.commit()
        print(f"  💾 Forecasts saved: {new_count} new, {updated_count} updated.")
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error saving forecasts: {e}")
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------

def run_ml_pipeline():
    """Full ML pipeline: build dataset → train → evaluate → predict → store."""
    print("\n🤖 Starting ML Pipeline (Phase 2)...")

    # 1. Build dataset
    dataset = build_training_dataset()
    if dataset.empty:
        print("  ⚠️  Empty dataset. Ensure Phase 1 pipeline has run and CSVs are present.")
        return

    # 2. Train & select best model
    model_meta = train_and_evaluate(dataset)

    # 3. Generate per-product predictions
    print("\n  Generating per-product demand forecasts...")
    forecasts = generate_predictions(
        dataset,
        model_meta["best_model"],
        model_meta["feature_cols"],
        model_meta["best_name"],
        {"mae": model_meta["mae"], "rmse": model_meta["rmse"], "mape": model_meta["mape"]},
    )
    print(f"  Generated forecasts for {len(forecasts)} products.")

    # 4. Persist
    save_forecasts(forecasts, model_meta)

    print("\n🎉 ML Pipeline complete!")
    print(f"   Best model : {model_meta['best_name']}")
    print(f"   MAE        : {model_meta['mae']}")
    print(f"   RMSE       : {model_meta['rmse']}")
    print(f"   MAPE       : {model_meta['mape']}%")
    print(f"   Products   : {len(forecasts)}")


if __name__ == "__main__":
    run_ml_pipeline()
