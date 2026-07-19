"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class ProductResponse(BaseModel):
    """Response schema for product."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, by_alias=False)
    
    id: int
    name: str
    brand: Optional[str] = None
    categoryId: Optional[int] = Field(None, validation_alias="category_id")
    unit: str
    mrp: float
    costPrice: float = Field(validation_alias="cost_price")
    barcode: Optional[str] = None
    hsnCode: Optional[str] = Field(None, validation_alias="hsn_code")
    taxPercent: float = Field(5.0, validation_alias="tax_percent")
    isActive: bool = Field(True, validation_alias="is_active")
    createdAt: Optional[datetime] = Field(None, validation_alias="created_at")
    category: Optional[str] = None
    stock: Optional[int] = None
    status: Optional[str] = None
    aiPick: Optional[bool] = None
    daysIdle: Optional[int] = None
    img: Optional[str] = None
    expiryDays: Optional[int] = None
    weightKg: Optional[float] = None
    healthScore: Optional[float] = None
    batch: Optional[str] = None
    # AI enrichment fields (populated by attach_ai_predictions / GET /api/ai/products)
    forecast7d: Optional[float] = None
    forecast30d: Optional[float] = None
    confidence: Optional[float] = None
    averageDailySales: Optional[float] = None
    salesTrend7d: Optional[float] = None
    salesTrend30d: Optional[float] = None
    salesTrend90d: Optional[float] = None
    categoryTrend: Optional[float] = None
    seasonalTrend: Optional[float] = None
    weekdayVsWeekendDemand: Optional[float] = None
    inventoryTurnover: Optional[float] = None
    historicalRestockFrequency: Optional[float] = None
    revenueContribution: Optional[float] = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: str
    address: Optional[str] = None
    creditLimit: float = 0
    outstandingBalance: float = 0
    loyaltyPoints: int = 0
    isActive: bool = True
    createdAt: Optional[datetime] = None
    lastPurchase: Optional[datetime] = None   # ADD THIS

    class Config:
        from_attributes = True


class NGOResponse(BaseModel):
    id: int
    name: str
    contact: str
    address: str
    category: str
    emoji: Optional[str] = None
    totalReceived: float = 0
    createdAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class DonationRecordResponse(BaseModel):
    id: int
    productId: int
    productName: str
    ngoId: int
    ngoName: str
    quantity: int
    weightKg: float
    carbonSavedKg: float
    donationDate: Optional[datetime] = None

    class Config:
        from_attributes = True


class DonationRecordCreate(BaseModel):
    productId: int
    productName: str
    ngoId: int
    ngoName: str
    quantity: int
    weightKg: float


class OfferProductResponse(BaseModel):
    id: int
    product_id: int

    class Config:
        from_attributes = True


class OfferResponse(BaseModel):
    id: int
    productIds: List[int]
    discountType: str
    discountValue: float
    validFrom: str
    validTo: str
    isActive: bool = True

    class Config:
        from_attributes = True


class OfferCreate(BaseModel):
    productIds: List[int]
    discountType: str
    discountValue: float
    validFrom: str
    validTo: str


class DailySalesResponse(BaseModel):
    day: str
    value: float


class PaymentMixResponse(BaseModel):
    name: str
    value: float
    color: str


class MoverResponse(BaseModel):
    name: str
    qty: int


class AnalyticsResponse(BaseModel):
    dailySales: List[DailySalesResponse]
    paymentMix: List[PaymentMixResponse]
    fastMovers: List[MoverResponse]
    slowMovers: List[MoverResponse]
    inventoryHealthScore: Optional[float] = None


class CarbonMetricsResponse(BaseModel):
    totalFoodKg: float
    totalCarbon: float
    totalProducts: int
    familiesHelped: int


class MonthlyTrendResponse(BaseModel):
    month: str
    foodKg: float
    carbon: float
    products: int


class SustainabilityResponse(BaseModel):
    metrics: CarbonMetricsResponse
    trends: List[MonthlyTrendResponse]


class CategoryResponse(BaseModel):
    categories: List[str]
