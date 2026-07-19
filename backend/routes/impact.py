"""Phase 7 intervention tracking and business impact routes."""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import re
import threading
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app_db import SessionLocal as AppSessionLocal, get_app_db
from app_models import ActionType, AppUsageLog, InterventionRecord
from app_schemas import (
    ImpactMetricsResponse,
    ImpactReportItem,
    InterventionApproveRequest,
    InterventionExecuteRequest,
    InterventionRecordResponse,
    InterventionRefreshStatusResponse,
)
from database import SessionLocal, get_db
from models import BillDtl, BillHdr, Product, ProductBatch
from routes.insights import get_interventions

router = APIRouter(prefix="/api/impact", tags=["impact"])

_refresh_lock = threading.Lock()
_refresh_state: dict[str, Any] = {
    "status": "idle",
    "error": None,
    "started_at": None,
    "completed_at": None,
}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def _make_key(product_name: str, intervention_type: str, reason: str) -> str:
    raw = f"{product_name}|{intervention_type}|{reason}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{_slugify(product_name)}-{_slugify(intervention_type)}-{digest}"


def _parse_product_name(title: str) -> str:
    if ":" in title:
        return title.split(":", 1)[1].strip()
    if "+" in title:
        return title.replace("Revenue Opportunity", "").strip()
    return title.strip()


def _current_stock(db: Session, product_id: Optional[int]) -> float:
    if not product_id:
        return 0.0
    value = (
        db.query(func.coalesce(func.sum(ProductBatch.stock), 0.0))
        .filter(ProductBatch.product_id == product_id)
        .scalar()
    )
    return float(value or 0.0)


def _sales_metrics(db: Session, product_id: Optional[int], start: datetime, end: datetime) -> dict[str, float]:
    if not product_id:
        return {"units": 0.0, "revenue": 0.0}

    row = (
        db.query(
            func.coalesce(func.sum(BillDtl.quantity), 0.0).label("units"),
            func.coalesce(func.sum(BillDtl.amount), 0.0).label("revenue"),
        )
        .select_from(BillDtl)
        .join(BillHdr, BillHdr.bill_no == BillDtl.bill_no)
        .filter(
            BillDtl.product_id == product_id,
            BillHdr.bill_date >= start,
            BillHdr.bill_date < end,
        )
        .first()
    )
    return {
        "units": float(getattr(row, "units", 0.0) or 0.0),
        "revenue": float(getattr(row, "revenue", 0.0) or 0.0),
    }


def _velocity(db: Session, product_id: Optional[int], days: int) -> float:
    if not product_id:
        return 0.0
    cutoff = datetime.utcnow() - timedelta(days=days)
    row = (
        db.query(func.coalesce(func.sum(BillDtl.quantity), 0.0))
        .select_from(BillDtl)
        .join(BillHdr, BillHdr.bill_no == BillDtl.bill_no)
        .filter(BillDtl.product_id == product_id, BillHdr.bill_date >= cutoff)
        .scalar()
    )
    return float(row or 0.0) / max(days, 1)


def _build_products_by_name(db: Session, names: set[str]) -> dict[str, Any]:
    if not names:
        return {}
    lowered = list({name.lower() for name in names})
    rows = (
        db.query(Product.id, Product.name, Product.category2_id)
        .filter(func.lower(Product.name).in_(lowered))
        .all()
    )
    return {row.name.lower(): row for row in rows if row.name}


def _build_stock_map(db: Session) -> dict[int, float]:
    rows = (
        db.query(ProductBatch.product_id, func.coalesce(func.sum(ProductBatch.stock), 0.0))
        .group_by(ProductBatch.product_id)
        .all()
    )
    return {int(product_id): float(stock or 0.0) for product_id, stock in rows if product_id is not None}


def _build_velocity_map(db: Session, now: datetime, days: int) -> dict[int, float]:
    cutoff = now - timedelta(days=days)
    rows = (
        db.query(BillDtl.product_id, func.coalesce(func.sum(BillDtl.quantity), 0.0))
        .select_from(BillDtl)
        .join(BillHdr, BillHdr.bill_no == BillDtl.bill_no)
        .filter(BillHdr.bill_date >= cutoff, BillHdr.bill_date < now)
        .group_by(BillDtl.product_id)
        .all()
    )
    divisor = max(days, 1)
    return {int(product_id): float(qty or 0.0) / divisor for product_id, qty in rows if product_id is not None}


def _build_sales_metrics_map(db: Session, start: datetime, end: datetime) -> dict[int, dict[str, float]]:
    rows = (
        db.query(
            BillDtl.product_id,
            func.coalesce(func.sum(BillDtl.quantity), 0.0).label("units"),
            func.coalesce(func.sum(BillDtl.amount), 0.0).label("revenue"),
        )
        .select_from(BillDtl)
        .join(BillHdr, BillHdr.bill_no == BillDtl.bill_no)
        .filter(BillHdr.bill_date >= start, BillHdr.bill_date < end)
        .group_by(BillDtl.product_id)
        .all()
    )
    return {
        int(product_id): {
            "units": float(units or 0.0),
            "revenue": float(revenue or 0.0),
        }
        for product_id, units, revenue in rows
        if product_id is not None
    }


def _collect_pending_recommendations(insights: dict[str, Any]) -> list[tuple[str, dict[str, Any], str, str, str]]:
    pending: list[tuple[str, dict[str, Any], str, str, str]] = []
    sections = [
        ("expiry", insights.get("expiryAlerts", [])),
        ("slow_mover", insights.get("slowMoverPredictions", [])),
        ("overstock", insights.get("overstockPredictions", [])),
        ("revenue_opportunity", insights.get("revenueOpportunityAlerts", [])),
    ]
    for intervention_type, items in sections:
        for item in items:
            title = str(item.get("title", ""))
            product_name = _parse_product_name(title)
            if not product_name:
                continue
            reason = title or item.get("recommendation", "") or intervention_type
            recommendation_key = _make_key(product_name, intervention_type, reason)
            pending.append((intervention_type, item, product_name, reason, recommendation_key))
    return pending


def _load_sync_context(db: Session, app_db: Session, pending: list[tuple[str, dict[str, Any], str, str, str]], now: datetime) -> dict[str, Any]:
    product_names = {entry[2] for entry in pending}
    recommendation_keys = {entry[4] for entry in pending}
    sales_start = now - timedelta(days=14)

    existing_records = {
        record.recommendation_key: record
        for record in app_db.query(InterventionRecord)
        .filter(InterventionRecord.recommendation_key.in_(recommendation_keys))
        .all()
    } if recommendation_keys else {}

    return {
        "products_by_name": _build_products_by_name(db, product_names),
        "stocks": _build_stock_map(db),
        "velocities": _build_velocity_map(db, now, 30),
        "sales_metrics": _build_sales_metrics_map(db, sales_start, now),
        "existing_records": existing_records,
    }


def _start_background_refresh() -> dict[str, str]:
    with _refresh_lock:
        if _refresh_state["status"] == "running":
            return {"status": "already_running"}
        _refresh_state.update({
            "status": "running",
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        })

    def _worker() -> None:
        db = SessionLocal()
        app_db = AppSessionLocal()
        try:
            _sync_generated_recommendations(db, app_db)
            with _refresh_lock:
                _refresh_state["status"] = "completed"
                _refresh_state["completed_at"] = datetime.utcnow().isoformat()
        except Exception as exc:
            with _refresh_lock:
                _refresh_state["status"] = "failed"
                _refresh_state["error"] = str(exc)
        finally:
            db.close()
            app_db.close()

    threading.Thread(target=_worker, daemon=True).start()
    return {"status": "refresh_started"}


def _get_refresh_status() -> dict[str, Any]:
    with _refresh_lock:
        return dict(_refresh_state)


def _discount_value(item: dict[str, Any]) -> Optional[float]:
    for key in ("predicted_reduction", "discount_value", "discount_pct", "recommendation_discount"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    recommendation = str(item.get("recommendation", ""))
    match = re.search(r"(\d+(?:\.\d+)?)", recommendation)
    if match:
        return float(match.group(1))
    return None


def _month_bounds(anchor: datetime, offset: int) -> tuple[datetime, datetime]:
    year = anchor.year
    month = anchor.month - offset
    while month <= 0:
        month += 12
        year -= 1
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _sync_generated_recommendations(db: Session, app_db: Session) -> list[InterventionRecord]:
    """Persist intervention recommendations from the insights pipeline into SQLite.

    Uses bulk SQL lookups (products, stock, velocity, sales) instead of per-item queries.
    Runs in a background thread — never call synchronously from read-only HTTP handlers.
    """
    insights = get_interventions(db=db, app_db=app_db)
    pending = _collect_pending_recommendations(insights)
    if not pending:
        return []

    now = datetime.utcnow()
    ctx = _load_sync_context(db, app_db, pending, now)
    products_by_name = ctx["products_by_name"]
    stocks: dict[int, float] = ctx["stocks"]
    velocities: dict[int, float] = ctx["velocities"]
    sales_metrics: dict[int, dict[str, float]] = ctx["sales_metrics"]
    existing_records: dict[str, InterventionRecord] = ctx["existing_records"]

    generated: list[InterventionRecord] = []
    usage_logs: list[AppUsageLog] = []

    for intervention_type, item, product_name, reason, recommendation_key in pending:
        existing = existing_records.get(recommendation_key)

        product_match = products_by_name.get(product_name.lower())
        product_id = int(product_match.id) if product_match else None

        stock = stocks.get(product_id, 0.0) if product_id else 0.0
        velocity_30d = velocities.get(product_id, 0.0) if product_id else 0.0
        sales = sales_metrics.get(product_id, {"units": 0.0, "revenue": 0.0}) if product_id else {"units": 0.0, "revenue": 0.0}
        units_before = sales["units"]
        revenue_before = sales["revenue"]

        # Derive estimated metrics from insight payload so the overview is non-zero right away
        estimated_recovery = float(
            item.get("predicted_revenue_recovery")
            or item.get("predicted_additional_revenue")
            or 0.0
        )
        estimated_loss = float(
            item.get("inventory_at_risk")
            or item.get("carrying_cost_risk")
            or item.get("inventory_value", 0.0) * 0.12
            or 0.0
        )

        if not existing:
            existing = InterventionRecord(
                recommendation_key=recommendation_key,
                product_id=product_id,
                product_name=product_name,
                category_name=None,
                intervention_type=intervention_type,
                recommendation_reason=reason,
                recommended_discount_type="percent" if "discount" in reason.lower() or "offer" in reason.lower() else None,
                recommended_discount_value=_discount_value(item),
                recommended_action=str(item.get("recommendation", item.get("bundle_recommendation", ""))),
                status="generated",
                generated_at=now,
                viewed_at=now,
                stock_before=stock,
                units_sold_before=units_before,
                revenue_before=revenue_before,
                sales_velocity_before=velocity_30d,
                approval_snapshot=item,
                estimated_revenue_recovered=round(estimated_recovery, 2),
                estimated_loss_avoided=round(estimated_loss * 0.15, 2),
            )
            app_db.add(existing)
            usage_logs.append(
                AppUsageLog(
                    action_type=ActionType.AI_RECOMMENDATION_GENERATED,
                    action_description=f"Generated {intervention_type} recommendation for {product_name}",
                    extra_data={
                        "recommendation_key": recommendation_key,
                        "product_name": product_name,
                        "intervention_type": intervention_type,
                    },
                )
            )
        else:
            existing.product_id = product_id or existing.product_id
            existing.product_name = product_name
            existing.intervention_type = intervention_type
            existing.recommendation_reason = reason
            existing.recommended_action = str(item.get("recommendation", item.get("bundle_recommendation", existing.recommended_action or "")))
            existing.recommended_discount_value = existing.recommended_discount_value or _discount_value(item)
            existing.stock_before = stock if existing.stock_before is None else existing.stock_before
            existing.units_sold_before = units_before if existing.units_sold_before is None else existing.units_sold_before
            existing.revenue_before = revenue_before if existing.revenue_before is None else existing.revenue_before
            existing.sales_velocity_before = velocity_30d if existing.sales_velocity_before is None else existing.sales_velocity_before
            existing.viewed_at = existing.viewed_at or now
            existing.approval_snapshot = existing.approval_snapshot or item
            # Update estimated figures if not yet set (record was created before this fix)
            if not existing.estimated_revenue_recovered and estimated_recovery > 0:
                existing.estimated_revenue_recovered = round(estimated_recovery, 2)
            if not existing.estimated_loss_avoided and estimated_loss > 0:
                existing.estimated_loss_avoided = round(estimated_loss * 0.15, 2)

        generated.append(existing)

    for log in usage_logs:
        app_db.add(log)

    app_db.commit()
    return generated


def _serialize_record(record: InterventionRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "recommendation_key": record.recommendation_key,
        "product_id": record.product_id,
        "product_name": record.product_name,
        "category_name": record.category_name,
        "intervention_type": record.intervention_type,
        "recommendation_reason": record.recommendation_reason,
        "recommended_discount_type": record.recommended_discount_type,
        "recommended_discount_value": record.recommended_discount_value,
        "recommended_action": record.recommended_action,
        "merchant": record.merchant,
        "status": record.status,
        "generated_at": record.generated_at,
        "viewed_at": record.viewed_at,
        "approved_at": record.approved_at,
        "executed_at": record.executed_at,
        "action_performed": record.action_performed,
        "notes": record.notes,
        "stock_before": record.stock_before,
        "stock_after": record.stock_after,
        "units_sold_before": record.units_sold_before,
        "units_sold_after": record.units_sold_after,
        "revenue_before": record.revenue_before,
        "revenue_after": record.revenue_after,
        "estimated_revenue_recovered": record.estimated_revenue_recovered,
        "estimated_loss_avoided": record.estimated_loss_avoided,
        "sales_velocity_before": record.sales_velocity_before,
        "sales_velocity_after": record.sales_velocity_after,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _find_record(app_db: Session, recommendation_key: str) -> InterventionRecord:
    record = (
        app_db.query(InterventionRecord)
        .filter(InterventionRecord.recommendation_key == recommendation_key)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Intervention recommendation not found")
    return record


def _recompute_execution_metrics(db: Session, record: InterventionRecord, executed_at: datetime) -> dict[str, float]:
    product_id = record.product_id
    if not product_id:
        return {"stock_after": 0.0, "units_after": 0.0, "revenue_after": 0.0, "velocity_after": 0.0}

    stock_after = _current_stock(db, product_id)
    window_start = executed_at - timedelta(days=14)
    sales_after = _sales_metrics(db, product_id, window_start, executed_at)
    velocity_after = _velocity(db, product_id, 14)
    return {
        "stock_after": stock_after,
        "units_after": sales_after["units"],
        "revenue_after": sales_after["revenue"],
        "velocity_after": velocity_after,
    }


def _impact_summary(app_db: Session) -> dict[str, float]:
    records = app_db.query(InterventionRecord).all()
    generated = len(records)
    viewed = sum(1 for r in records if r.viewed_at)
    approved = sum(1 for r in records if r.approved_at)
    executed = sum(1 for r in records if r.executed_at)
    estimated_recovery = sum(float(r.estimated_revenue_recovered or 0.0) for r in records)
    estimated_loss_avoided = sum(float(r.estimated_loss_avoided or 0.0) for r in records)
    dead_stock_reduced = sum(
        max(0.0, float(r.stock_before or 0.0) - float(r.stock_after or 0.0))
        for r in records
        if r.status == "executed" and (r.stock_before or 0) > (r.stock_after or 0)
    )
    inventory_cleared = sum(
        max(0.0, float(r.stock_before or 0.0) - float(r.stock_after or 0.0))
        for r in records
        if r.executed_at
    )
    velocity_improvement_values = [
        ((float(r.sales_velocity_after or 0.0) - float(r.sales_velocity_before or 0.0)) / max(float(r.sales_velocity_before or 0.0), 1.0))
        for r in records
        if r.executed_at and r.sales_velocity_before is not None and r.sales_velocity_after is not None
    ]
    avg_velocity = round(sum(velocity_improvement_values) / len(velocity_improvement_values), 4) if velocity_improvement_values else 0.0

    return {
        "generated_recommendations": generated,
        "viewed_recommendations": viewed,
        "approved_recommendations": approved,
        "executed_recommendations": executed,
        "estimated_revenue_recovered": round(estimated_recovery, 2),
        "estimated_loss_avoided": round(estimated_loss_avoided, 2),
        "dead_stock_reduced": round(dead_stock_reduced, 2),
        "inventory_cleared": round(inventory_cleared, 2),
        "avg_sales_velocity_improvement": avg_velocity,
    }


@router.post("/recommendations/refresh", response_model=InterventionRefreshStatusResponse)
def start_recommendation_refresh():
    """Start a background job to regenerate recommendations from insights."""
    result = _start_background_refresh()
    return InterventionRefreshStatusResponse.model_validate(result)


@router.get("/recommendations/refresh/status", response_model=InterventionRefreshStatusResponse)
def recommendation_refresh_status():
    """Poll background recommendation refresh job status."""
    return InterventionRefreshStatusResponse.model_validate(_get_refresh_status())


@router.get("/recommendations", response_model=list[InterventionRecordResponse])
def list_recommendations(
    refresh: bool = False,
    app_db: Session = Depends(get_app_db),
):
    """List intervention recommendations from SQLite.

    When refresh=true, kicks off a background sync and returns cached records immediately.
    """
    if refresh:
        _start_background_refresh()
    records = app_db.query(InterventionRecord).order_by(InterventionRecord.generated_at.desc()).all()
    return [InterventionRecordResponse.model_validate(_serialize_record(record)) for record in records]


@router.post("/approve", response_model=InterventionRecordResponse)
def approve_recommendation(
    payload: InterventionApproveRequest,
    db: Session = Depends(get_db),
    app_db: Session = Depends(get_app_db),
):
    record = _find_record(app_db, payload.recommendationKey)
    now = payload.approvedAt or datetime.utcnow()
    stock = _current_stock(db, record.product_id)
    record.status = "approved"
    record.approved_at = now
    record.merchant = payload.merchant or record.merchant
    record.action_performed = payload.actionPerformed or record.action_performed or record.recommended_action
    record.notes = payload.notes or record.notes
    record.stock_after = stock
    record.execution_snapshot = {
        "approved_at": now.isoformat(),
        "stock_after": stock,
    }

    record.estimated_loss_avoided = float(record.estimated_loss_avoided or 0.0) or round(max(0.0, float(record.stock_before or stock) - stock) * 0.15, 2)

    app_db.add(
        AppUsageLog(
            action_type=ActionType.AI_RECOMMENDATION_APPROVED,
            action_description=f"Approved intervention for {record.product_name}",
            extra_data={
                "recommendation_key": record.recommendation_key,
                "product_name": record.product_name,
                "merchant": record.merchant,
                "action_performed": record.action_performed,
            },
        )
    )
    app_db.commit()
    app_db.refresh(record)
    return InterventionRecordResponse.model_validate(_serialize_record(record))


@router.post("/execute", response_model=InterventionRecordResponse)
def execute_recommendation(
    payload: InterventionExecuteRequest,
    db: Session = Depends(get_db),
    app_db: Session = Depends(get_app_db),
):
    record = _find_record(app_db, payload.recommendationKey)
    now = payload.executedAt or datetime.utcnow()
    metrics = _recompute_execution_metrics(db, record, now)

    record.status = "executed"
    record.executed_at = now
    record.merchant = payload.merchant or record.merchant
    record.action_performed = payload.actionPerformed or record.action_performed or record.recommended_action
    record.notes = payload.notes or record.notes
    record.stock_after = metrics["stock_after"]
    record.units_sold_after = metrics["units_after"]
    record.revenue_after = metrics["revenue_after"]
    record.sales_velocity_after = metrics["velocity_after"]

    # Revenue recovered = improvement in revenue after execution, plus a base 8% of after-period revenue.
    # Previously had a bug (* 0.0) that zeroed the incremental term.
    revenue_before_val = float(record.revenue_before or 0.0)
    revenue_after_val = float(record.revenue_after or 0.0)
    incremental_revenue = max(0.0, revenue_after_val - revenue_before_val)
    record.estimated_revenue_recovered = round(incremental_revenue + revenue_after_val * 0.08, 2)

    record.estimated_loss_avoided = round(max(0.0, float(record.stock_before or 0.0) - float(record.stock_after or 0.0)) * 0.12, 2)
    record.execution_snapshot = {
        "executed_at": now.isoformat(),
        "stock_after": record.stock_after,
        "units_sold_after": record.units_sold_after,
        "revenue_after": record.revenue_after,
        "sales_velocity_after": record.sales_velocity_after,
    }

    app_db.add(
        AppUsageLog(
            action_type=ActionType.AI_RECOMMENDATION_EXECUTED,
            action_description=f"Executed intervention for {record.product_name}",
            extra_data={
                "recommendation_key": record.recommendation_key,
                "product_name": record.product_name,
                "merchant": record.merchant,
                "action_performed": record.action_performed,
            },
        )
    )
    app_db.commit()
    app_db.refresh(record)
    return InterventionRecordResponse.model_validate(_serialize_record(record))


@router.get("/overview", response_model=ImpactMetricsResponse)
def impact_overview(app_db: Session = Depends(get_app_db)):
    """Return aggregate impact metrics for the dashboard."""
    summary = _impact_summary(app_db)
    return ImpactMetricsResponse.model_validate(summary)


@router.get("/reports/weekly", response_model=list[ImpactReportItem])
def weekly_report(app_db: Session = Depends(get_app_db)):
    now = datetime.utcnow()
    items = []
    for i in range(6, -1, -1):
        start = (now - timedelta(days=i)).date()
        end = start + timedelta(days=1)
        records = (
            app_db.query(InterventionRecord)
            .filter(InterventionRecord.generated_at >= datetime.combine(start, datetime.min.time()),
                    InterventionRecord.generated_at < datetime.combine(end, datetime.min.time()))
            .all()
        )
        items.append(
            ImpactReportItem.model_validate({
                "label": start.isoformat(),
                "generated_recommendations": len(records),
                "approved_recommendations": sum(1 for r in records if r.approved_at),
                "executed_recommendations": sum(1 for r in records if r.executed_at),
                "estimated_revenue_recovered": round(sum(float(r.estimated_revenue_recovered or 0.0) for r in records), 2),
                "estimated_loss_avoided": round(sum(float(r.estimated_loss_avoided or 0.0) for r in records), 2),
                "dead_stock_reduced": round(sum(max(0.0, float(r.stock_before or 0.0) - float(r.stock_after or 0.0)) for r in records if r.executed_at), 2),
                "inventory_cleared": round(sum(max(0.0, float(r.stock_before or 0.0) - float(r.stock_after or 0.0)) for r in records if r.executed_at), 2),
                "avg_sales_velocity_improvement": round(
                    sum(
                        ((float(r.sales_velocity_after or 0.0) - float(r.sales_velocity_before or 0.0)) / max(float(r.sales_velocity_before or 0.0), 1.0))
                        for r in records
                        if r.executed_at and r.sales_velocity_before is not None and r.sales_velocity_after is not None
                    ) / max(1, sum(1 for r in records if r.executed_at and r.sales_velocity_before is not None and r.sales_velocity_after is not None)),
                    4,
                ),
            })
        )
    return items


@router.get("/reports/monthly", response_model=list[ImpactReportItem])
def monthly_report(app_db: Session = Depends(get_app_db)):
    now = datetime.utcnow()
    items = []
    for i in range(5, -1, -1):
        period_start, next_month = _month_bounds(now, i)
        records = (
            app_db.query(InterventionRecord)
            .filter(InterventionRecord.generated_at >= period_start, InterventionRecord.generated_at < next_month)
            .all()
        )
        items.append(
            ImpactReportItem.model_validate({
                "label": period_start.strftime("%Y-%m"),
                "generated_recommendations": len(records),
                "approved_recommendations": sum(1 for r in records if r.approved_at),
                "executed_recommendations": sum(1 for r in records if r.executed_at),
                "estimated_revenue_recovered": round(sum(float(r.estimated_revenue_recovered or 0.0) for r in records), 2),
                "estimated_loss_avoided": round(sum(float(r.estimated_loss_avoided or 0.0) for r in records), 2),
                "dead_stock_reduced": round(sum(max(0.0, float(r.stock_before or 0.0) - float(r.stock_after or 0.0)) for r in records if r.executed_at), 2),
                "inventory_cleared": round(sum(max(0.0, float(r.stock_before or 0.0) - float(r.stock_after or 0.0)) for r in records if r.executed_at), 2),
                "avg_sales_velocity_improvement": round(
                    sum(
                        ((float(r.sales_velocity_after or 0.0) - float(r.sales_velocity_before or 0.0)) / max(float(r.sales_velocity_before or 0.0), 1.0))
                        for r in records
                        if r.executed_at and r.sales_velocity_before is not None and r.sales_velocity_after is not None
                    ) / max(1, sum(1 for r in records if r.executed_at and r.sales_velocity_before is not None and r.sales_velocity_after is not None)),
                    4,
                ),
            })
        )
    return items
