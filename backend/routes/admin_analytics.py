"""Administrator analytics routes."""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app_db import get_app_db
from app_models import AIConversation, AppUsageLog, InterventionRecord, LoginActivity, Offer, BroadcastLog

router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])


def _safe_extra_data(log: AppUsageLog) -> dict[str, Any]:
    return log.extra_data if isinstance(log.extra_data, dict) else {}


def _activity_window(db: Session, start: datetime | None = None, end: datetime | None = None):
    query = db.query(AppUsageLog)
    if start is not None:
        query = query.filter(AppUsageLog.created_at >= start)
    if end is not None:
        query = query.filter(AppUsageLog.created_at < end)
    return query


def _unique_logins(logins: list[LoginActivity]) -> set[str]:
    return {login.username for login in logins if login.username}


def _active_users(logins: list[LoginActivity], start: datetime) -> set[str]:
    return {
        login.username
        for login in logins
        if login.username and login.login_time and login.login_time >= start
    }


def _page_key(log: AppUsageLog) -> str:
    extra = _safe_extra_data(log)
    if "page" in extra and extra["page"]:
        return str(extra["page"])
    description = (log.action_description or "").lower()
    if "login" in description:
        return "/login"
    if "logout" in description:
        return "/logout"
    if "broadcast" in description:
        return "/broadcast"
    if "offer" in description:
        return "/offers"
    if "dashboard" in description:
        return "/"
    if "ai" in description or "chat" in description:
        return "/ai-chat"
    return "other"


def _summarize_period(db: Session, days: int) -> dict[str, Any]:
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    logs = _activity_window(db, start=start, end=now).all()
    logins = db.query(LoginActivity).filter(LoginActivity.login_time >= start).all()
    conversations = db.query(AIConversation).filter(AIConversation.created_at >= start).all()
    interventions = db.query(InterventionRecord).filter(InterventionRecord.generated_at >= start).all()

    action_counts = Counter(log.action_type for log in logs)
    page_counts = Counter(_page_key(log) for log in logs)
    user_names = _unique_logins(logins)
    returning_users = sum(
        1
        for username in user_names
        if db.query(LoginActivity).filter(LoginActivity.username == username).count() > 1
    )
    avg_session_seconds = 0.0
    durations = [
        (login.logout_time - login.login_time).total_seconds()
        for login in logins
        if login.logout_time and login.login_time
    ]
    if durations:
        avg_session_seconds = sum(durations) / len(durations)

    page_seconds: dict[str, float] = defaultdict(float)
    recent_page_hits = sorted(
        [log for log in logs if _page_key(log) != "other"],
        key=lambda item: item.created_at or now,
    )
    for idx, log in enumerate(recent_page_hits):
        current_page = _page_key(log)
        next_stamp = recent_page_hits[idx + 1].created_at if idx + 1 < len(recent_page_hits) else None
        delta = 0.0
        if next_stamp and log.created_at:
            delta = max(0.0, (next_stamp - log.created_at).total_seconds())
        page_seconds[current_page] += delta

    approved = sum(1 for item in interventions if item.approved_at)
    executed = sum(1 for item in interventions if item.executed_at)
    recommendation_conversion = (executed / max(1, len(interventions))) * 100.0
    approval_rate = (approved / max(1, len(interventions))) * 100.0

    return {
        "window_days": days,
        "registered_merchants": db.query(LoginActivity.username).distinct().count(),
        "daily_active_users": len(_active_users(logins, now - timedelta(days=1))),
        "weekly_active_users": len(_active_users(logins, now - timedelta(days=7))),
        "monthly_active_users": len(_active_users(logins, now - timedelta(days=30))),
        "login_frequency": len(logins),
        "average_session_duration_minutes": round(avg_session_seconds / 60.0, 2),
        "average_engagement_time_minutes": round(sum(page_seconds.values()) / 60.0, 2),
        "session_duration_by_user": round(avg_session_seconds / 60.0, 2),
        "most_visited_pages": [
            {"page": page, "count": count}
            for page, count in page_counts.most_common(10)
        ],
        "most_clicked_features": [
            {"action_type": action_type, "count": count}
            for action_type, count in action_counts.most_common(10)
        ],
        "page_time_spent": [
            {"page": page, "minutes": round(seconds / 60.0, 2)}
            for page, seconds in sorted(page_seconds.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
        "ai_chat_usage": len(conversations),
        "reports_generated": db.query(Offer).count() + db.query(BroadcastLog).count(),
        "recommendation_approval_rate": round(approval_rate, 2),
        "recommendation_conversion_rate": round(recommendation_conversion, 2),
        "returning_users": returning_users,
        "last_active_timestamp": max((login.login_time for login in logins if login.login_time), default=None),
    }


@router.get("")
def get_admin_analytics(db: Session = Depends(get_app_db)):
    """Return administrator analytics summary and supporting charts."""
    now = datetime.utcnow()
    weekly = [_summarize_period(db, days) for days in (7, 14, 30)]
    recent_logins = (
        db.query(LoginActivity)
        .order_by(LoginActivity.login_time.desc())
        .limit(12)
        .all()
    )
    recent_activity = (
        db.query(AppUsageLog)
        .order_by(AppUsageLog.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "generated_at": now,
        "summary": _summarize_period(db, 30),
        "weekly_snapshots": weekly,
        "recent_logins": [
            {
                "username": item.username,
                "login_time": item.login_time,
                "logout_time": item.logout_time,
                "device_info": item.device_info,
                "ip_address": item.ip_address,
            }
            for item in recent_logins
        ],
        "recent_activity": [
            {
                "action_type": item.action_type,
                "action_description": item.action_description,
                "created_at": item.created_at,
                "extra_data": item.extra_data,
            }
            for item in recent_activity
        ],
    }


@router.get("/export")
def export_admin_analytics(db: Session = Depends(get_app_db)):
    """Return a simple CSV-friendly analytics payload."""
    summary = _summarize_period(db, 30)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    for key, value in summary.items():
        if isinstance(value, list):
            writer.writerow([key, len(value)])
        else:
            writer.writerow([key, value])
    return {"csv": output.getvalue(), "generated_at": datetime.utcnow()}
