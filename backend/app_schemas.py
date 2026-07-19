"""Pydantic schemas for app data (offers, broadcasts, activity logs)."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class BroadcastRecipientResponse(BaseModel):
    """Response schema for broadcast recipient."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, by_alias=False)
    
    id: int
    broadcastLogId: int = Field(validation_alias="broadcast_log_id")
    customerId: int = Field(validation_alias="customer_id")
    customerName: str = Field(validation_alias="customer_name")
    phoneNumber: str = Field(validation_alias="phone_number")
    sentStatus: str = Field(validation_alias="sent_status")
    sentAt: datetime = Field(validation_alias="sent_at")
    createdAt: datetime = Field(validation_alias="created_at")


class BroadcastLogResponse(BaseModel):
    """Response schema for broadcast log."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, by_alias=False)
    
    id: int
    offerId: int = Field(validation_alias="offer_id")
    customerCount: int = Field(validation_alias="customer_count")
    status: str
    sentAt: datetime = Field(validation_alias="sent_at")
    scheduledAt: Optional[datetime] = Field(validation_alias="scheduled_at")
    createdAt: datetime = Field(validation_alias="created_at")
    recipients: List[BroadcastRecipientResponse] = []


class BroadcastRecipientCreate(BaseModel):
    """Request schema for creating broadcast recipients."""
    model_config = ConfigDict(from_attributes=True)
    
    customerId: int
    customerName: str
    phoneNumber: str


class BroadcastLogCreate(BaseModel):
    """Request schema for creating broadcast log."""
    model_config = ConfigDict(from_attributes=True)
    
    offerId: int
    customerCount: int
    recipients: List[BroadcastRecipientCreate] = []
    scheduledAt: Optional[datetime] = None


class OfferResponse(BaseModel):
    """Response schema for offer."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, by_alias=False)
    
    id: int
    productIds: List[int] = Field(validation_alias="product_ids")
    productNames: List[str] = Field(validation_alias="product_names")
    discountType: str = Field(validation_alias="discount_type")
    discountValue: float = Field(validation_alias="discount_value")
    validFrom: datetime = Field(validation_alias="valid_from")
    validTo: datetime = Field(validation_alias="valid_to")
    status: str
    broadcasted: bool = False
    createdAt: datetime = Field(validation_alias="created_at")


class OfferCreate(BaseModel):
    """Request schema for creating offer."""
    model_config = ConfigDict(from_attributes=True)
    
    productIds: List[int]
    productNames: List[str]
    discountType: str
    discountValue: float
    validFrom: datetime
    validTo: datetime


class AppUsageLogResponse(BaseModel):
    """Response schema for app usage log."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, by_alias=False)
    
    id: int
    actionType: str = Field(validation_alias="action_type")
    actionDescription: str = Field(validation_alias="action_description")
    offerId: Optional[int] = Field(validation_alias="offer_id")
    broadcastLogId: Optional[int] = Field(validation_alias="broadcast_log_id")
    extraData: Optional[dict] = Field(None, validation_alias="extra_data")
    createdAt: datetime = Field(validation_alias="created_at")


class AppUsageLogCreate(BaseModel):
    """Request schema for creating app usage log."""
    model_config = ConfigDict(populate_by_name=True)
    
    actionType: str = Field(validation_alias="action_type")
    actionDescription: str = Field(validation_alias="action_description")
    offerId: Optional[int] = Field(None, validation_alias="offer_id")
    broadcastLogId: Optional[int] = Field(None, validation_alias="broadcast_log_id")
    extraData: Optional[dict] = Field(None, validation_alias="extra_data")


# Analytics Response Schemas
class OfferAnalytics(BaseModel):
    """Analytics data for offers."""
    model_config = ConfigDict(populate_by_name=True, by_alias=False)
    
    totalOffersApproved: int = Field(validation_alias="total_offers_approved")
    totalBroadcastsSent: int = Field(validation_alias="total_broadcasts_sent")
    totalCustomersReached: int = Field(validation_alias="total_customers_reached")
    averageRecipientsPerBroadcast: float = Field(validation_alias="average_recipients_per_broadcast")


class ActivityStats(BaseModel):
    """Activity statistics."""
    model_config = ConfigDict(populate_by_name=True, by_alias=False)
    
    actionType: str = Field(validation_alias="action_type")
    count: int
    lastAction: datetime = Field(validation_alias="last_action")


class Last7DaysActivity(BaseModel):
    """Last 7 days activity summary."""
    model_config = ConfigDict(populate_by_name=True, by_alias=False)
    
    date: str
    offersApproved: int = Field(validation_alias="offers_approved")
    broadcastsSent: int = Field(validation_alias="broadcasts_sent")


class OfferHistoryItem(BaseModel):
    """Single offer history item."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, by_alias=False)
    
    id: int
    productNames: List[str] = Field(validation_alias="product_names")
    discountValue: float = Field(validation_alias="discount_value")
    discountType: str = Field(validation_alias="discount_type")
    validFrom: datetime = Field(validation_alias="valid_from")
    validTo: datetime = Field(validation_alias="valid_to")
    createdAt: datetime = Field(validation_alias="created_at")


class BroadcastHistoryItem(BaseModel):
    """Single broadcast history item."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, by_alias=False)
    
    id: int
    offerId: int = Field(validation_alias="offer_id")
    customerCount: int = Field(validation_alias="customer_count")
    status: str
    sentAt: datetime = Field(validation_alias="sent_at")


class InterventionRecordResponse(BaseModel):
    """Response schema for intervention tracking."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    recommendation_key: str
    product_id: Optional[int] = None
    product_name: str
    category_name: Optional[str] = None
    intervention_type: str
    recommendation_reason: str
    recommended_discount_type: Optional[str] = None
    recommended_discount_value: Optional[float] = None
    recommended_action: Optional[str] = None
    merchant: Optional[str] = None
    status: str
    generated_at: datetime
    viewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    action_performed: Optional[str] = None
    notes: Optional[str] = None
    stock_before: Optional[float] = None
    stock_after: Optional[float] = None
    units_sold_before: Optional[float] = None
    units_sold_after: Optional[float] = None
    revenue_before: Optional[float] = None
    revenue_after: Optional[float] = None
    estimated_revenue_recovered: Optional[float] = None
    estimated_loss_avoided: Optional[float] = None
    sales_velocity_before: Optional[float] = None
    sales_velocity_after: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class InterventionApproveRequest(BaseModel):
    """Request schema for approving an intervention."""
    model_config = ConfigDict(populate_by_name=True)

    recommendationKey: str
    merchant: Optional[str] = None
    actionPerformed: Optional[str] = None
    notes: Optional[str] = None
    approvedAt: Optional[datetime] = None


class InterventionExecuteRequest(BaseModel):
    """Request schema for executing an intervention."""
    model_config = ConfigDict(populate_by_name=True)

    recommendationKey: str
    merchant: Optional[str] = None
    actionPerformed: Optional[str] = None
    notes: Optional[str] = None
    executedAt: Optional[datetime] = None


class ImpactMetricsResponse(BaseModel):
    """Aggregate impact metrics."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    generatedRecommendations: int = Field(validation_alias="generated_recommendations")
    viewedRecommendations: int = Field(validation_alias="viewed_recommendations")
    approvedRecommendations: int = Field(validation_alias="approved_recommendations")
    executedRecommendations: int = Field(validation_alias="executed_recommendations")
    estimatedRevenueRecovered: float = Field(validation_alias="estimated_revenue_recovered")
    estimatedLossAvoided: float = Field(validation_alias="estimated_loss_avoided")
    deadStockReduced: float = Field(validation_alias="dead_stock_reduced")
    inventoryCleared: float = Field(validation_alias="inventory_cleared")
    avgSalesVelocityImprovement: float = Field(validation_alias="avg_sales_velocity_improvement")


class ImpactReportItem(BaseModel):
    """Report item for weekly/monthly impact summary."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    label: str
    generatedRecommendations: int = Field(validation_alias="generated_recommendations")
    approvedRecommendations: int = Field(validation_alias="approved_recommendations")
    executedRecommendations: int = Field(validation_alias="executed_recommendations")
    estimatedRevenueRecovered: float = Field(validation_alias="estimated_revenue_recovered")
    estimatedLossAvoided: float = Field(validation_alias="estimated_loss_avoided")
    deadStockReduced: float = Field(validation_alias="dead_stock_reduced")
    inventoryCleared: float = Field(validation_alias="inventory_cleared")
    avgSalesVelocityImprovement: float = Field(validation_alias="avg_sales_velocity_improvement")


class InterventionRefreshStatusResponse(BaseModel):
    """Background recommendation refresh job status."""
    status: str
    error: Optional[str] = None
    startedAt: Optional[str] = Field(None, validation_alias="started_at")
    completedAt: Optional[str] = Field(None, validation_alias="completed_at")
