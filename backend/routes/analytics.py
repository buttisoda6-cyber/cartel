"""Analytics API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Date
from datetime import datetime, timedelta
from typing import List, Optional
from schemas import AnalyticsResponse, DailySalesResponse, PaymentMixResponse, MoverResponse
from models import Product, BillHdr, BillDtl, ProductBatch
from database import get_db
from app_db import get_app_db
from app_models import Offer, BroadcastLog, AppUsageLog, ActionType
from app_schemas import OfferAnalytics, ActivityStats, Last7DaysActivity, BroadcastHistoryItem, AppUsageLogResponse
from routes.products import _calculate_basic_health_score

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    """Get analytics data from production SQL Server database."""
    # Find the maximum billing date to align the last 7 days chart window dynamically
    max_date_row = db.query(func.max(BillHdr.bill_date)).first()
    max_date = max_date_row[0] if max_date_row and max_date_row[0] else datetime.utcnow()
    
    # Calculate start date for 7-day window
    start_date = max_date - timedelta(days=6)
    
    # Query daily sales aggregates
    sales_data = db.query(
        func.cast(BillHdr.bill_date, Date).label("date_val"),
        func.sum(BillHdr.bill_amount).label("total")
    ).filter(BillHdr.bill_date >= start_date)\
     .group_by(func.cast(BillHdr.bill_date, Date))\
     .order_by(func.cast(BillHdr.bill_date, Date)).all()
     
    # Convert dates to weekday names (e.g. Mon, Tue)
    daily_sales = []
    days_map = {}
    for r in sales_data:
        day_name = r.date_val.strftime("%a")
        days_map[day_name] = float(r.total or 0.0)
        
    # Construct complete 7-day list in order
    for i in range(6, -1, -1):
        day_name = (max_date - timedelta(days=i)).strftime("%a")
        value = days_map.get(day_name, 0.0)
        daily_sales.append(DailySalesResponse(day=day_name, value=value))
        
    # Query Payment Mix split percentages
    payments = db.query(
        func.sum(BillHdr.cash_amount).label("cash"),
        func.sum(BillHdr.card_amount).label("card"),
        func.sum(BillHdr.credit_amount).label("credit"),
        func.sum(BillHdr.wallet_amount).label("wallet")
    ).first()
    
    cash_val = float(payments.cash or 0.0) if payments else 0.0
    card_val = float(payments.card or 0.0) if payments else 0.0
    credit_val = float(payments.credit or 0.0) if payments else 0.0
    wallet_val = float(payments.wallet or 0.0) if payments else 0.0
    
    total_payment = cash_val + card_val + credit_val + wallet_val
    if total_payment > 0:
        cash_pct = round((cash_val / total_payment) * 100, 1)
        card_pct = round((card_val / total_payment) * 100, 1)
        credit_pct = round((credit_val / total_payment) * 100, 1)
        wallet_pct = round((wallet_val / total_payment) * 100, 1)
    else:
        # Fallback split
        cash_pct, card_pct, credit_pct, wallet_pct = 40.0, 10.0, 20.0, 30.0
        
    payment_mix = [
        PaymentMixResponse(name="Cash", value=cash_pct, color="oklch(0.32 0.09 150)"),
        PaymentMixResponse(name="Wallet", value=wallet_pct, color="oklch(0.5 0.13 150)"),
        PaymentMixResponse(name="Credit", value=credit_pct, color="oklch(0.72 0.15 75)"),
        PaymentMixResponse(name="Card", value=card_pct, color="oklch(0.7 0.13 150)"),
    ]
    
    # Query Fast Movers (top 5 selling items)
    fast_movers_query = db.query(
        Product.name,
        func.sum(BillDtl.quantity).label("qty")
    ).join(BillDtl, Product.id == BillDtl.product_id)\
     .group_by(Product.name)\
     .order_by(func.sum(BillDtl.quantity).desc())\
     .limit(5).all()
     
    fast_movers = [
        MoverResponse(name=row[0] or "Unknown Product", qty=int(row[1] or 0))
        for row in fast_movers_query
    ]
    
    # Query Slow Movers (lowest selling items, minimum sale > 0)
    slow_movers_query = db.query(
        Product.name,
        func.sum(BillDtl.quantity).label("qty")
    ).join(BillDtl, Product.id == BillDtl.product_id)\
     .group_by(Product.name)\
     .order_by(func.sum(BillDtl.quantity).asc())\
     .limit(5).all()
     
    slow_movers = [
        MoverResponse(name=row[0] or "Unknown Product", qty=int(row[1] or 0))
        for row in slow_movers_query
    ]
    
    # Calculate Store-Wide Inventory Health Score (Phase 3)
    stock_data = db.query(
        ProductBatch.product_id,
        func.sum(ProductBatch.stock).label("stock"),
        func.min(ProductBatch.expiry_date).label("expiry")
    ).group_by(ProductBatch.product_id).all()
    
    inventory_health_score = 0.0
    if stock_data:
        total_score = 0.0
        count = 0
        now = datetime.utcnow()

        for row in stock_data:
            stock = float(row[1] or 0)
            expiry = row[2]

            expiry_days = None
            if expiry:
                if isinstance(expiry, str):
                    try:
                        expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            expiry = datetime.strptime(expiry, "%Y-%m-%d")
                        except ValueError:
                            pass
                if isinstance(expiry, datetime):
                    expiry_days = max(0, (expiry - now).days)
                elif hasattr(expiry, "year"):
                    expiry_days = max(0, (datetime(expiry.year, expiry.month, expiry.day) - now).days)

            score = _calculate_basic_health_score(stock, expiry_days)
            total_score += score
            count += 1

        if count > 0:
            inventory_health_score = round(total_score / count, 1)
    
    return AnalyticsResponse(
        dailySales=daily_sales,
        paymentMix=payment_mix,
        fastMovers=fast_movers,
        slowMovers=slow_movers,
        inventoryHealthScore=inventory_health_score
    )


# ============= OFFER AND BROADCAST ANALYTICS =============


@router.get("/offers/summary", response_model=OfferAnalytics)
def get_offer_analytics(app_db: Session = Depends(get_app_db)):
    """Get comprehensive offer analytics."""
    total_offers = app_db.query(Offer).count()
    total_broadcasts = app_db.query(BroadcastLog).count()
    
    total_customers_reached = app_db.query(
        func.sum(BroadcastLog.customer_count)
    ).scalar() or 0
    
    avg_recipients = 0
    if total_broadcasts > 0:
        avg_recipients = total_customers_reached / total_broadcasts
    
    return OfferAnalytics(
        total_offers_approved=total_offers,
        total_broadcasts_sent=total_broadcasts,
        total_customers_reached=int(total_customers_reached),
        average_recipients_per_broadcast=round(avg_recipients, 2)
    )


@router.get("/offers/feature-usage", response_model=List[ActivityStats])
def get_feature_usage(app_db: Session = Depends(get_app_db)):
    """Get most used features by action type."""
    stats = app_db.query(
        AppUsageLog.action_type,
        func.count(AppUsageLog.id).label("count"),
        func.max(AppUsageLog.created_at).label("last_action")
    ).group_by(AppUsageLog.action_type).all()
    
    return [
        ActivityStats(
            action_type=stat[0],
            count=stat[1],
            last_action=stat[2]
        )
        for stat in stats
    ]


@router.get("/offers/activity/last-7-days", response_model=List[Last7DaysActivity])
def get_last_7_days_activity(app_db: Session = Depends(get_app_db)):
    """Get activity breakdown for the last 7 days."""
    activities = []
    
    for i in range(6, -1, -1):
        date = datetime.utcnow().date() - timedelta(days=i)
        date_start = datetime.combine(date, datetime.min.time())
        date_end = datetime.combine(date, datetime.max.time())
        
        offers_approved = app_db.query(AppUsageLog).filter(
            AppUsageLog.action_type == ActionType.OFFER_APPROVED,
            AppUsageLog.created_at >= date_start,
            AppUsageLog.created_at <= date_end
        ).count()
        
        broadcasts_sent = app_db.query(AppUsageLog).filter(
            AppUsageLog.action_type == ActionType.BROADCAST_SENT,
            AppUsageLog.created_at >= date_start,
            AppUsageLog.created_at <= date_end
        ).count()
        
        activities.append(Last7DaysActivity(
            date=date.strftime("%Y-%m-%d"),
            offers_approved=offers_approved,
            broadcasts_sent=broadcasts_sent
        ))
    
    return activities


@router.get("/offers/history", response_model=List[dict])
def get_offer_approval_history(
    limit: int = Query(50, ge=1, le=500),
    app_db: Session = Depends(get_app_db)
):
    """Get offer approval history with details."""
    offers = app_db.query(Offer).order_by(
        Offer.created_at.desc()
    ).limit(limit).all()
    
    history = []
    for offer in offers:
        broadcast_count = app_db.query(BroadcastLog).filter(
            BroadcastLog.offer_id == offer.id
        ).count()
        
        total_recipients = app_db.query(
            func.sum(BroadcastLog.customer_count)
        ).filter(BroadcastLog.offer_id == offer.id).scalar() or 0
        
        history.append({
            "id": offer.id,
            "product_names": offer.product_names,
            "discount_type": offer.discount_type,
            "discount_value": offer.discount_value,
            "valid_from": offer.valid_from,
            "valid_to": offer.valid_to,
            "created_at": offer.created_at,
            "status": offer.status,
            "broadcast_count": broadcast_count,
            "total_recipients": int(total_recipients)
        })
    
    return history


@router.get("/broadcasts/history", response_model=List[dict])
def get_broadcast_history(
    limit: int = Query(50, ge=1, le=500),
    app_db: Session = Depends(get_app_db)
):
    """Get broadcast history with details."""
    broadcasts = app_db.query(BroadcastLog).order_by(
        BroadcastLog.sent_at.desc()
    ).limit(limit).all()
    
    history = []
    for broadcast in broadcasts:
        offer = app_db.query(Offer).filter(Offer.id == broadcast.offer_id).first()
        
        history.append({
            "id": broadcast.id,
            "offer_id": broadcast.offer_id,
            "offer_products": offer.product_names if offer else [],
            "customer_count": broadcast.customer_count,
            "status": broadcast.status,
            "sent_at": broadcast.sent_at,
            "scheduled_at": broadcast.scheduled_at
        })
    
    return history


@router.get("/activity/recent", response_model=List[AppUsageLogResponse])
def get_recent_activity(
    action_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    app_db: Session = Depends(get_app_db)
):
    """Get recent activity logs with optional filtering by action type."""
    query = app_db.query(AppUsageLog)
    
    if action_type:
        query = query.filter(AppUsageLog.action_type == action_type)
    
    return query.order_by(AppUsageLog.created_at.desc()).limit(limit).all()
