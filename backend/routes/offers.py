"""Offer API routes - handles offer approval and management stored in SQLite."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from app_db import get_app_db
from app_models import Offer, AppUsageLog, ActionType, OfferStatus
from app_schemas import OfferResponse, OfferCreate, OfferHistoryItem

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.post("/approve", response_model=OfferResponse)
def approve_offer(
    offer_data: OfferCreate,
    db: Session = Depends(get_app_db)
):
    """
    Approve and create a new offer.
    
    This endpoint:
    1. Creates a new Offer record with approved status
    2. Stores product IDs and names
    3. Logs the action in AppUsageLog
    4. Archives previous offers
    """
    # Archive any previous offers
    db.query(Offer).filter(
        Offer.status == OfferStatus.ACTIVE
    ).update({Offer.status: OfferStatus.ARCHIVED})
    
    # Create new offer
    new_offer = Offer(
        product_ids=offer_data.productIds,
        product_names=offer_data.productNames,
        discount_type=offer_data.discountType,
        discount_value=offer_data.discountValue,
        valid_from=offer_data.validFrom,
        valid_to=offer_data.validTo,
        status=OfferStatus.APPROVED
    )
    
    db.add(new_offer)
    db.flush()
    
    # Log the action
    products_str = ", ".join(offer_data.productNames)
    discount_str = f"{offer_data.discountValue}{'%' if offer_data.discountType == 'percent' else '₹'}"
    
    activity_log = AppUsageLog(
        action_type=ActionType.OFFER_APPROVED,
        action_description=f"Approved {discount_str} discount offer for {products_str}",
        offer_id=new_offer.id,
        extra_data={
            "product_count": len(offer_data.productIds),
            "discount_type": offer_data.discountType,
            "discount_value": offer_data.discountValue
        }
    )
    db.add(activity_log)
    
    db.commit()
    db.refresh(new_offer)
    
    return OfferResponse.from_orm(new_offer)


@router.get("/current", response_model=Optional[OfferResponse])
def get_current_offer(db: Session = Depends(get_app_db)):
    """
    Get the oldest approved offer that hasn't been broadcasted yet.
    
    This endpoint:
    1. Returns only offers where status = 'approved' AND broadcasted = FALSE
    2. Orders by created_at ASC to get the oldest unbroadcasted offer
    3. Returns None if no unbroadcasted offers exist
    """
    offer = db.query(Offer).filter(
        Offer.status == OfferStatus.APPROVED,
        Offer.broadcasted == False
    ).order_by(Offer.created_at.desc()).first()
    
    if not offer:
        return None
    
    return OfferResponse.from_orm(offer)


@router.get("", response_model=List[OfferResponse])
def list_offers(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_app_db)
):
    """Get all offers with optional filtering by status."""
    query = db.query(Offer)
    
    if status:
        query = query.filter(Offer.status == status)
    
    offers = query.order_by(Offer.created_at.desc()).offset(offset).limit(limit).all()
    
    return [OfferResponse.from_orm(o) for o in offers]


@router.get("/{offer_id}", response_model=OfferResponse)
def get_offer(
    offer_id: int,
    db: Session = Depends(get_app_db)
):
    """Get a specific offer by ID."""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    return OfferResponse.from_orm(offer)


@router.get("/history/approval", response_model=List[OfferHistoryItem])
def get_offer_history(
    days: Optional[int] = Query(None, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_app_db)
):
    """Get offer approval history."""
    query = db.query(Offer)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Offer.created_at >= cutoff_date)
    
    offers = query.order_by(Offer.created_at.desc()).offset(offset).limit(limit).all()
    
    return [OfferHistoryItem.from_orm(o) for o in offers]


@router.patch("/{offer_id}/archive")
def archive_offer(
    offer_id: int,
    db: Session = Depends(get_app_db)
):
    """Archive an offer (mark as archived)."""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offer.status = OfferStatus.ARCHIVED
    db.commit()
    db.refresh(offer)
    
    return OfferResponse.from_orm(offer)


@router.get("/{offer_id}/details")
def get_offer_details(
    offer_id: int,
    db: Session = Depends(get_app_db)
):
    """Get detailed information about an offer including broadcast stats."""
    from app_models import BroadcastLog
    
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    broadcasts = db.query(BroadcastLog).filter(
        BroadcastLog.offer_id == offer_id
    ).all()
    
    total_recipients = sum(b.customer_count for b in broadcasts)
    
    return {
        "offer": OfferResponse.from_orm(offer),
        "broadcast_count": len(broadcasts),
        "total_recipients": total_recipients,
        "last_broadcast": broadcasts[-1].sent_at if broadcasts else None
    }


from datetime import timedelta
