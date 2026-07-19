"""SQLAlchemy ORM models for app data stored in SQLite (offers, broadcasts, activity logs)."""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Enum, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class OfferStatus(str, enum.Enum):
    """Status of an offer."""
    APPROVED = "approved"
    ARCHIVED = "archived"
    ACTIVE = "active"


class BroadcastStatus(str, enum.Enum):
    """Status of a broadcast."""
    PENDING = "Pending"
    SENT = "Sent"
    FAILED = "Failed"
    DELIVERED = "Delivered"


class ActionType(str, enum.Enum):
    """Types of actions that can be logged."""
    OFFER_APPROVED = "OFFER_APPROVED"
    BROADCAST_SENT = "BROADCAST_SENT"
    PROMOTION_CREATED = "PROMOTION_CREATED"
    AI_RECOMMENDATION_APPLIED = "AI_RECOMMENDATION_APPLIED"
    AI_RECOMMENDATION_GENERATED = "AI_RECOMMENDATION_GENERATED"
    AI_RECOMMENDATION_APPROVED = "AI_RECOMMENDATION_APPROVED"
    AI_RECOMMENDATION_EXECUTED = "AI_RECOMMENDATION_EXECUTED"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    POSTER_GENERATED = "POSTER_GENERATED"
    DASHBOARD_VIEWED = "DASHBOARD_VIEWED"


class Offer(Base):
    """Offers table - stores approved offers with product details."""
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    product_ids = Column(JSON, nullable=False)  # List of product IDs as JSON
    product_names = Column(JSON, nullable=False)  # List of product names as JSON
    discount_type = Column(String(50), nullable=False)  # "percent" or "flat"
    discount_value = Column(Float, nullable=False)
    valid_from = Column(DateTime, nullable=False, index=True)
    valid_to = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default=OfferStatus.APPROVED, index=True)
    broadcasted = Column(Boolean, default=False, index=True)  # Track if offer has been broadcasted
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    broadcast_logs = relationship("BroadcastLog", back_populates="offer", cascade="all, delete-orphan")
    app_usage_logs = relationship("AppUsageLog", back_populates="offer", foreign_keys="AppUsageLog.offer_id")


class BroadcastLog(Base):
    """Broadcast logs - tracks when and to how many customers offers were sent."""
    __tablename__ = "broadcast_logs"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, index=True)
    customer_count = Column(Integer, nullable=False)
    status = Column(String(50), default=BroadcastStatus.SENT)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    scheduled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    offer = relationship("Offer", back_populates="broadcast_logs")
    recipients = relationship("BroadcastRecipient", back_populates="broadcast_log", cascade="all, delete-orphan")


class BroadcastRecipient(Base):
    """Broadcast recipients - tracks individual customer delivery status."""
    __tablename__ = "broadcast_recipients"

    id = Column(Integer, primary_key=True, index=True)
    broadcast_log_id = Column(Integer, ForeignKey("broadcast_logs.id"), nullable=False, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    sent_status = Column(String(50), default=BroadcastStatus.SENT, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    broadcast_log = relationship("BroadcastLog", back_populates="recipients")


class AppUsageLog(Base):
    """Activity logs - tracks user actions in the application."""
    __tablename__ = "app_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    action_description = Column(Text, nullable=False)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=True)
    broadcast_log_id = Column(Integer, ForeignKey("broadcast_logs.id"), nullable=True)
    extra_data = Column(JSON, nullable=True)  # Additional data as JSON
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    offer = relationship("Offer", back_populates="app_usage_logs", foreign_keys=[offer_id])
    broadcast_log = relationship("BroadcastLog", foreign_keys=[broadcast_log_id])


class LoginActivity(Base):
    """Login activity table - tracks merchant login/logout sessions."""
    __tablename__ = "login_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    login_time = Column(DateTime, default=datetime.utcnow, index=True)
    logout_time = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    device_info = Column(Text, nullable=True)


class ProductAnalytics(Base):
    """Analytics table - stores computed business features for each product."""
    __tablename__ = "product_analytics"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True, nullable=False)
    
    # Core sales metrics
    average_daily_sales = Column(Float, nullable=True)
    average_weekly_sales = Column(Float, nullable=True)
    average_monthly_sales = Column(Float, nullable=True)
    sales_velocity = Column(Float, nullable=True)
    revenue_contribution = Column(Float, nullable=True)
    
    # Inventory metrics
    days_since_last_sale = Column(Integer, nullable=True)
    inventory_turnover = Column(Float, nullable=True)
    current_stock = Column(Float, nullable=True)
    days_of_inventory = Column(Float, nullable=True)
    historical_restock_frequency = Column(Float, nullable=True)
    
    # Trends
    sales_trend_7d = Column(Float, nullable=True)
    sales_trend_30d = Column(Float, nullable=True)
    sales_trend_90d = Column(Float, nullable=True)
    category_trend = Column(Float, nullable=True)
    seasonal_trend = Column(Float, nullable=True)
    weekday_vs_weekend_demand = Column(Float, nullable=True)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)


class MLForecast(Base):
    """ML Forecasting table - stores demand predictions per product."""
    __tablename__ = "ml_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True, nullable=False)

    # Demand forecasts
    forecast_7d = Column(Float, nullable=True)    # Expected units sold in next 7 days
    forecast_30d = Column(Float, nullable=True)   # Expected units sold in next 30 days

    # Prediction confidence (0-1)
    confidence = Column(Float, nullable=True)

    # Model info
    model_used = Column(String(50), nullable=True)   # "xgboost" or "lightgbm"
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)

    predicted_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)


class MLModelMeta(Base):
    """ML Model Metadata - tracks which model version is active."""
    __tablename__ = "ml_model_meta"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(50), nullable=False)      # "xgboost" or "lightgbm"
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False, index=True)
    trained_at = Column(DateTime, default=datetime.utcnow, index=True)
    feature_count = Column(Integer, nullable=True)
    training_rows = Column(Integer, nullable=True)


class AIConversation(Base):
    """AI Chat History - stores RAG interactions."""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_query = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    context_snapshot = Column(Text, nullable=True)  # Store the data snapshot used for the response
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class InterventionRecord(Base):
    """Intervention tracking table - stores recommendation lifecycle and impact."""
    __tablename__ = "intervention_records"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_key = Column(String(255), unique=True, nullable=False, index=True)
    product_id = Column(Integer, nullable=True, index=True)
    product_name = Column(String(255), nullable=False, index=True)
    category_name = Column(String(255), nullable=True, index=True)
    intervention_type = Column(String(100), nullable=False, index=True)
    recommendation_reason = Column(Text, nullable=False)
    recommended_discount_type = Column(String(50), nullable=True)
    recommended_discount_value = Column(Float, nullable=True)
    recommended_action = Column(String(255), nullable=True)
    merchant = Column(String(255), nullable=True, index=True)
    status = Column(String(50), default="generated", index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    viewed_at = Column(DateTime, nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True, index=True)
    executed_at = Column(DateTime, nullable=True, index=True)
    action_performed = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    approval_snapshot = Column(JSON, nullable=True)
    execution_snapshot = Column(JSON, nullable=True)
    stock_before = Column(Float, nullable=True)
    stock_after = Column(Float, nullable=True)
    units_sold_before = Column(Float, nullable=True)
    units_sold_after = Column(Float, nullable=True)
    revenue_before = Column(Float, nullable=True)
    revenue_after = Column(Float, nullable=True)
    estimated_revenue_recovered = Column(Float, nullable=True)
    estimated_loss_avoided = Column(Float, nullable=True)
    sales_velocity_before = Column(Float, nullable=True)
    sales_velocity_after = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
