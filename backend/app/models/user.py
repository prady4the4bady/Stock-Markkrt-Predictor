from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date
from sqlalchemy.orm import relationship
from ..database import Base
from datetime import datetime


class User(Base):
    """
    Core user model with enhanced security and tracking relationships
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Subscription fields
    is_premium = Column(Boolean, default=False)
    subscription_plan = Column(String(50), default="free")  # free, pro, elite
    subscription_end = Column(DateTime, nullable=True)
    
    # Usage tracking for subscription limits
    predictions_today = Column(Integer, default=0)
    last_prediction_date = Column(Date, nullable=True)
    
    # Enhanced security fields
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(256), nullable=True)
    password_reset_token = Column(String(256), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, nullable=True)
    
    # Two-factor authentication
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(256), nullable=True)  # Encrypted
    
    # Profile data
    avatar_url = Column(String(512), nullable=True)
    timezone = Column(String(50), default="UTC")
    
    # Consent and compliance
    privacy_consent = Column(Boolean, default=False)
    privacy_consent_date = Column(DateTime, nullable=True)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_date = Column(DateTime, nullable=True)
    data_deletion_requested = Column(Boolean, default=False)
    data_deletion_requested_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships to activity tracking models
    watchlist = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    stock_views = relationship("UserStockView", back_populates="user", cascade="all, delete-orphan")
    stock_interactions = relationship("UserStockInteraction", back_populates="user", cascade="all, delete-orphan")
    prediction_history = relationship("UserPredictionHistory", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    behavior_pattern = relationship("UserBehaviorPattern", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
