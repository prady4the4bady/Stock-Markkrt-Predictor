"""
Market Oracle - User Activity Models
Secure models for tracking user behavior and preferences within the application
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, Index, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base
import uuid


class UserWatchlist(Base):
    """
    Tracks stocks/crypto that users add to their watchlist
    """
    __tablename__ = "user_watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)  # 'stock', 'crypto', 'forex', 'index'
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    alert_price_above = Column(Float, nullable=True)
    alert_price_below = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="watchlist")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='unique_user_watchlist'),
        Index('idx_watchlist_user_symbol', 'user_id', 'symbol'),
    )


class UserStockView(Base):
    """
    Tracks when users view specific stocks - used for pattern analysis
    """
    __tablename__ = "user_stock_views"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)
    view_count = Column(Integer, default=1)
    first_viewed_at = Column(DateTime, default=datetime.utcnow)
    last_viewed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_view_duration_seconds = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="stock_views")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='unique_user_stock_view'),
        Index('idx_stock_views_user_symbol', 'user_id', 'symbol'),
        Index('idx_stock_views_view_count', 'user_id', 'view_count'),
    )


class UserStockInteraction(Base):
    """
    Detailed interaction log for each stock view session
    """
    __tablename__ = "user_stock_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)
    
    # Session details
    session_id = Column(String(64), default=lambda: str(uuid.uuid4()), index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    
    # Interaction details
    prediction_requested = Column(Boolean, default=False)
    prediction_days = Column(Integer, nullable=True)
    chart_period_selected = Column(String(20), nullable=True)
    news_viewed = Column(Boolean, default=False)
    technical_chart_viewed = Column(Boolean, default=False)
    
    # Context at time of interaction
    price_at_view = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="stock_interactions")
    
    __table_args__ = (
        Index('idx_interactions_user_time', 'user_id', 'started_at'),
        Index('idx_interactions_symbol', 'symbol'),
    )


class UserPredictionHistory(Base):
    """
    Stores prediction requests and their outcomes for accuracy tracking
    """
    __tablename__ = "user_prediction_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)
    
    # Prediction details
    requested_at = Column(DateTime, default=datetime.utcnow)
    prediction_days = Column(Integer, nullable=False)
    predicted_prices = Column(JSON, nullable=False)  # List of predicted prices
    predicted_dates = Column(JSON, nullable=False)   # List of predicted dates
    confidence_score = Column(Float, nullable=False)
    
    # Model weights used
    model_weights = Column(JSON, nullable=True)
    
    # Price at prediction time
    actual_price_at_prediction = Column(Float, nullable=False)
    
    # Outcome tracking (filled in later when dates pass)
    actual_prices = Column(JSON, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    outcome_computed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="prediction_history")
    
    __table_args__ = (
        Index('idx_prediction_history_user_symbol', 'user_id', 'symbol'),
        Index('idx_prediction_history_time', 'requested_at'),
    )


class UserPreferences(Base):
    """
    Stores user preferences and settings
    """
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Display preferences
    default_prediction_days = Column(Integer, default=7)
    default_chart_period = Column(String(20), default="1y")
    theme = Column(String(20), default="dark")
    
    # Notification preferences
    email_alerts_enabled = Column(Boolean, default=True)
    price_alert_frequency = Column(String(20), default="realtime")  # realtime, hourly, daily
    
    # Default asset type preference
    preferred_asset_type = Column(String(20), default="stock")
    
    # Analysis preferences
    show_technical_indicators = Column(Boolean, default=True)
    show_news_feed = Column(Boolean, default=True)
    show_model_weights = Column(Boolean, default=True)
    
    # Privacy settings
    track_activity = Column(Boolean, default=True)  # Allow user to opt-out
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="preferences")


class UserSession(Base):
    """
    Tracks user sessions for security and analytics
    """
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(256), unique=True, index=True, nullable=False)
    
    # Session metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    
    # Security information (hashed/anonymized)
    ip_hash = Column(String(64), nullable=True)  # Hashed IP for security
    user_agent_hash = Column(String(64), nullable=True)  # Hashed user agent
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    
    # Session status
    is_active = Column(Boolean, default=True)
    invalidated_at = Column(DateTime, nullable=True)
    invalidation_reason = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_sessions_user_active', 'user_id', 'is_active'),
        Index('idx_sessions_token', 'session_token'),
    )


class UserBehaviorPattern(Base):
    """
    Aggregated behavior patterns computed from user activity
    Used to improve prediction confidence based on user expertise/focus areas
    """
    __tablename__ = "user_behavior_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Computed behavior metrics
    most_viewed_symbols = Column(JSON, default=list)  # Top 10 symbols
    most_viewed_asset_types = Column(JSON, default=dict)  # asset_type: count
    
    # Time patterns
    peak_usage_hours = Column(JSON, default=list)  # Hours of day with most activity
    peak_usage_days = Column(JSON, default=list)   # Days of week with most activity
    average_session_duration = Column(Float, default=0.0)  # in minutes
    
    # Engagement metrics
    total_predictions_requested = Column(Integer, default=0)
    total_unique_symbols_viewed = Column(Integer, default=0)
    total_session_count = Column(Integer, default=0)
    
    # Computed interest scores
    sector_interests = Column(JSON, default=dict)  # sector: interest_score
    
    # Pattern analysis timestamps
    first_activity = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    pattern_computed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="behavior_pattern")


class AuditLog(Base):
    """
    Security audit log for tracking sensitive operations
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Audit details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)  # user, watchlist, prediction, etc.
    resource_id = Column(Integer, nullable=True)
    
    # Request details (anonymized)
    ip_hash = Column(String(64), nullable=True)
    user_agent_hash = Column(String(64), nullable=True)
    
    # Change tracking
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(20), default="success")  # success, failure, blocked
    error_message = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_timestamp', 'timestamp'),
    )
