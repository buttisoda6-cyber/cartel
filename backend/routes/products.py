"""Product API routes — three-layer inventory architecture.

Layer 1  get_products_base(db)           SQL Server only — live inventory
Layer 2  attach_basic_status(products)   rule-based status, no SQLite
Layer 3  attach_ai_predictions(products, app_db)  ML enrichment, SQLite only

Fast UI (Stock, Action Center, Offers, …):
    get_products(db)  →  base + basic status

AI Employee:
    get_products_base(db) → attach_ai_predictions(products, app_db)

Endpoints:
    GET /api/products      fast (base + basic status)
    GET /api/ai/products   enriched (base + ML)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, List, Optional
from models import Product, ProductBatch, Category
from schemas import ProductResponse
from database import get_db
from app_db import get_app_db
from app_models import MLForecast, ProductAnalytics
from services.imgbb_service import upload_to_imgbb
import os
from datetime import datetime

router = APIRouter(prefix="/api/products", tags=["products"])

IMGBB_CACHE = {}

GROCERY_CATEGORY_IDS = [1, 291, 267]


def get_product_image_url(product_id: int, name: str, keyword: str) -> str:
    """Gets the ImgBB URL if configured, otherwise returns the fallback Unsplash URL."""
    original_url = f"https://source.unsplash.com/160x160/?{keyword}"

    api_key = os.getenv("IMGBB_API_KEY")
    if not api_key:
        return original_url

    cache_key = f"{product_id}_{keyword}"
    if cache_key in IMGBB_CACHE:
        return IMGBB_CACHE[cache_key]

    imgbb_url = upload_to_imgbb(original_url)
    if imgbb_url:
        IMGBB_CACHE[cache_key] = imgbb_url
        print(f"[INFO] Uploaded product {name} to ImgBB: {imgbb_url}")
        return imgbb_url

    return original_url


def _img_keyword(name: str | None) -> str:
    name_lower = (name or "").lower()
    if "bangle" in name_lower:
        return "bangles"
    if "paper" in name_lower or "roll" in name_lower:
        return "paper,roll"
    if "milk" in name_lower:
        return "milk"
    return "grocery"


def _expiry_days(nearest_expiry) -> int | None:
    if not nearest_expiry:
        return None
    return max(0, (nearest_expiry - datetime.utcnow()).days)


def _base_product_query(db: Session, category: Optional[str] = None):
    query = db.query(
        Product.id.label("id"),
        Product.name.label("name"),
        Product.brand.label("brand"),
        Product.category_id.label("category_id"),
        Product.unit.label("unit"),
        Product.cost_price_fallback.label("cost_price_fallback"),
        Product.barcode_fallback.label("barcode_fallback"),
        Product.hsn_code.label("hsn_code"),
        Product.created_at.label("created_at"),
        Product.availability.label("availability"),
        func.coalesce(func.sum(ProductBatch.stock), 0).label("stock"),
        func.coalesce(func.max(ProductBatch.mrp), Product.cost_price_fallback).label("mrp"),
        func.coalesce(func.max(ProductBatch.purchase_price), Product.cost_price_fallback).label("cost_price"),
        func.max(ProductBatch.barcode).label("barcode"),
        func.min(ProductBatch.expiry_date).label("nearest_expiry"),
        func.max(ProductBatch.batch_no).label("batch_no"),
        func.max(Category.name).label("category_name"),
    ).select_from(Product)\
     .outerjoin(ProductBatch, Product.id == ProductBatch.product_id)\
     .outerjoin(Category, Product.category2_id == Category.id)\
     .group_by(
        Product.id,
        Product.name,
        Product.brand,
        Product.category_id,
        Product.unit,
        Product.cost_price_fallback,
        Product.barcode_fallback,
        Product.hsn_code,
        Product.created_at,
        Product.availability,
    ).order_by(Product.id)

    query = query.filter(Product.category_id.in_(GROCERY_CATEGORY_IDS))

    if category:
        query = query.filter(Category.name == category)

    return query


def _row_to_base_response(p) -> ProductResponse:
    expiry_days = _expiry_days(p.nearest_expiry)
    img_keyword = _img_keyword(p.name)
    resolved_img_url = get_product_image_url(p.id, p.name or "product", img_keyword)

    return ProductResponse(
        id=p.id,
        name=p.name or "Unknown Item",
        brand=p.brand,
        categoryId=p.category_id,
        unit=p.unit or "N",
        mrp=float(p.mrp or 0.0),
        costPrice=float(p.cost_price or 0.0),
        barcode=p.barcode or p.barcode_fallback,
        hsnCode=p.hsn_code,
        taxPercent=5.0,
        isActive=(p.availability == "Y"),
        createdAt=p.created_at,
        category=p.category_name or "General",
        stock=int(p.stock),
        batch=p.batch_no,
        img=resolved_img_url,
        expiryDays=expiry_days,
        weightKg=0.5,
        status=None,
        aiPick=None,
        daysIdle=None,
        healthScore=None,
    )


# ---------------------------------------------------------------------------
# Layer 1 — Base inventory (SQL Server only)
# ---------------------------------------------------------------------------

def get_products_base(
    db: Session,
    category: Optional[str] = None,
    skip: int = 0,
) -> List[ProductResponse]:
    """Return live inventory from SQL Server. No SQLite, no status logic."""
    rows = _base_product_query(db, category).offset(skip).all()
    return [_row_to_base_response(p) for p in rows]


# ---------------------------------------------------------------------------
# Layer 2 — Basic status (no SQLite, no ML)
# ---------------------------------------------------------------------------

def _basic_status(stock: float, expiry_days: int | None) -> str:
    if expiry_days is not None and expiry_days <= 7:
        return "Critical"
    if stock == 0:
        return "Out of Stock"
    if expiry_days is not None and expiry_days <= 30:
        return "Expiring"
    if stock > 100:
        return "Overstock"
    return "Healthy"


def _calculate_basic_health_score(stock: float, expiry_days: int | None) -> float:
    """Simple 0–100 score from stock and expiry only."""
    if stock == 0:
        return 0.0

    score = 100.0

    if expiry_days is not None:
        if expiry_days <= 7:
            score -= 70
        elif expiry_days <= 30:
            score -= 35

    if stock > 100:
        over = min(stock - 100, 200)
        score -= over * 0.15

    if stock <= 5:
        score -= 25
    elif stock <= 15:
        score -= 10

    return round(max(0.0, min(100.0, score)), 2)


def attach_basic_status(products: List[ProductResponse]) -> List[ProductResponse]:
    """Apply rule-based status and health score. No SQLite."""
    enriched: List[ProductResponse] = []
    for p in products:
        stock = float(p.stock or 0)
        expiry = p.expiryDays
        status = _basic_status(stock, expiry)
        health = _calculate_basic_health_score(stock, expiry)
        ai_pick = status in ("Critical", "Expiring", "Out of Stock", "Overstock")
        enriched.append(p.model_copy(update={
            "status": status,
            "healthScore": health,
            "aiPick": ai_pick,
            "daysIdle": 0,
        }))
    return enriched


def get_products(
    db: Session,
    category: Optional[str] = None,
    skip: int = 0,
) -> List[ProductResponse]:
    """Fast path for UI: base inventory + basic status."""
    return attach_basic_status(get_products_base(db, category=category, skip=skip))


# ---------------------------------------------------------------------------
# Layer 3 — AI enrichment (SQLite ML tables)
# ---------------------------------------------------------------------------

def _ml_driven_status(
    stock: float,
    expiry_days: int | None,
    forecast: MLForecast | None,
    analytics: ProductAnalytics | None,
) -> str:
    if stock == 0:
        return "Dead Stock"

    if forecast and forecast.forecast_30d and forecast.forecast_30d > 0:
        daily_demand = forecast.forecast_30d / 30.0
        doi = stock / daily_demand
        if expiry_days is not None:
            doi = min(doi, expiry_days)

        if doi <= 7:
            return "Critical"
        if doi <= 21:
            return "Restock Soon"
        if doi >= 180 and analytics and analytics.days_since_last_sale and analytics.days_since_last_sale > 30:
            return "Dead Stock"
        if doi >= 90:
            return "Overstocked"
        if doi <= 45:
            return "Monitor"
        return "Healthy"

    if analytics and analytics.average_daily_sales and analytics.average_daily_sales > 0:
        doi = stock / analytics.average_daily_sales
        if expiry_days is not None:
            doi = min(doi, expiry_days)
        if doi <= 7:
            return "Critical"
        if doi <= 21:
            return "Restock Soon"
        if doi >= 90:
            return "Overstocked"
        return "Monitor"

    if expiry_days is not None and expiry_days <= 7:
        return "Critical"
    if expiry_days is not None and expiry_days <= 30:
        return "Restock Soon"
    if stock <= 5:
        return "Critical"
    if stock <= 20:
        return "Monitor"
    return "Healthy"


def _calculate_health_score(
    stock: float,
    expiry_days: int | None,
    forecast: MLForecast | None,
    analytics: ProductAnalytics | None,
) -> float:
    score = 100.0

    if stock == 0:
        return 0.0

    doi = None
    if forecast and forecast.forecast_30d and forecast.forecast_30d > 0:
        doi = stock / (forecast.forecast_30d / 30.0)
    elif analytics and analytics.average_daily_sales and analytics.average_daily_sales > 0:
        doi = stock / analytics.average_daily_sales

    if doi is not None:
        if doi <= 7:
            score = 20.0 * (doi / 7.0)
        elif doi <= 14:
            score = 20.0 + 30.0 * ((doi - 7.0) / 7.0)
        elif doi <= 60:
            if doi <= 30:
                score = 50.0 + 50.0 * ((doi - 14.0) / 16.0)
            else:
                score = 100.0 - 20.0 * ((doi - 30.0) / 30.0)
        elif doi <= 120:
            score = 80.0 - 40.0 * ((doi - 60.0) / 60.0)
        else:
            score = max(0.0, 40.0 - 40.0 * ((doi - 120.0) / 60.0))

    if expiry_days is not None:
        if expiry_days <= 7:
            score = min(score, 10.0)
        elif expiry_days <= 30:
            score = min(score, 30.0)
        elif doi is not None and expiry_days < doi:
            score *= 0.5

    if analytics:
        if analytics.sales_trend_30d and analytics.sales_trend_30d < 0.5:
            score *= 0.9
        elif analytics.sales_trend_30d and analytics.sales_trend_30d > 1.5:
            score = min(100.0, score * 1.1)

    if forecast and forecast.confidence and forecast.confidence < 0.5:
        score *= 0.9

    return round(max(0.0, min(100.0, score)), 2)


def attach_ai_predictions(
    products: List[ProductResponse],
    app_db: Session,
) -> List[ProductResponse]:
    """Bulk-load ML tables and replace status/health/forecast fields with AI values."""
    product_ids = [p.id for p in products]
    forecasts: dict[int, MLForecast] = {}
    analytics: dict[int, ProductAnalytics] = {}

    if product_ids:
        for fc in app_db.query(MLForecast).filter(MLForecast.product_id.in_(product_ids)).all():
            forecasts[fc.product_id] = fc
        for an in app_db.query(ProductAnalytics).filter(ProductAnalytics.product_id.in_(product_ids)).all():
            analytics[an.product_id] = an

    enriched: List[ProductResponse] = []
    for p in products:
        stock = float(p.stock or 0)
        expiry = p.expiryDays
        fc = forecasts.get(p.id)
        an = analytics.get(p.id)

        status = _ml_driven_status(stock, expiry, fc, an)
        health = _calculate_health_score(stock, expiry, fc, an)
        ai_pick = status in ("Critical", "Restock Soon", "Dead Stock", "Overstocked")

        days_idle = 0
        if an and an.days_since_last_sale:
            days_idle = int(an.days_since_last_sale)
        elif status == "Dead Stock":
            days_idle = 60
        elif status == "Critical":
            days_idle = 7

        enriched.append(p.model_copy(update={
            "status": status,
            "healthScore": health,
            "aiPick": ai_pick,
            "daysIdle": days_idle,
            "forecast7d": float(fc.forecast_7d) if fc and fc.forecast_7d is not None else None,
            "forecast30d": float(fc.forecast_30d) if fc and fc.forecast_30d is not None else None,
            "confidence": float(fc.confidence) if fc and fc.confidence is not None else None,
            "averageDailySales": float(an.average_daily_sales) if an and an.average_daily_sales is not None else None,
            "salesTrend7d": float(an.sales_trend_7d) if an and an.sales_trend_7d is not None else None,
            "salesTrend30d": float(an.sales_trend_30d) if an and an.sales_trend_30d is not None else None,
            "salesTrend90d": float(an.sales_trend_90d) if an and an.sales_trend_90d is not None else None,
            "categoryTrend": float(an.category_trend) if an and an.category_trend is not None else None,
            "seasonalTrend": float(an.seasonal_trend) if an and an.seasonal_trend is not None else None,
            "weekdayVsWeekendDemand": float(an.weekday_vs_weekend_demand) if an and an.weekday_vs_weekend_demand is not None else None,
            "inventoryTurnover": float(an.inventory_turnover) if an and an.inventory_turnover is not None else None,
            "historicalRestockFrequency": float(an.historical_restock_frequency) if an and an.historical_restock_frequency is not None else None,
            "revenueContribution": float(an.revenue_contribution) if an and an.revenue_contribution is not None else None,
        }))

    return enriched


def _calculate_recommendation_score(
    status: str,
    stock: float,
    health_score: float,
    forecast_7d: float | None,
    forecast_30d: float | None,
    days_since_last_sale: int | None,
    sales_trend_30d: float | None,
    category_trend: float | None,
    expiry_days: int | None,
) -> float:
    score = 0.0
    status_weight = {
        "Critical": 100.0,
        "Restock Soon": 85.0,
        "Dead Stock": 90.0,
        "Overstocked": 75.0,
        "Monitor": 50.0,
        "Healthy": 25.0,
    }
    score += status_weight.get(status, 40.0)
    score += max(0.0, 100.0 - health_score)
    if forecast_7d is not None and stock <= forecast_7d:
        score += 20.0
    if forecast_30d is not None and stock <= forecast_30d:
        score += 10.0
    if days_since_last_sale is not None:
        score += min(25.0, days_since_last_sale / 2.0)
    if sales_trend_30d is not None and sales_trend_30d < 1.0:
        score += (1.0 - sales_trend_30d) * 25.0
    if category_trend is not None and category_trend < 1.0:
        score += (1.0 - category_trend) * 12.0
    if expiry_days is not None and expiry_days <= 14:
        score += 20.0
    return round(score, 2)


def enriched_product_to_snapshot_entry(p: ProductResponse) -> dict[str, Any]:
    """Convert an AI-enriched ProductResponse into the dict shape used by ai_service."""
    stock = float(p.stock or 0)
    forecast_7d = p.forecast7d
    forecast_30d = p.forecast30d
    average_daily_sales = p.averageDailySales or 0.0
    days_since_last_sale = p.daysIdle if p.daysIdle else None
    sales_trend_30d = p.salesTrend30d
    category_trend = p.categoryTrend
    expiry_days = p.expiryDays
    status = p.status or "Healthy"
    health_score = p.healthScore or 0.0

    daily_demand = None
    if forecast_30d and forecast_30d > 0:
        daily_demand = forecast_30d / 30.0
    elif average_daily_sales > 0:
        daily_demand = average_daily_sales

    doi = stock / daily_demand if daily_demand and daily_demand > 0 else None

    reasons: list[str] = []
    if status in {"Critical", "Restock Soon"}:
        if forecast_7d is not None and stock <= forecast_7d:
            reasons.append("7-day forecast exceeds current stock")
        if doi is not None:
            reasons.append(f"Days of inventory remaining: {round(doi, 1)}")
        if days_since_last_sale is not None:
            reasons.append(f"Last sale was {days_since_last_sale} days ago")
    if status in {"Dead Stock", "Overstocked"}:
        if days_since_last_sale is not None:
            reasons.append(f"Very low recent movement, last sale {days_since_last_sale} days ago")
        if forecast_30d is not None:
            reasons.append(f"Forecasted 30-day demand is {round(forecast_30d, 2)} units")
    if status == "Critical" and expiry_days is not None:
        reasons.append(f"Expiry in {expiry_days} days")
    if sales_trend_30d is not None and sales_trend_30d < 1.0:
        reasons.append(f"30-day sales trend is down at {round(sales_trend_30d, 2)}x baseline")
    if category_trend is not None and category_trend < 1.0:
        reasons.append(f"Category trend is weak at {round(category_trend, 2)}x baseline")

    recommended_action = "Monitor"
    if status in {"Critical", "Restock Soon"}:
        recommended_action = "Reorder now"
    elif status in {"Dead Stock", "Overstocked"}:
        recommended_action = "Promote or discount"
    elif status == "Monitor":
        recommended_action = "Watch closely"

    recommendation_score = _calculate_recommendation_score(
        status,
        stock,
        health_score,
        forecast_7d,
        forecast_30d,
        days_since_last_sale,
        sales_trend_30d,
        category_trend,
        expiry_days,
    )

    return {
        "product_id": p.id,
        "product_name": p.name,
        "brand": p.brand,
        "category": p.category or "General",
        "status": status,
        "health_score": health_score,
        "stock": round(stock, 2),
        "current_stock": round(stock, 2),
        "mrp": round(float(p.mrp or 0), 2),
        "purchase_price": round(float(p.costPrice or 0), 2),
        "forecast_7d": round(forecast_7d, 2) if forecast_7d is not None else None,
        "forecast_30d": round(forecast_30d, 2) if forecast_30d is not None else None,
        "confidence": round(p.confidence, 4) if p.confidence is not None else None,
        "average_daily_sales": round(average_daily_sales, 4),
        "days_since_last_sale": days_since_last_sale,
        "days_of_inventory": round(doi, 2) if doi is not None else None,
        "inventory_turnover": round(p.inventoryTurnover, 4) if p.inventoryTurnover is not None else None,
        "historical_restock_frequency": round(p.historicalRestockFrequency, 4) if p.historicalRestockFrequency is not None else None,
        "sales_trend_7d": round(p.salesTrend7d, 4) if p.salesTrend7d is not None else None,
        "sales_trend_30d": round(sales_trend_30d, 4) if sales_trend_30d is not None else None,
        "sales_trend_90d": round(p.salesTrend90d, 4) if p.salesTrend90d is not None else None,
        "category_trend": round(category_trend, 4) if category_trend is not None else None,
        "seasonal_trend": round(p.seasonalTrend, 4) if p.seasonalTrend is not None else None,
        "weekday_vs_weekend_demand": round(p.weekdayVsWeekendDemand, 4) if p.weekdayVsWeekendDemand is not None else None,
        "revenue_contribution": round(p.revenueContribution, 4) if p.revenueContribution is not None else None,
        "expiry_days": expiry_days,
        "recommended_action": recommended_action,
        "recommendation_score": recommendation_score,
        "reasons": reasons[:4],
    }


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = None,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    return get_products(category=category, skip=skip, db=db)


@router.get("/categories", response_model=dict)
def get_categories(db: Session = Depends(get_db)):
    """Get the subcategory names under Groceries for dashboard filtering."""
    return {"categories": [
        "FOODS",
        "HEALTH & BEAUTY",
        "NON - FOOD",
        "FRAGRANCES",
        "COOKING & DINING",
        "KIDS & BABY CARE",
        "BABY ACCESSORIES",
    ]}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID — fast path with basic status."""
    p = _base_product_query(db).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return attach_basic_status([_row_to_base_response(p)])[0]
