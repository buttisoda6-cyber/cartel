"""Admin API routes for cartel dashboard."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel

from database import get_db
from app_db import get_app_db
from app_models import LoginActivity, Offer, BroadcastLog
from models import Product, BillHdr, BillDtl

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_current_time() -> datetime:
    """Return the live server time so week-based dashboards stay current."""
    return datetime.now()

class ScreenTimeResponse(BaseModel):
    username: str
    screentime_minutes: float
    screentime_hours: float

class ScreenTimeData(BaseModel):
    week_label: str
    start_date: str
    end_date: str
    users: List[ScreenTimeResponse]

class BroadcastPerformanceResponse(BaseModel):
    product_id: int
    product_name: str
    category: str
    this_week_qty: float
    usual_weekly_qty: float
    qty_growth: float
    this_week_rev: float
    usual_weekly_rev: float
    rev_growth: float

class DailySalesResponse(BaseModel):
    day: str
    date: str
    value: float

class OverallSalesData(BaseModel):
    week_label: str
    start_date: str
    end_date: str
    sales: List[DailySalesResponse]

class TrafficPoint(BaseModel):
    hour: int
    time_label: str
    traffic: int

class TrafficPeak(BaseModel):
    time_label: str
    traffic: int
    period: str

class TrafficData(BaseModel):
    week_label: str
    start_date: str
    end_date: str
    points: List[TrafficPoint]
    peaks: List[TrafficPeak]


def _format_hour_label(hour: int) -> str:
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour} {period}"


def _period_of_day(hour: int) -> str:
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Night"


def _hour_distance(a: int, b: int) -> int:
    """Shortest circular distance between two hours on a 24-hour clock."""
    direct = abs(a - b)
    return min(direct, 24 - direct)

@router.get("/screentime", response_model=ScreenTimeData)
def get_user_screentime(
    week_offset: int = Query(0, ge=0),
    app_db: Session = Depends(get_app_db)
):
    """
    Get user screen times for a given week offset.
    week_offset=0: Current week (Sunday to Saturday)
    week_offset=1: Previous week, etc.
    """
    current_date = get_current_time().date()
    days_since_sunday = (current_date.weekday() + 1) % 7
    sunday_of_current_week = current_date - timedelta(days=days_since_sunday)
    
    start_of_week = sunday_of_current_week - timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    
    start_dt = datetime.combine(start_of_week, datetime.min.time())
    end_dt = datetime.combine(end_of_week, datetime.max.time())
    
    week_label = f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"
    
    # Query sessions in this range
    sessions = app_db.query(LoginActivity).filter(
        LoginActivity.login_time >= start_dt,
        LoginActivity.login_time <= end_dt
    ).all()
    
    user_screentime = {}
    for s in sessions:
        login = s.login_time
        logout = s.logout_time
        
        if logout:
            duration = (logout - login).total_seconds() / 60.0
        else:
            # Fallback to standard 30 minutes duration for un-logged out sessions
            duration = 30.0
            
        user_screentime[s.username] = user_screentime.get(s.username, 0.0) + duration
        
    user_list = [
        ScreenTimeResponse(
            username=user,
            screentime_minutes=round(mins, 1),
            screentime_hours=round(mins / 60.0, 2)
        )
        for user, mins in user_screentime.items()
    ]
    
    # Sort by screentime descending
    user_list.sort(key=lambda x: x.screentime_minutes, reverse=True)
    
    return ScreenTimeData(
        week_label=week_label,
        start_date=start_of_week.strftime("%Y-%m-%d"),
        end_date=end_of_week.strftime("%Y-%m-%d"),
        users=user_list
    )


@router.get("/broadcast-performance", response_model=List[BroadcastPerformanceResponse])
def get_broadcast_performance(
    app_db: Session = Depends(get_app_db),
    db: Session = Depends(get_db)
):
    """
    Compare this week's sales of broadcasted products against their historical weekly baseline.
    """
    # Find all product IDs from broadcasted offers
    offers = app_db.query(Offer).filter(Offer.broadcasted == True).all()
    product_codes = set()
    for o in offers:
        try:
            ids = o.product_ids
            if isinstance(ids, list):
                product_codes.update(ids)
        except Exception:
            pass
            
    if not product_codes:
        return []
        
    placeholders = ",".join(str(c) for c in product_codes)
    
    # Query SQL Server for this week's quantity & revenue + 7-month historical total quantity & revenue
    query = f"""
    SELECT 
        itm.MIH_ITEM_CODE AS ItemCode,
        itm.MIH_ITEM_NAME AS ItemName,
        cat.MCD_CAT_NAME AS SubCategoryName,
        
        -- This week (June 21 - June 25, 2026)
        SUM(CASE WHEN bhd.MBH_BILL_DATE >= '2026-06-21 00:00:00' AND bhd.MBH_BILL_DATE <= '2026-06-25 23:59:59' THEN bdt.MBD_ITEM_QTY ELSE 0 END) AS ThisWeekQty,
        SUM(CASE WHEN bhd.MBH_BILL_DATE >= '2026-06-21 00:00:00' AND bhd.MBH_BILL_DATE <= '2026-06-25 23:59:59' THEN bdt.MBD_ITEM_AMOUNT ELSE 0 END) AS ThisWeekRev,
        
        -- Historical 7-month baseline (2025-11-20 to 2026-06-20)
        SUM(CASE WHEN bhd.MBH_BILL_DATE >= '2025-11-20 00:00:00' AND bhd.MBH_BILL_DATE <= '2026-06-20 23:59:59' THEN bdt.MBD_ITEM_QTY ELSE 0 END) AS HistQty,
        SUM(CASE WHEN bhd.MBH_BILL_DATE >= '2025-11-20 00:00:00' AND bhd.MBH_BILL_DATE <= '2026-06-20 23:59:59' THEN bdt.MBD_ITEM_AMOUNT ELSE 0 END) AS HistRev
    FROM 
        MED_BILL_DTL bdt
    INNER JOIN 
        MED_BILL_HDR bhd ON bdt.MBD_BILL_NO = bhd.MBH_BILL_NO
    INNER JOIN 
        med_item_hdr itm ON bdt.MBD_ITEM_CODE = itm.MIH_ITEM_CODE
    LEFT JOIN 
        MED_CATEGORY_DTL cat ON itm.MIH_CATEGORY_2 = cat.MCD_CAT_CODE
    WHERE 
        itm.MIH_ITEM_CODE IN ({placeholders})
    GROUP BY 
        itm.MIH_ITEM_CODE,
        itm.MIH_ITEM_NAME,
        cat.MCD_CAT_NAME
    """
    
    res = db.execute(text(query)).fetchall()
    
    performance_list = []
    for r in res:
        tw_qty = float(r.ThisWeekQty or 0.0)
        tw_rev = float(r.ThisWeekRev or 0.0)
        hist_qty = float(r.HistQty or 0.0)
        hist_rev = float(r.HistRev or 0.0)
        
        # Calculate usual weekly sales (hist_qty in 7 months / 365 * 7)
        usual_weekly_qty = hist_qty / 365.0 * 7.0
        usual_weekly_rev = hist_rev / 365.0 * 7.0
        
        qty_growth = tw_qty - usual_weekly_qty
        rev_growth = tw_rev - usual_weekly_rev
        
        performance_list.append(
            BroadcastPerformanceResponse(
                product_id=r.ItemCode,
                product_name=r.ItemName,
                category=r.SubCategoryName or "FOODS",
                this_week_qty=round(tw_qty, 1),
                usual_weekly_qty=round(usual_weekly_qty, 1),
                qty_growth=round(qty_growth, 1),
                this_week_rev=round(tw_rev, 2),
                usual_weekly_rev=round(usual_weekly_rev, 2),
                rev_growth=round(rev_growth, 2)
            )
        )
        
    # Sort by quantity growth descending
    performance_list.sort(key=lambda x: x.qty_growth, reverse=True)
    return performance_list


@router.get("/overall-sales", response_model=OverallSalesData)
def get_overall_sales(
    week_offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get daily overall sales for Sunday to Saturday for a given week offset.
    Future days are automatically zeroed.
    """
    current_date = get_current_time().date()
    days_since_sunday = (current_date.weekday() + 1) % 7
    sunday_of_current_week = current_date - timedelta(days=days_since_sunday)
    
    start_of_week = sunday_of_current_week - timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    
    week_label = f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"
    
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    sales_list = []
    
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        day_name = day_names[i]
        
        # If in the future relative to current_date, force sales to 0
        if day_date > current_date:
            sales_val = 0.0
        else:
            day_str = day_date.strftime("%Y-%m-%d")
            query = f"""
            SELECT SUM(MBH_BILL_AMOUNT) 
            FROM MED_BILL_HDR 
            WHERE MBH_BILL_DATE >= '{day_str} 00:00:00' 
              AND MBH_BILL_DATE <= '{day_str} 23:59:59'
            """
            sales_val = db.execute(text(query)).scalar() or 0.0
            
        sales_list.append(
            DailySalesResponse(
                day=day_name,
                date=day_date.strftime("%Y-%m-%d"),
                value=float(sales_val)
            )
        )
        
    return OverallSalesData(
        week_label=week_label,
        start_date=start_of_week.strftime("%Y-%m-%d"),
        end_date=end_of_week.strftime("%Y-%m-%d"),
        sales=sales_list
    )


@router.get("/traffic", response_model=TrafficData)
def get_website_traffic(
    week_offset: int = Query(0, ge=0),
    app_db: Session = Depends(get_app_db)
):
    """
    Hourly website traffic pattern for a given week, derived from login activity.
    Traffic = number of overlapping active sessions per hour, aggregated across the week.
    """
    current_date = get_current_time().date()
    days_since_sunday = (current_date.weekday() + 1) % 7
    sunday_of_current_week = current_date - timedelta(days=days_since_sunday)

    start_of_week = sunday_of_current_week - timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    start_dt = datetime.combine(start_of_week, datetime.min.time())
    end_dt = datetime.combine(end_of_week, datetime.max.time())

    week_label = f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"

    sessions = app_db.query(LoginActivity).filter(
        LoginActivity.login_time >= start_dt,
        LoginActivity.login_time <= end_dt
    ).all()

    hourly_counts = [0] * 24
    for session in sessions:
        login = session.login_time
        logout = session.logout_time or (login + timedelta(minutes=30))

        # Clamp to the selected week window before bucketing.
        clamped_start = max(login, start_dt)
        clamped_end = min(logout, end_dt)
        if clamped_end <= clamped_start:
            continue

        cursor = clamped_start
        while cursor < clamped_end:
            hourly_counts[cursor.hour] += 1
            cursor += timedelta(hours=1)
            if cursor - clamped_start > timedelta(hours=48):
                break

    points = [
        TrafficPoint(hour=h, time_label=_format_hour_label(h), traffic=hourly_counts[h])
        for h in range(24)
    ]

    # Pick top peak and next highest peak at least 3 hours away.
    sorted_points = sorted(points, key=lambda point: point.traffic, reverse=True)
    peaks: List[TrafficPeak] = []
    if sorted_points and sorted_points[0].traffic > 0:
        top = sorted_points[0]
        peaks.append(TrafficPeak(
            time_label=top.time_label,
            traffic=top.traffic,
            period=_period_of_day(top.hour)
        ))
        for point in sorted_points[1:]:
            if point.traffic == 0:
                break
            if _hour_distance(point.hour, top.hour) >= 3:
                peaks.append(TrafficPeak(
                    time_label=point.time_label,
                    traffic=point.traffic,
                    period=_period_of_day(point.hour)
                ))
                break

    return TrafficData(
        week_label=week_label,
        start_date=start_of_week.strftime("%Y-%m-%d"),
        end_date=end_of_week.strftime("%Y-%m-%d"),
        points=points,
        peaks=peaks
    )