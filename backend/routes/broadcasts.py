"""Broadcast API routes for managing and tracking offer broadcasts."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app_db import get_app_db
from app_models import BroadcastLog, BroadcastRecipient, AppUsageLog, Offer, BroadcastStatus, ActionType
from app_schemas import (
    BroadcastLogResponse,
    BroadcastLogCreate,
    BroadcastRecipientResponse,
    BroadcastRecipientCreate,
)
from services.twilio_service import send_whatsapp

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])


class SendBroadcastRequest(BaseModel):
    """Request payload for sending broadcast with poster."""
    poster_url: str
    phone_numbers: List[str]
    message: str


class BroadcastSendResponse(BaseModel):
    """Response for broadcast send request."""
    success: bool
    messages_sent: int
    poster_url: str
    results: List[dict]


@router.post("", response_model=BroadcastLogResponse)
def create_broadcast(
    broadcast_data: BroadcastLogCreate,
    db: Session = Depends(get_app_db)
):
    """
    Create a new broadcast log for an approved offer.
    
    This endpoint:
    1. Creates a BroadcastLog record
    2. Creates BroadcastRecipient records for each customer
    3. Logs the action in AppUsageLog
    """
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == broadcast_data.offerId).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Create broadcast log
    broadcast_log = BroadcastLog(
        offer_id=broadcast_data.offerId,
        customer_count=broadcast_data.customerCount,
        status=BroadcastStatus.SENT,
        scheduled_at=broadcast_data.scheduledAt,
        sent_at=datetime.utcnow()
    )
    
    db.add(broadcast_log)
    db.flush()  # Flush to get the broadcast_log.id
    
    # Create recipient records
    for recipient_data in broadcast_data.recipients:
        recipient = BroadcastRecipient(
            broadcast_log_id=broadcast_log.id,
            customer_id=recipient_data.customerId,
            customer_name=recipient_data.customerName,
            phone_number=recipient_data.phoneNumber,
            sent_status=BroadcastStatus.SENT,
            sent_at=datetime.utcnow()
        )
        db.add(recipient)
    
    # Log the broadcast action
    activity_log = AppUsageLog(
        action_type=ActionType.BROADCAST_SENT,
        action_description=f"Offer broadcast sent to {broadcast_data.customerCount} customers",
        offer_id=broadcast_data.offerId,
        broadcast_log_id=broadcast_log.id,
        extra_data={
            "recipient_count": broadcast_data.customerCount,
            "scheduled_at": broadcast_data.scheduledAt.isoformat() if broadcast_data.scheduledAt else None
        }
    )
    db.add(activity_log)
    
    # Mark the offer as broadcasted
    offer.broadcasted = True
    
    db.commit()
    db.refresh(broadcast_log)
    
    return BroadcastLogResponse.from_orm(broadcast_log)


@router.get("", response_model=List[BroadcastLogResponse])
def list_broadcasts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    offer_id: Optional[int] = None,
    db: Session = Depends(get_app_db)
):
    """Get all broadcast logs with optional filtering by offer ID."""
    query = db.query(BroadcastLog)
    
    if offer_id:
        query = query.filter(BroadcastLog.offer_id == offer_id)
    
    broadcasts = query.order_by(BroadcastLog.sent_at.desc()).offset(offset).limit(limit).all()
    
    return [BroadcastLogResponse.from_orm(b) for b in broadcasts]


@router.get("/{broadcast_id}", response_model=BroadcastLogResponse)
def get_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_app_db)
):
    """Get a specific broadcast log with all recipient details."""
    broadcast = db.query(BroadcastLog).filter(BroadcastLog.id == broadcast_id).first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    return BroadcastLogResponse.from_orm(broadcast)


@router.get("/offer/{offer_id}/broadcasts", response_model=List[BroadcastLogResponse])
def get_offer_broadcasts(
    offer_id: int,
    db: Session = Depends(get_app_db)
):
    """Get all broadcasts for a specific offer."""
    broadcasts = db.query(BroadcastLog).filter(
        BroadcastLog.offer_id == offer_id
    ).order_by(BroadcastLog.sent_at.desc()).all()
    
    return [BroadcastLogResponse.from_orm(b) for b in broadcasts]


@router.get("/{broadcast_id}/recipients", response_model=List[BroadcastRecipientResponse])
def get_broadcast_recipients(
    broadcast_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_app_db)
):
    """Get all recipients for a specific broadcast with pagination."""
    recipients = db.query(BroadcastRecipient).filter(
        BroadcastRecipient.broadcast_log_id == broadcast_id
    ).order_by(BroadcastRecipient.sent_at.desc()).offset(offset).limit(limit).all()
    
    return [BroadcastRecipientResponse.from_orm(r) for r in recipients]


@router.patch("/{broadcast_id}/recipients/{recipient_id}/status")
def update_recipient_status(
    broadcast_id: int,
    recipient_id: int,
    status: str,
    db: Session = Depends(get_app_db)
):
    """Update the delivery status of a specific recipient."""
    recipient = db.query(BroadcastRecipient).filter(
        BroadcastRecipient.id == recipient_id,
        BroadcastRecipient.broadcast_log_id == broadcast_id
    ).first()
    
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    recipient.sent_status = status
    db.commit()
    db.refresh(recipient)
    
    return BroadcastRecipientResponse.from_orm(recipient)


@router.get("/{broadcast_id}/summary")
def get_broadcast_summary(
    broadcast_id: int,
    db: Session = Depends(get_app_db)
):
    """Get summary statistics for a broadcast."""
    broadcast = db.query(BroadcastLog).filter(BroadcastLog.id == broadcast_id).first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    total_recipients = db.query(BroadcastRecipient).filter(
        BroadcastRecipient.broadcast_log_id == broadcast_id
    ).count()
    
    delivered = db.query(BroadcastRecipient).filter(
        BroadcastRecipient.broadcast_log_id == broadcast_id,
        BroadcastRecipient.sent_status == BroadcastStatus.DELIVERED
    ).count()
    
    failed = db.query(BroadcastRecipient).filter(
        BroadcastRecipient.broadcast_log_id == broadcast_id,
        BroadcastRecipient.sent_status == BroadcastStatus.FAILED
    ).count()
    
    return {
        "broadcast_id": broadcast_id,
        "offer_id": broadcast.offer_id,
        "total_recipients": total_recipients,
        "delivered": delivered,
        "failed": failed,
        "pending": total_recipients - delivered - failed,
        "sent_at": broadcast.sent_at,
        "status": broadcast.status
    }


@router.post("/send", response_model=BroadcastSendResponse)
def send_broadcast(
    payload: SendBroadcastRequest,
    db: Session = Depends(get_app_db)
):
    """
    Send WhatsApp messages with poster to multiple customers.
    
    Args:
        payload: Contains poster_url, phone_numbers list, and message text
        
    Returns:
        Success status and list of message SIDs from Twilio
    """
    results = []
    errors = []
    
    for phone in payload.phone_numbers:
        try:
            sid = send_whatsapp(phone, payload.message, payload.poster_url)
            results.append({"phone": phone, "sid": sid, "status": "sent"})
        except Exception as e:
            errors.append({"phone": phone, "error": str(e)})
            results.append({"phone": phone, "status": "failed", "error": str(e)})
    
    # Log the broadcast action
    activity_log = AppUsageLog(
        action_type=ActionType.BROADCAST_SENT,
        action_description=f"WhatsApp broadcast sent with poster to {len(payload.phone_numbers)} customers",
        extra_data={
            "poster_url": payload.poster_url,
            "message": payload.message,
            "recipient_count": len(payload.phone_numbers),
            "successful": len([r for r in results if r["status"] == "sent"]),
            "failed": len([r for r in results if r["status"] == "failed"])
        }
    )
    db.add(activity_log)
    db.commit()
    
    return BroadcastSendResponse(
        success=len(errors) == 0,
        messages_sent=len([r for r in results if r["status"] == "sent"]),
        poster_url=payload.poster_url,
        results=results
    )
