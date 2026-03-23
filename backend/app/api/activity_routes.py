"""
Market Oracle - Activity API Routes
Secure endpoints for user activity tracking and watchlist management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User
from ..activity_tracker import ActivityTracker, BehaviorAnalyzer

router = APIRouter()


# ==================== Pydantic Models ====================

class WatchlistAddRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    asset_type: str = Field(..., pattern="^(stock|crypto|forex|index)$")
    notes: Optional[str] = Field(None, max_length=500)
    alert_price_above: Optional[float] = Field(None, ge=0)
    alert_price_below: Optional[float] = Field(None, ge=0)


class WatchlistResponse(BaseModel):
    id: int
    symbol: str
    asset_type: str
    added_at: str
    notes: Optional[str]
    alert_price_above: Optional[float]
    alert_price_below: Optional[float]


class StockViewRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    asset_type: str = Field(..., pattern="^(stock|stocks|crypto|forex|index|indices|commodity|commodities)$")
    duration_seconds: int = Field(default=0, ge=0)


class InteractionStartRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    asset_type: str = Field(..., pattern="^(stock|stocks|crypto|forex|index|indices|commodity|commodities)$")
    price_at_view: Optional[float] = None


class InteractionUpdateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    prediction_requested: Optional[bool] = None
    prediction_days: Optional[int] = Field(None, ge=1, le=30)
    chart_period_selected: Optional[str] = None
    news_viewed: Optional[bool] = None
    technical_chart_viewed: Optional[bool] = None


class InteractionEndRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class PreferencesUpdateRequest(BaseModel):
    default_prediction_days: Optional[int] = Field(None, ge=1, le=30)
    default_chart_period: Optional[str] = None
    theme: Optional[str] = Field(None, pattern="^(dark|light)$")
    email_alerts_enabled: Optional[bool] = None
    price_alert_frequency: Optional[str] = Field(None, pattern="^(realtime|hourly|daily)$")
    preferred_asset_type: Optional[str] = Field(None, pattern="^(stock|crypto|forex|index)$")
    show_technical_indicators: Optional[bool] = None
    show_news_feed: Optional[bool] = None
    show_model_weights: Optional[bool] = None
    track_activity: Optional[bool] = None


class TopViewedStockResponse(BaseModel):
    symbol: str
    asset_type: str
    view_count: int
    total_duration_minutes: float
    last_viewed: Optional[str]


# ==================== Watchlist Endpoints ====================

@router.get("/watchlist", response_model=List[WatchlistResponse])
async def get_watchlist(
    active_only: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's watchlist"""
    tracker = ActivityTracker(db)
    return tracker.get_user_watchlist(current_user.id, active_only)


@router.post("/watchlist", response_model=WatchlistResponse)
async def add_to_watchlist(
    request: WatchlistAddRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a symbol to watchlist"""
    tracker = ActivityTracker(db)
    item = tracker.add_to_watchlist(
        user_id=current_user.id,
        symbol=request.symbol.upper(),
        asset_type=request.asset_type,
        notes=request.notes,
        alert_above=request.alert_price_above,
        alert_below=request.alert_price_below
    )
    return {
        "id": item.id,
        "symbol": item.symbol,
        "asset_type": item.asset_type,
        "added_at": item.added_at.isoformat(),
        "notes": item.notes,
        "alert_price_above": item.alert_price_above,
        "alert_price_below": item.alert_price_below
    }


@router.delete("/watchlist/{symbol:path}")
async def remove_from_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a symbol from watchlist"""
    # URL-decode the symbol in case it contains encoded characters
    from urllib.parse import unquote
    decoded_symbol = unquote(symbol).upper()
    tracker = ActivityTracker(db)
    success = tracker.remove_from_watchlist(current_user.id, decoded_symbol)
    if not success:
        raise HTTPException(status_code=404, detail="Symbol not found in watchlist")
    return {"status": "removed", "symbol": decoded_symbol}


# ==================== Activity Tracking Endpoints ====================

@router.post("/activity/view")
async def track_stock_view(
    request: StockViewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Track a stock view event"""
    tracker = ActivityTracker(db)
    result = tracker.track_stock_view(
        user_id=current_user.id,
        symbol=request.symbol.upper(),
        asset_type=request.asset_type,
        duration_seconds=request.duration_seconds
    )
    if not result:
        return {"status": "tracking_disabled"}
    return {"status": "tracked", "view_count": result.view_count}


@router.post("/activity/interaction/start")
async def start_interaction(
    request: InteractionStartRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start an interaction session"""
    tracker = ActivityTracker(db)
    interaction = tracker.start_interaction_session(
        user_id=current_user.id,
        symbol=request.symbol.upper(),
        asset_type=request.asset_type,
        price_at_view=request.price_at_view,
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent")
    )
    if not interaction:
        return {"status": "tracking_disabled"}
    return {"status": "started", "session_id": interaction.session_id}


@router.post("/activity/interaction/update")
async def update_interaction(
    request: InteractionUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an interaction session"""
    tracker = ActivityTracker(db)
    interaction = tracker.update_interaction_session(
        session_id=request.session_id,
        prediction_requested=request.prediction_requested,
        prediction_days=request.prediction_days,
        chart_period_selected=request.chart_period_selected,
        news_viewed=request.news_viewed,
        technical_chart_viewed=request.technical_chart_viewed
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "updated"}


@router.post("/activity/interaction/end")
async def end_interaction(
    request: InteractionEndRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """End an interaction session"""
    tracker = ActivityTracker(db)
    interaction = tracker.end_interaction_session(request.session_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "status": "ended",
        "duration_seconds": interaction.duration_seconds
    }


@router.get("/activity/top-viewed", response_model=List[TopViewedStockResponse])
async def get_top_viewed(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's top viewed stocks"""
    tracker = ActivityTracker(db)
    return tracker.get_user_top_viewed_stocks(current_user.id, min(limit, 50))


# ==================== Prediction History Endpoints ====================

@router.get("/activity/predictions")
async def get_prediction_history(
    symbol: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's prediction history"""
    tracker = ActivityTracker(db)
    return tracker.get_user_prediction_history(
        user_id=current_user.id,
        symbol=symbol.upper() if symbol else None,
        limit=min(limit, 100)
    )


# ==================== User Preferences Endpoints ====================

@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    tracker = ActivityTracker(db)
    prefs = tracker.get_or_create_preferences(current_user.id)
    return {
        "default_prediction_days": prefs.default_prediction_days,
        "default_chart_period": prefs.default_chart_period,
        "theme": prefs.theme,
        "email_alerts_enabled": prefs.email_alerts_enabled,
        "price_alert_frequency": prefs.price_alert_frequency,
        "preferred_asset_type": prefs.preferred_asset_type,
        "show_technical_indicators": prefs.show_technical_indicators,
        "show_news_feed": prefs.show_news_feed,
        "show_model_weights": prefs.show_model_weights,
        "track_activity": prefs.track_activity
    }


@router.put("/preferences")
async def update_preferences(
    request: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    tracker = ActivityTracker(db)
    updates = {k: v for k, v in request.dict().items() if v is not None}
    prefs = tracker.update_preferences(current_user.id, **updates)
    return {"status": "updated"}


# ==================== Analytics & Insights Endpoints ====================

@router.get("/insights")
async def get_user_insights(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get personalized insights based on user behavior"""
    analyzer = BehaviorAnalyzer(db)
    return analyzer.get_user_insights(current_user.id)


@router.get("/insights/confidence-boost/{symbol:path}")
async def get_confidence_boost(
    symbol: str,
    base_confidence: float = 0.7,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get confidence boost for a symbol based on user history.
    This helps improve prediction confidence for familiar stocks.
    """
    analyzer = BehaviorAnalyzer(db)
    return analyzer.get_confidence_boost(
        user_id=current_user.id,
        symbol=symbol.upper(),
        base_confidence=base_confidence
    )


@router.post("/insights/refresh")
async def refresh_user_patterns(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Refresh computed behavior patterns"""
    analyzer = BehaviorAnalyzer(db)
    pattern = analyzer.compute_user_patterns(current_user.id)
    return {"status": "refreshed", "computed_at": pattern.pattern_computed_at.isoformat()}


# ==================== Data Export & Privacy Endpoints ====================

@router.get("/export")
async def export_user_data(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export all user data (GDPR/CCPA compliance).
    Returns all data associated with the user's account.
    """
    tracker = ActivityTracker(db)
    analyzer = BehaviorAnalyzer(db)
    
    return {
        "user": {
            "email": current_user.email,
            "full_name": current_user.full_name,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "subscription_plan": current_user.subscription_plan
        },
        "watchlist": tracker.get_user_watchlist(current_user.id, active_only=False),
        "top_viewed_stocks": tracker.get_user_top_viewed_stocks(current_user.id, limit=100),
        "prediction_history": tracker.get_user_prediction_history(current_user.id, limit=500),
        "insights": analyzer.get_user_insights(current_user.id),
        "preferences": {
            "default_prediction_days": (prefs := tracker.get_or_create_preferences(current_user.id)).default_prediction_days,
            "theme": prefs.theme,
            "track_activity": prefs.track_activity
        },
        "exported_at": datetime.utcnow().isoformat()
    }


@router.delete("/data")
async def request_data_deletion(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Request deletion of all user data (GDPR right to erasure).
    This marks the account for deletion but doesn't immediately delete.
    """
    current_user.data_deletion_requested = True
    current_user.data_deletion_requested_at = datetime.utcnow()
    db.commit()
    
    return {
        "status": "deletion_requested",
        "message": "Your data deletion request has been received. Your account and all associated data will be permanently deleted within 30 days."
    }
