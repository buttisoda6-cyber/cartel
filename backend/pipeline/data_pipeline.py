import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app_db import SessionLocal as AppSessionLocal
from app_models import ProductAnalytics

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def load_data():
    """Load the historical CSV data."""
    print("Loading CSV files...")
    
    # 1. Item Sales History.csv
    try:
        sales_history = pd.read_csv(
            os.path.join(DATA_DIR, "Item Sales History.csv"),
            header=None,
            names=["product_id", "product_name", "category", "date", "quantity", "price", "cost"]
        )
        sales_history['date'] = pd.to_datetime(sales_history['date'], errors='coerce')
    except Exception as e:
        print(f"Error loading sales history: {e}")
        sales_history = pd.DataFrame()

    # 2. Detailed Time-Series Data.csv
    try:
        time_series = pd.read_csv(
            os.path.join(DATA_DIR, "Detailed Time-Series Data.csv"),
            header=None,
            names=["date", "transaction_id", "product_id", "product_name", "category", "quantity", "rate", "revenue", "cost", "profit"]
        )
        time_series['date'] = pd.to_datetime(time_series['date'], errors='coerce')
    except Exception as e:
        print(f"Error loading time series: {e}")
        time_series = pd.DataFrame()

    return sales_history, time_series


def process_features(sales_history, time_series):
    """Generate business features for each product."""
    print("Processing business features...")
    if time_series.empty:
        return pd.DataFrame()

    df = time_series.copy()
    
    # Calculate per-product aggregate metrics
    today = df['date'].max() if not df['date'].empty else datetime.now()
    
    # Clean non-numeric values
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0)
    
    product_stats = df.groupby('product_id').agg(
        total_quantity=('quantity', 'sum'),
        total_revenue=('revenue', 'sum'),
        last_sale_date=('date', 'max'),
        first_sale_date=('date', 'min')
    ).reset_index()

    product_stats['days_since_last_sale'] = (today - product_stats['last_sale_date']).dt.days

    product_stats['sales_span_days'] = (product_stats['last_sale_date'] - product_stats['first_sale_date']).dt.days
    product_stats['sales_span_days'] = product_stats['sales_span_days'].clip(lower=1)

    product_stats['average_daily_sales'] = product_stats['total_quantity'] / product_stats['sales_span_days']
    product_stats['average_weekly_sales'] = product_stats['average_daily_sales'] * 7
    product_stats['average_monthly_sales'] = product_stats['average_daily_sales'] * 30
    
    total_store_revenue = product_stats['total_revenue'].sum()
    product_stats['revenue_contribution'] = np.where(
        total_store_revenue > 0, 
        product_stats['total_revenue'] / total_store_revenue, 
        0
    )

    product_stats['sales_velocity'] = product_stats['average_daily_sales']
    
    # Time-based trends
    last_7d = df[df['date'] >= today - timedelta(days=7)]
    last_30d = df[df['date'] >= today - timedelta(days=30)]
    last_90d = df[df['date'] >= today - timedelta(days=90)]
    
    qty_7d = last_7d.groupby('product_id')['quantity'].sum().reset_index().rename(columns={'quantity': 'qty_7d'})
    qty_30d = last_30d.groupby('product_id')['quantity'].sum().reset_index().rename(columns={'quantity': 'qty_30d'})
    qty_90d = last_90d.groupby('product_id')['quantity'].sum().reset_index().rename(columns={'quantity': 'qty_90d'})
    
    product_stats = product_stats.merge(qty_7d, on='product_id', how='left').fillna({'qty_7d': 0})
    product_stats = product_stats.merge(qty_30d, on='product_id', how='left').fillna({'qty_30d': 0})
    product_stats = product_stats.merge(qty_90d, on='product_id', how='left').fillna({'qty_90d': 0})
    
    product_stats['sales_trend_7d'] = (product_stats['qty_7d'] / 7) / (product_stats['average_daily_sales'] + 0.001)
    product_stats['sales_trend_30d'] = (product_stats['qty_30d'] / 30) / (product_stats['average_daily_sales'] + 0.001)
    product_stats['sales_trend_90d'] = (product_stats['qty_90d'] / 90) / (product_stats['average_daily_sales'] + 0.001)

    return product_stats


def save_to_db(product_stats: pd.DataFrame):
    """Save computed features to SQLite analytics table."""
    print("Saving to database...")
    if product_stats.empty:
        print("No stats to save.")
        return

    product_stats = product_stats.replace([np.inf, -np.inf], np.nan)
    product_stats = product_stats.fillna(0)

    db: Session = AppSessionLocal()
    try:
        updated_count = 0
        new_count = 0
        for _, row in product_stats.iterrows():
            record = db.query(ProductAnalytics).filter(ProductAnalytics.product_id == int(row['product_id'])).first()
            if not record:
                record = ProductAnalytics(product_id=int(row['product_id']))
                db.add(record)
                new_count += 1
            else:
                updated_count += 1
            
            record.average_daily_sales = float(row['average_daily_sales'])
            record.average_weekly_sales = float(row['average_weekly_sales'])
            record.average_monthly_sales = float(row['average_monthly_sales'])
            record.sales_velocity = float(row['sales_velocity'])
            record.revenue_contribution = float(row['revenue_contribution'])
            record.days_since_last_sale = int(row['days_since_last_sale'])
            
            record.sales_trend_7d = float(row['sales_trend_7d'])
            record.sales_trend_30d = float(row['sales_trend_30d'])
            record.sales_trend_90d = float(row['sales_trend_90d'])
            
        db.commit()
        print(f"✅ Successfully processed {len(product_stats)} records ({new_count} new, {updated_count} updated).")
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving to DB: {e}")
    finally:
        db.close()


def run_pipeline():
    print("🚀 Starting Data Engineering Pipeline...")
    sales, ts = load_data()
    print(f"Loaded {len(sales)} sales history records, {len(ts)} time-series records.")
    
    stats = process_features(sales, ts)
    if not stats.empty:
        print(f"Computed features for {len(stats)} unique products.")
        save_to_db(stats)
    else:
        print("No features computed, possibly due to empty data.")
    print("🎉 Pipeline finished.")


if __name__ == "__main__":
    run_pipeline()
