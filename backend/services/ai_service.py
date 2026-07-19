"""AI Service for Retrieval-Augmented Generation using Gemini."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import Date, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _question_intent(question: str) -> str:
    text = question.lower()
    intent_map = [
        ("morning_brief", ["morning brief", "today's inventory health", "store health summary", "summarize today's inventory health"]),
        ("end_of_day", ["end of day", "end-of-day", "today's review", "review today"]),
        ("reorder", ["reorder", "restock", "buy today", "need to order", "what products should i reorder"]),
        ("out_of_stock_next_week", ["go out of stock", "stock out", "out of stock next week", "run out next week"]),
        ("promotion", ["promot", "discount", "offer", "clear stock", "dead stock", "what items should be promoted"]),
        ("critical_reason", ["why is this product marked critical", "why critical", "why is it critical"]),
        ("category_performance", ["underperforming categories", "category performance", "which categories are underperforming"]),
        ("month_comparison", ["compare this month with last month", "this month with last month", "month over month", "month comparison"]),
        ("dead_stock", ["dead stock", "becoming dead stock", "what is dead stock"]),
    ]
    for intent, keywords in intent_map:
        if any(keyword in text for keyword in keywords):
            return intent
    return "general"


def _days_between(later: datetime | None, earlier: datetime | None) -> int | None:
    if not later or not earlier:
        return None
    later_date = later.date() if hasattr(later, "date") else later
    earlier_date = earlier.date() if hasattr(earlier, "date") else earlier
    try:
        return max(0, (later_date - earlier_date).days)
    except TypeError:
        return None


def _product_name(row: Any) -> str:
    return getattr(row, "name", None) or getattr(row, "product_name", None) or "Unknown Item"


def _build_month_window(anchor: datetime) -> tuple[datetime, datetime, datetime, datetime]:
    current_start = datetime(anchor.year, anchor.month, 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = datetime(previous_end.year, previous_end.month, 1)
    next_month = (current_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return current_start, next_month, previous_start, current_start


def _sql_schema_reference() -> str:
    return """
SQL SERVER TABLES
- med_item_hdr(MIH_ITEM_CODE, MIH_ITEM_NAME, mih_item_name_short, MIH_CATEGORY_1, MIH_CATEGORY_2, mih_unit, MIH_PUR_PRICE, MIH_EANCODE, MIH_HSN_CODE, MIH_CREATED_DATE, MIH_AVAILABILITY)
- MED_ITEM_DTL(mid_row_id, MID_ITEM_CODE, MID_BAL_STOCK, MID_EXPIRY_DT, MID_BATCH_NO, MID_MRP, MID_PUR_PRICE, mid_unique_Barcode, MID_SALE_TAX_PERC)
- MED_CATEGORY_DTL(MCD_CAT_CODE, MCD_CAT_NAME, MCD_CAT_ANAME, MCD_Active)
- MED_CUSTOMER_MAST(MCM_CUST_CODE, MCM_CUST_NAME, mcm_phone2, MCM_CUST_TEL, MCM_CUST_CREDIT_BAL, MCM_CUST_CREDIT_LIMIT, MCM_CUST_ADDR1, mcm_loyalty_allowed, MCM_CUST_STATUS, MCM_CREATED_DT_TIME)
- MED_BILL_HDR(MBH_BILL_NO, MBH_BILL_DATE, MBH_BILL_AMOUNT, MBH_BILL_CUST_CODE, MBH_BILL_CUST_NAME, MBH_CASH_AMT, MBH_CARD_AMT, MBH_CREDIT_AMT, mbh_wallet_amt, MBH_PROFIT)
- MED_BILL_DTL(mbd_item_rowid, MBD_BILL_NO, MBD_ITEM_CODE, MBD_ITEM_QTY, MBD_ITEM_RATE, MBD_ITEM_AMOUNT, MBD_PUR_RATE, mbd_profit_amt, mbd_eancode)

SQLITE TABLES
- offers(id, product_ids, product_names, discount_type, discount_value, valid_from, valid_to, status, broadcasted, created_at)
- broadcast_logs(id, offer_id, customer_count, status, sent_at, scheduled_at, created_at)
- broadcast_recipients(id, broadcast_log_id, customer_id, customer_name, phone_number, sent_status, sent_at, created_at)
- app_usage_logs(id, action_type, action_description, offer_id, broadcast_log_id, extra_data, created_at)
- login_activity(id, user_id, username, login_time, logout_time, ip_address, device_info)
- product_analytics(id, product_id, average_daily_sales, average_weekly_sales, average_monthly_sales, sales_velocity, revenue_contribution, days_since_last_sale, inventory_turnover, current_stock, days_of_inventory, historical_restock_frequency, sales_trend_7d, sales_trend_30d, sales_trend_90d, category_trend, seasonal_trend, weekday_vs_weekend_demand, last_updated)
- ml_forecasts(id, product_id, forecast_7d, forecast_30d, confidence, model_used, mae, rmse, mape, predicted_at, last_updated)
- ml_model_meta(id, model_name, mae, rmse, mape, is_active, trained_at, feature_count, training_rows)
- ai_conversations(id, user_query, ai_response, context_snapshot, created_at)
"""


def _guess_sql_source(question: str) -> str:
    text_q = question.lower()
    sqlite_keywords = [
        "offer",
        "broadcast",
        "recipient",
        "activity",
        "login",
        "conversation",
        "session",
        "campaign",
    ]
    if any(keyword in text_q for keyword in sqlite_keywords):
        return "sqlite"
    return "sqlserver"


def _extract_json_blob(text_value: str) -> dict[str, Any]:
    cleaned = text_value.strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def _validate_sql_query(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    lowered = cleaned.lower()
    forbidden = [
        " insert ",
        " update ",
        " delete ",
        " drop ",
        " alter ",
        " truncate ",
        " merge ",
        " exec ",
        " execute ",
        " grant ",
        " revoke ",
    ]
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    if ";" in cleaned:
        raise ValueError("Only single-statement SQL queries are allowed.")
    if any(token in f" {lowered} " for token in forbidden):
        raise ValueError("Mutating SQL statements are not allowed.")
    if "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise ValueError("SQL comments are not allowed.")
    return cleaned


def _rows_to_dicts(rows: list[Any], columns: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if hasattr(row, "_mapping"):
            mapping = dict(row._mapping)
        elif isinstance(row, dict):
            mapping = dict(row)
        else:
            mapping = {columns[i]: row[i] for i in range(min(len(columns), len(row)))}
        out.append(_to_jsonable(mapping))
    return out


def _sql_agent_prompt(question: str, source_db: str) -> str:
    db_name = "SQL Server" if source_db == "sqlserver" else "SQLite"
    return f"""
You are the SQL Agent for Aadhirai Mart.

Return a single JSON object with these keys:
- source_db: "{source_db}"
- sql: the read-only SQL query to execute against {db_name}
- explanation: a short business explanation of what the query returns
- limit_applied: true or false

Rules:
- Use only SELECT or WITH queries.
- Do not modify data.
- Prefer clear aggregations and filters.
- If the question asks for a list, use a sensible limit of 50 rows or fewer.
- If the question needs inventory or sales data, use SQL Server tables.
- If the question needs offers, broadcasts, activity, or sessions, use SQLite tables.
- Use the schema below only.

Question: {question}

Schema:
{_sql_schema_reference()}
"""


def run_sql_agent(question: str, db: Session, app_db: Session) -> dict[str, Any]:
    """Generate and execute a safe read-only SQL query."""
    if not model:
        return {
            "error": "GEMINI_API_KEY is missing or invalid. Please check your backend configuration.",
            "generated_at": datetime.utcnow().isoformat(),
        }

    source_db = _guess_sql_source(question)
    prompt = _sql_agent_prompt(question, source_db)

    try:
        response = model.generate_content(prompt)
        payload = _extract_json_blob(response.text or "{}")
    except Exception as e:
        return {
            "error": f"SQL agent failed to generate a query: {str(e)}",
            "generated_at": datetime.utcnow().isoformat(),
        }

    sql_text = str(payload.get("sql", "")).strip()
    try:
        sql_text = _validate_sql_query(sql_text)
    except ValueError as e:
        return {
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat(),
            "source_db": source_db,
            "sql": sql_text,
            "explanation": payload.get("explanation", ""),
        }

    session = db if str(payload.get("source_db", source_db)).lower() != "sqlite" else app_db

    try:
        result = session.execute(text(sql_text))
        columns = list(result.keys())
        rows = result.fetchall()
        rows = rows[:50]
        row_dicts = _rows_to_dicts(rows, columns)
    except SQLAlchemyError as e:
        return {
            "error": f"SQL execution failed: {str(e)}",
            "generated_at": datetime.utcnow().isoformat(),
            "source_db": source_db,
            "sql": sql_text,
            "explanation": payload.get("explanation", ""),
        }

    summary = {
        "row_count": len(row_dicts),
        "columns": columns,
    }

    return {
        "source_db": "sqlite" if session is app_db else "sqlserver",
        "sql": sql_text,
        "explanation": payload.get("explanation", ""),
        "limit_applied": bool(payload.get("limit_applied", False)),
        "generated_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "rows": row_dicts,
    }


def _load_inventory_snapshot(db: Session, app_db: Session, question: str, report_type: str = "chat") -> dict[str, Any]:
    from models import BillDtl, BillHdr, Category, Product, ProductBatch
    from app_models import MLModelMeta, Offer, BroadcastLog
    from routes.products import get_products_base, attach_ai_predictions, enriched_product_to_snapshot_entry

    intent = _question_intent(question)
    now = datetime.utcnow()
    current_start, next_month, previous_start, previous_end = _build_month_window(now)
    last_30_days = now - timedelta(days=30)
    previous_30_days = now - timedelta(days=60)
    last_7_days = now - timedelta(days=7)

    active_model = app_db.query(MLModelMeta).filter(MLModelMeta.is_active.is_(True)).first()
    active_offers = app_db.query(Offer).filter(Offer.status == "approved").count()
    total_broadcasts = app_db.query(BroadcastLog).count()

    current_month_row = db.query(
        func.coalesce(func.sum(BillHdr.bill_amount), 0.0).label("revenue"),
        func.coalesce(func.count(BillHdr.bill_no), 0).label("bills"),
        func.coalesce(func.sum(BillHdr.profit), 0.0).label("profit"),
    ).filter(BillHdr.bill_date >= current_start, BillHdr.bill_date < next_month).first()
    previous_month_row = db.query(
        func.coalesce(func.sum(BillHdr.bill_amount), 0.0).label("revenue"),
        func.coalesce(func.count(BillHdr.bill_no), 0).label("bills"),
        func.coalesce(func.sum(BillHdr.profit), 0.0).label("profit"),
    ).filter(BillHdr.bill_date >= previous_start, BillHdr.bill_date < previous_end).first()

    total_inventory_stock_row = db.query(func.coalesce(func.sum(ProductBatch.stock), 0.0)).scalar()
    total_inventory_stock = _safe_float(total_inventory_stock_row)

    enriched_products = attach_ai_predictions(get_products_base(db), app_db)

    reorder_candidates: list[dict[str, Any]] = []
    promotion_candidates: list[dict[str, Any]] = []
    dead_stock_candidates: list[dict[str, Any]] = []
    expiring_candidates: list[dict[str, Any]] = []
    underperforming_categories: list[dict[str, Any]] = []

    store_health_total = 0.0
    store_health_count = 0

    for product in enriched_products:
        detail = enriched_product_to_snapshot_entry(product)
        status = detail["status"]
        store_health_total += detail["health_score"]
        store_health_count += 1

        forecast_7d = detail.get("forecast_7d")
        stock = detail["stock"]
        days_since_last_sale = detail.get("days_since_last_sale")
        sales_trend_30d = detail.get("sales_trend_30d")
        expiry_days = detail.get("expiry_days")

        if status in {"Critical", "Restock Soon"} or (forecast_7d is not None and stock <= forecast_7d):
            reorder_candidates.append(detail)
        if status in {"Dead Stock", "Overstocked"} or (sales_trend_30d is not None and sales_trend_30d < 0.8):
            promotion_candidates.append(detail)
        if status == "Dead Stock" or (days_since_last_sale is not None and days_since_last_sale >= 60):
            dead_stock_candidates.append(detail)
        if expiry_days is not None and expiry_days <= 30:
            expiring_candidates.append(detail)

    store_health_score = round(store_health_total / store_health_count, 1) if store_health_count else 0.0

    reorder_candidates = sorted(reorder_candidates, key=lambda item: (item["recommendation_score"], -item["health_score"]), reverse=True)
    promotion_candidates = sorted(promotion_candidates, key=lambda item: (item["recommendation_score"], -item["health_score"]), reverse=True)
    dead_stock_candidates = sorted(dead_stock_candidates, key=lambda item: (item["recommendation_score"], -item["health_score"]), reverse=True)
    expiring_candidates = sorted(expiring_candidates, key=lambda item: (item["expiry_days"] or 9999, -item["recommendation_score"]))

    category_rows = (
        db.query(
            Category.name.label("category_name"),
            func.sum(BillDtl.quantity).label("quantity"),
            func.sum(BillDtl.amount).label("revenue"),
        )
        .select_from(BillDtl)
        .join(BillHdr, BillHdr.bill_no == BillDtl.bill_no)
        .join(Product, Product.id == BillDtl.product_id)
        .outerjoin(Category, Product.category2_id == Category.id)
        .filter(BillHdr.bill_date >= last_30_days)
        .group_by(Category.name)
        .all()
    )
    previous_category_rows = (
        db.query(
            Category.name.label("category_name"),
            func.sum(BillDtl.quantity).label("quantity"),
            func.sum(BillDtl.amount).label("revenue"),
        )
        .select_from(BillDtl)
        .join(BillHdr, BillHdr.bill_no == BillDtl.bill_no)
        .join(Product, Product.id == BillDtl.product_id)
        .outerjoin(Category, Product.category2_id == Category.id)
        .filter(
            BillHdr.bill_date >= previous_30_days,
            BillHdr.bill_date < last_30_days,
        )
        .group_by(Category.name)
        .all()
    )

    previous_category_map = {(row.category_name or "General"): row for row in previous_category_rows}
    for row in category_rows:
        category_name = row.category_name or "General"
        previous_row = previous_category_map.get(category_name)
        current_revenue = _safe_float(row.revenue)
        previous_revenue = _safe_float(previous_row.revenue) if previous_row else 0.0
        growth = None
        if previous_revenue > 0:
            growth = (current_revenue - previous_revenue) / previous_revenue
        elif current_revenue > 0:
            growth = 1.0

        underperforming_categories.append(
            {
                "category": category_name,
                "current_30d_revenue": round(current_revenue, 2),
                "previous_30d_revenue": round(previous_revenue, 2),
                "growth_rate": round(growth, 4) if growth is not None else None,
                "30d_quantity": round(_safe_float(row.quantity), 2),
            }
        )

    underperforming_categories = sorted(
        underperforming_categories,
        key=lambda item: (
            item["growth_rate"] if item["growth_rate"] is not None else -9_999,
            -item["current_30d_revenue"],
        ),
    )

    rolling_30d_sales_row = db.query(
        func.coalesce(func.sum(BillHdr.bill_amount), 0.0).label("revenue"),
        func.coalesce(func.count(BillHdr.bill_no), 0).label("bills"),
        func.coalesce(func.sum(BillHdr.profit), 0.0).label("profit"),
    ).filter(BillHdr.bill_date >= last_30_days, BillHdr.bill_date < now).first()

    current_revenue = _safe_float(getattr(current_month_row, "revenue", 0.0))
    previous_revenue = _safe_float(getattr(previous_month_row, "revenue", 0.0))
    revenue_growth = None
    if previous_revenue > 0:
        revenue_growth = (current_revenue - previous_revenue) / previous_revenue
    elif current_revenue > 0:
        revenue_growth = 1.0

    recent_daily_sales = (
        db.query(
            func.cast(BillHdr.bill_date, Date).label("sale_date"),
            func.coalesce(func.sum(BillHdr.bill_amount), 0.0).label("revenue"),
            func.coalesce(func.count(BillHdr.bill_no), 0).label("bills"),
        )
        .filter(BillHdr.bill_date >= last_7_days)
        .group_by(func.cast(BillHdr.bill_date, Date))
        .order_by(func.cast(BillHdr.bill_date, Date))
        .all()
    )

    recent_activity = (
        app_db.query(BroadcastLog)
        .order_by(BroadcastLog.sent_at.desc())
        .limit(5)
        .all()
    )

    top_reorder = reorder_candidates[:8]
    top_promotions = promotion_candidates[:8]
    top_dead_stock = dead_stock_candidates[:8]
    top_expiring = expiring_candidates[:8]

    focus_by_intent = {
        "reorder": top_reorder,
        "out_of_stock_next_week": top_reorder,
        "promotion": top_promotions,
        "dead_stock": top_dead_stock,
        "critical_reason": top_reorder,
        "category_performance": underperforming_categories[:6],
        "month_comparison": underperforming_categories[:6],
        "morning_brief": top_reorder + top_promotions,
        "end_of_day": top_reorder + top_promotions,
        "general": top_reorder[:4] + top_promotions[:4],
    }

    snapshot = {
        "generated_at": now,
        "report_type": report_type,
        "question": question,
        "intent": intent,
        "store_overview": {
            "health_score": store_health_score,
            "active_model": {
                "name": getattr(active_model, "model_name", None),
                "mae": getattr(active_model, "mae", None),
                "rmse": getattr(active_model, "rmse", None),
                "mape": getattr(active_model, "mape", None),
                "trained_at": getattr(active_model, "trained_at", None),
            } if active_model else None,
            "active_offers": active_offers,
            "broadcasts_sent": total_broadcasts,
            "inventory_units": round(total_inventory_stock, 2),
            "current_month_revenue": round(current_revenue, 2),
            "previous_month_revenue": round(previous_revenue, 2),
            "revenue_growth_rate": round(revenue_growth, 4) if revenue_growth is not None else None,
            "current_month_bills": _safe_int(getattr(current_month_row, "bills", 0)),
            "previous_month_bills": _safe_int(getattr(previous_month_row, "bills", 0)),
            "rolling_30d_revenue": round(_safe_float(getattr(rolling_30d_sales_row, "revenue", 0.0)), 2),
        },
        "month_comparison": {
            "current_month": {
                "revenue": round(current_revenue, 2),
                "bills": _safe_int(getattr(current_month_row, "bills", 0)),
            },
            "previous_month": {
                "revenue": round(previous_revenue, 2),
                "bills": _safe_int(getattr(previous_month_row, "bills", 0)),
            },
            "growth_rate": round(revenue_growth, 4) if revenue_growth is not None else None,
        },
        "daily_sales_last_7_days": [
            {
                "date": row.sale_date.isoformat() if hasattr(row.sale_date, "isoformat") else str(row.sale_date),
                "revenue": round(_safe_float(row.revenue), 2),
                "bills": _safe_int(row.bills),
            }
            for row in recent_daily_sales
        ],
        "focus_items": _to_jsonable(focus_by_intent.get(intent, focus_by_intent["general"])),
        "reorder_candidates": _to_jsonable(top_reorder),
        "promotion_candidates": _to_jsonable(top_promotions),
        "dead_stock_candidates": _to_jsonable(top_dead_stock),
        "expiring_candidates": _to_jsonable(top_expiring),
        "underperforming_categories": _to_jsonable(underperforming_categories[:8]),
        "recent_activity": [
            {
                "broadcast_id": activity.id,
                "offer_id": activity.offer_id,
                "customer_count": activity.customer_count,
                "status": activity.status,
                "sent_at": activity.sent_at,
            }
            for activity in recent_activity
        ],
    }

    return snapshot


def _render_context_snapshot(snapshot: dict[str, Any]) -> str:
    lines: list[str] = []
    overview = snapshot["store_overview"]

    lines.append("STORE OVERVIEW")
    lines.append("--------------")
    lines.append(f"Report Type: {snapshot['report_type']}")
    lines.append(f"Intent: {snapshot['intent']}")
    lines.append(f"Store Health Score: {overview['health_score']}/100")
    lines.append(f"Current Month Revenue: {overview['current_month_revenue']}")
    lines.append(f"Previous Month Revenue: {overview['previous_month_revenue']}")
    lines.append(f"Revenue Growth Rate: {overview['revenue_growth_rate']}")
    lines.append(f"Active Offers: {overview['active_offers']}")
    lines.append(f"Total Broadcasts Sent: {overview['broadcasts_sent']}")
    lines.append(f"Inventory Units: {overview['inventory_units']}")
    if overview.get("active_model"):
        active_model = overview["active_model"]
        lines.append(
            f"Active ML Model: {active_model['name']} | MAE={active_model['mae']} | RMSE={active_model['rmse']} | MAPE={active_model['mape']}"
        )

    lines.append("")
    lines.append("FOCUS ITEMS")
    lines.append("-----------")
    for item in snapshot["focus_items"][:10]:
        if isinstance(item, dict):
            lines.append(
                f"- {item.get('product_name', 'Unknown Item')} | Status: {item.get('status')} | Stock: {item.get('stock')} | "
                f"7d Forecast: {item.get('forecast_7d')} | 30d Forecast: {item.get('forecast_30d')} | "
                f"Health: {item.get('health_score')}/100 | Reason: {', '.join(item.get('reasons', [])) or 'N/A'}"
            )
        else:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("RECOMMENDATIONS")
    lines.append("---------------")
    for item in snapshot["reorder_candidates"][:6]:
        lines.append(
            f"- Reorder {item.get('product_name')} because {', '.join(item.get('reasons', [])) or 'forecast risk is elevated'}"
        )
    for item in snapshot["promotion_candidates"][:6]:
        lines.append(
            f"- Promote {item.get('product_name')} because {', '.join(item.get('reasons', [])) or 'inventory is moving slowly'}"
        )
    for item in snapshot["dead_stock_candidates"][:4]:
        lines.append(
            f"- Review dead stock for {item.get('product_name')} because {', '.join(item.get('reasons', [])) or 'no recent movement'}"
        )

    lines.append("")
    lines.append("CATEGORY TRENDS")
    lines.append("---------------")
    for item in snapshot["underperforming_categories"][:6]:
        lines.append(
            f"- {item.get('category')}: current 30d revenue {item.get('current_30d_revenue')}, previous 30d revenue {item.get('previous_30d_revenue')}, growth rate {item.get('growth_rate')}"
        )

    lines.append("")
    lines.append("RECENT SALES")
    lines.append("------------")
    for item in snapshot["daily_sales_last_7_days"]:
        lines.append(
            f"- {item['date']}: revenue {item['revenue']} across {item['bills']} bills"
        )

    return "\n".join(lines)


def build_rag_context(db: Session, app_db: Session, question: str, report_type: str = "chat") -> str:
    """Build a structured, grounded business context for the Gemini prompt."""
    snapshot = _load_inventory_snapshot(db, app_db, question, report_type=report_type)
    return _render_context_snapshot(snapshot)


def build_rag_payload(db: Session, app_db: Session, question: str, report_type: str = "chat") -> dict[str, Any]:
    """Return the structured context snapshot used by the model."""
    snapshot = _load_inventory_snapshot(db, app_db, question, report_type=report_type)
    return {
        "snapshot": snapshot,
        "rendered_context": _render_context_snapshot(snapshot),
        "snapshot_json": json.dumps(_to_jsonable(snapshot), indent=2, ensure_ascii=True),
    }


def _build_prompt(context: str, question: str, report_type: str) -> str:
    instructions = """
You are the AI Store Employee for Aadhirai Mart.

Use only the retrieved business context below.
Do not invent product names, numbers, forecasts, or business reasons.
If the context does not contain enough evidence, say that clearly and explain what is missing.

When you give a recommendation:
- include the product or category
- explain why the recommendation was triggered
- mention the relevant evidence such as stock, forecasts, days since last sale, expiry, health score, or category trend
- keep the answer practical for a merchant

For morning briefs, summarize store health, critical products, dead stock, suggested interventions, and risk to revenue.
For end-of-day reviews, summarize actions taken, remaining risks, and what to watch tomorrow.

Respond in concise markdown.
"""
    return (
        f"{instructions}\n"
        f"Report Type: {report_type}\n"
        f"Merchant Question: {question}\n\n"
        f"--- RETRIEVED BUSINESS CONTEXT ---\n{context}\n"
        f"--- END CONTEXT ---\n\n"
        "Answer:"
    )


def ask_ai(question: str, db: Session, app_db: Session, report_type: str = "chat") -> dict[str, Any]:
    """Answer a merchant question using grounded business retrieval and Gemini."""
    if not model:
        return {
            "answer": "Error: GEMINI_API_KEY is missing or invalid. Please check your backend configuration.",
            "context_snapshot": "No context generated due to missing API key.",
            "intent": _question_intent(question),
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
        }

    payload = build_rag_payload(db, app_db, question, report_type=report_type)
    context = payload["rendered_context"]
    prompt = _build_prompt(context, question, report_type)

    try:
        response = model.generate_content(prompt)
        answer = (response.text or "").strip()
    except Exception as e:
        answer = f"Sorry, I encountered an error while analyzing the data: {str(e)}"

    snapshot_json = payload["snapshot_json"]
    return {
        "answer": answer,
        "context_snapshot": snapshot_json,
        "intent": payload["snapshot"]["intent"],
        "report_type": report_type,
        "generated_at": payload["snapshot"]["generated_at"].isoformat(),
    }


def generate_brief(report_type: str, db: Session, app_db: Session) -> dict[str, Any]:
    """Generate a daily merchant briefing using the same grounded retrieval stack."""
    if report_type == "morning":
        question = "Generate a morning brief for the merchant."
    elif report_type == "end_of_day":
        question = "Generate an end-of-day review for the merchant."
    else:
        question = "Generate a concise store health brief."
    return ask_ai(question, db, app_db, report_type=report_type)
