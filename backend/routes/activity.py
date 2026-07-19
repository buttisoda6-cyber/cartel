"""Activity tracking API routes — login, logout, poster, dashboard events."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app_db import get_app_db
from app_models import LoginActivity, AppUsageLog, ActionType

router = APIRouter(prefix="/api/activity", tags=["activity"])


# ── Request Schemas ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    user_id: Optional[str] = None
    device_info: Optional[str] = None


class LogoutRequest(BaseModel):
    username: str
    session_id: int  # login_activity.id returned on login


class DashboardRequest(BaseModel):
    username: str
    page: Optional[str] = "/"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login")
def track_login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_app_db),
):
    """
    Record a login event.

    Creates a LoginActivity row and an AppUsageLog row.
    Returns the session_id (LoginActivity.id) for use in logout.
    """
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)

    session = LoginActivity(
        user_id=payload.user_id,
        username=payload.username,
        login_time=datetime.utcnow(),
        ip_address=ip,
        device_info=payload.device_info,
    )
    db.add(session)
    db.flush()

    usage_log = AppUsageLog(
        action_type=ActionType.LOGIN,
        action_description=f"Merchant '{payload.username}' logged in",
        extra_data={
            "session_id": session.id,
            "ip_address": ip,
            "device_info": payload.device_info,
        },
    )
    db.add(usage_log)
    db.commit()
    db.refresh(session)

    return {"status": "ok", "session_id": session.id, "login_time": session.login_time}


@router.post("/logout")
def track_logout(
    payload: LogoutRequest,
    db: Session = Depends(get_app_db),
):
    """
    Record a logout event.

    Stamps logout_time on the matching LoginActivity row and
    appends an AppUsageLog row.
    """
    session = db.query(LoginActivity).filter(
        LoginActivity.id == payload.session_id
    ).first()

    logout_time = datetime.utcnow()

    if session:
        session.logout_time = logout_time
        db.add(session)

    usage_log = AppUsageLog(
        action_type=ActionType.LOGOUT,
        action_description=f"Merchant '{payload.username}' logged out",
        extra_data={
            "session_id": payload.session_id,
            "logout_time": logout_time.isoformat(),
        },
    )
    db.add(usage_log)
    db.commit()

    return {"status": "ok", "logout_time": logout_time}


@router.post("/poster-generated")
def track_poster_generated(
    payload: DashboardRequest,
    db: Session = Depends(get_app_db),
):
    """Log a poster generation event."""
    usage_log = AppUsageLog(
        action_type=ActionType.POSTER_GENERATED,
        action_description=f"Merchant '{payload.username}' generated a poster",
        extra_data={"page": payload.page},
    )
    db.add(usage_log)
    db.commit()
    return {"status": "ok"}


@router.post("/dashboard-viewed")
def track_dashboard_viewed(
    payload: DashboardRequest,
    db: Session = Depends(get_app_db),
):
    """Log a dashboard page-view event."""
    usage_log = AppUsageLog(
        action_type=ActionType.DASHBOARD_VIEWED,
        action_description=f"Merchant '{payload.username}' viewed page '{payload.page}'",
        extra_data={"page": payload.page},
    )
    db.add(usage_log)
    db.commit()
    return {"status": "ok"}


@router.get("/sessions")
def list_sessions(
    limit: int = 50,
    db: Session = Depends(get_app_db),
):
    """Return recent login sessions (for verification / admin view)."""
    sessions = (
        db.query(LoginActivity)
        .order_by(LoginActivity.login_time.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": s.id,
            "username": s.username,
            "user_id": s.user_id,
            "login_time": s.login_time,
            "logout_time": s.logout_time,
            "ip_address": s.ip_address,
            "device_info": s.device_info,
        }
        for s in sessions
    ]
