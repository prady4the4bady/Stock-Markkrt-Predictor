"""
Market Oracle - Activity Tracking Service
Tracks and analyzes user behavior patterns within the application
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from collections import defaultdict

from .models import (
    User, UserWatchlist, UserStockView, UserStockInteraction,
    UserPredictionHistory, UserPreferences, UserBehaviorPattern, AuditLog
)
from .database import DatabaseSecurity


class ActivityTracker:
    """
    Service for tracking user activity within the Market Oracle application.
    All tracking respects user privacy preferences.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_tracking_enabled(self, user_id: int) -> bool:
        """Check if user has opted into activity tracking"""
        prefs = self.db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        return prefs.track_activity if prefs else True  # Default to enabled
    
    # ==================== STOCK VIEW TRACKING ====================
    
    def track_stock_view(
        self,
        user_id: int,
        symbol: str,
        asset_type: str,
        duration_seconds: int = 0
    ) -> Optional[UserStockView]:
        """
        Track when a user views a stock/crypto.
        Updates existing record or creates new one.
        """
        if not self.check_tracking_enabled(user_id):
            return None
        
        existing = self.db.query(UserStockView).filter(
            UserStockView.user_id == user_id,
            UserStockView.symbol == symbol
        ).first()
        
        if existing:
            existing.view_count += 1
            existing.last_viewed_at = datetime.utcnow()
            existing.total_view_duration_seconds += duration_seconds
        else:
            existing = UserStockView(
                user_id=user_id,
                symbol=symbol,
                asset_type=asset_type,
                view_count=1,
                total_view_duration_seconds=duration_seconds
            )
            self.db.add(existing)
        
        self.db.commit()
        return existing
    
    def get_user_top_viewed_stocks(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get user's most viewed stocks"""
        views = self.db.query(UserStockView).filter(
            UserStockView.user_id == user_id
        ).order_by(desc(UserStockView.view_count)).limit(limit).all()
        
        return [
            {
                "symbol": v.symbol,
                "asset_type": v.asset_type,
                "view_count": v.view_count,
                "total_duration_minutes": v.total_view_duration_seconds / 60,
                "last_viewed": v.last_viewed_at.isoformat() if v.last_viewed_at else None
            }
            for v in views
        ]
    
    # ==================== INTERACTION TRACKING ====================
    
    def start_interaction_session(
        self,
        user_id: int,
        symbol: str,
        asset_type: str,
        price_at_view: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[UserStockInteraction]:
        """Start a new interaction session for a stock view"""
        if not self.check_tracking_enabled(user_id):
            return None
        
        interaction = UserStockInteraction(
            user_id=user_id,
            symbol=symbol,
            asset_type=asset_type,
            price_at_view=price_at_view
        )
        self.db.add(interaction)
        self.db.commit()
        
        return interaction
    
    def update_interaction_session(
        self,
        session_id: str,
        prediction_requested: Optional[bool] = None,
        prediction_days: Optional[int] = None,
        chart_period_selected: Optional[str] = None,
        news_viewed: Optional[bool] = None,
        technical_chart_viewed: Optional[bool] = None
    ) -> Optional[UserStockInteraction]:
        """Update an existing interaction session with new activity"""
        interaction = self.db.query(UserStockInteraction).filter(
            UserStockInteraction.session_id == session_id
        ).first()
        
        if not interaction:
            return None
        
        if prediction_requested is not None:
            interaction.prediction_requested = prediction_requested
        if prediction_days is not None:
            interaction.prediction_days = prediction_days
        if chart_period_selected is not None:
            interaction.chart_period_selected = chart_period_selected
        if news_viewed is not None:
            interaction.news_viewed = news_viewed
        if technical_chart_viewed is not None:
            interaction.technical_chart_viewed = technical_chart_viewed
        
        self.db.commit()
        return interaction
    
    def end_interaction_session(
        self,
        session_id: str
    ) -> Optional[UserStockInteraction]:
        """End an interaction session and calculate duration"""
        interaction = self.db.query(UserStockInteraction).filter(
            UserStockInteraction.session_id == session_id
        ).first()
        
        if not interaction:
            return None
        
        interaction.ended_at = datetime.utcnow()
        interaction.duration_seconds = int(
            (interaction.ended_at - interaction.started_at).total_seconds()
        )
        
        self.db.commit()
        
        # Also update the aggregate view tracking
        self.track_stock_view(
            user_id=interaction.user_id,
            symbol=interaction.symbol,
            asset_type=interaction.asset_type,
            duration_seconds=interaction.duration_seconds
        )
        
        return interaction
    
    # ==================== WATCHLIST MANAGEMENT ====================
    
    def add_to_watchlist(
        self,
        user_id: int,
        symbol: str,
        asset_type: str,
        notes: Optional[str] = None,
        alert_above: Optional[float] = None,
        alert_below: Optional[float] = None
    ) -> UserWatchlist:
        """Add a symbol to user's watchlist"""
        existing = self.db.query(UserWatchlist).filter(
            UserWatchlist.user_id == user_id,
            UserWatchlist.symbol == symbol
        ).first()
        
        if existing:
            existing.is_active = True
            existing.notes = notes or existing.notes
            existing.alert_price_above = alert_above or existing.alert_price_above
            existing.alert_price_below = alert_below or existing.alert_price_below
        else:
            existing = UserWatchlist(
                user_id=user_id,
                symbol=symbol,
                asset_type=asset_type,
                notes=notes,
                alert_price_above=alert_above,
                alert_price_below=alert_below
            )
            self.db.add(existing)
        
        self.db.commit()
        self._log_audit(user_id, "watchlist_add", "watchlist", existing.id)
        return existing
    
    def remove_from_watchlist(
        self,
        user_id: int,
        symbol: str
    ) -> bool:
        """Remove a symbol from user's watchlist (soft delete)"""
        item = self.db.query(UserWatchlist).filter(
            UserWatchlist.user_id == user_id,
            UserWatchlist.symbol == symbol
        ).first()
        
        if item:
            item.is_active = False
            self.db.commit()
            self._log_audit(user_id, "watchlist_remove", "watchlist", item.id)
            return True
        return False
    
    def get_user_watchlist(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get user's watchlist"""
        query = self.db.query(UserWatchlist).filter(
            UserWatchlist.user_id == user_id
        )
        if active_only:
            query = query.filter(UserWatchlist.is_active == True)
        
        items = query.order_by(desc(UserWatchlist.added_at)).all()
        
        return [
            {
                "id": item.id,
                "symbol": item.symbol,
                "asset_type": item.asset_type,
                "added_at": item.added_at.isoformat(),
                "notes": item.notes,
                "alert_price_above": item.alert_price_above,
                "alert_price_below": item.alert_price_below
            }
            for item in items
        ]
    
    # ==================== PREDICTION HISTORY ====================
    
    def record_prediction(
        self,
        user_id: int,
        symbol: str,
        asset_type: str,
        prediction_days: int,
        predicted_prices: List[float],
        predicted_dates: List[str],
        confidence_score: float,
        actual_price: float,
        model_weights: Dict[str, float] = None
    ) -> UserPredictionHistory:
        """Record a prediction request for accuracy tracking"""
        prediction = UserPredictionHistory(
            user_id=user_id,
            symbol=symbol,
            asset_type=asset_type,
            prediction_days=prediction_days,
            predicted_prices=predicted_prices,
            predicted_dates=predicted_dates,
            confidence_score=confidence_score,
            actual_price_at_prediction=actual_price,
            model_weights=model_weights
        )
        self.db.add(prediction)
        self.db.commit()
        return prediction
    
    def get_user_prediction_history(
        self,
        user_id: int,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's prediction history"""
        query = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.user_id == user_id
        )
        if symbol:
            query = query.filter(UserPredictionHistory.symbol == symbol)
        
        predictions = query.order_by(
            desc(UserPredictionHistory.requested_at)
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "symbol": p.symbol,
                "asset_type": p.asset_type,
                "requested_at": p.requested_at.isoformat(),
                "prediction_days": p.prediction_days,
                "predicted_prices": p.predicted_prices,
                "predicted_dates": p.predicted_dates,
                "confidence_score": p.confidence_score,
                "actual_price_at_prediction": p.actual_price_at_prediction,
                "accuracy_score": p.accuracy_score
            }
            for p in predictions
        ]
    
    # ==================== USER PREFERENCES ====================
    
    def get_or_create_preferences(self, user_id: int) -> UserPreferences:
        """Get user preferences, creating defaults if needed"""
        prefs = self.db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not prefs:
            prefs = UserPreferences(user_id=user_id)
            self.db.add(prefs)
            self.db.commit()
        
        return prefs
    
    def update_preferences(
        self,
        user_id: int,
        **kwargs
    ) -> UserPreferences:
        """Update user preferences"""
        prefs = self.get_or_create_preferences(user_id)
        
        allowed_fields = {
            'default_prediction_days', 'default_chart_period', 'theme',
            'email_alerts_enabled', 'price_alert_frequency', 'preferred_asset_type',
            'show_technical_indicators', 'show_news_feed', 'show_model_weights',
            'track_activity'
        }
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(prefs, key, value)
        
        self.db.commit()
        return prefs
    
    # ==================== AUDIT LOGGING ====================
    
    def _log_audit(
        self,
        user_id: int,
        action: str,
        resource_type: str = None,
        resource_id: int = None,
        old_value: Any = None,
        new_value: Any = None,
        status: str = "success",
        error_message: str = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """Create an audit log entry"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value if isinstance(old_value, (dict, list)) else None,
            new_value=new_value if isinstance(new_value, (dict, list)) else None,
            status=status,
            error_message=error_message,
            ip_hash=DatabaseSecurity.hash_ip(ip_address) if ip_address else None,
            user_agent_hash=DatabaseSecurity.hash_user_agent(user_agent) if user_agent else None
        )
        self.db.add(log)
        # Don't commit - let the calling function handle it


class BehaviorAnalyzer:
    """
    Analyzes user behavior patterns to improve prediction confidence
    and provide personalized insights.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_user_patterns(self, user_id: int) -> UserBehaviorPattern:
        """
        Compute and store behavior patterns for a user.
        This data is used to improve prediction confidence.
        """
        # Get or create pattern record
        pattern = self.db.query(UserBehaviorPattern).filter(
            UserBehaviorPattern.user_id == user_id
        ).first()
        
        if not pattern:
            pattern = UserBehaviorPattern(user_id=user_id)
            self.db.add(pattern)
        
        # Compute most viewed symbols
        top_views = self.db.query(
            UserStockView.symbol,
            UserStockView.view_count
        ).filter(
            UserStockView.user_id == user_id
        ).order_by(
            desc(UserStockView.view_count)
        ).limit(10).all()
        
        pattern.most_viewed_symbols = [
            {"symbol": v.symbol, "count": v.view_count}
            for v in top_views
        ]
        
        # Compute asset type preferences
        asset_counts = self.db.query(
            UserStockView.asset_type,
            func.sum(UserStockView.view_count).label("total")
        ).filter(
            UserStockView.user_id == user_id
        ).group_by(UserStockView.asset_type).all()
        
        pattern.most_viewed_asset_types = {
            a.asset_type: int(a.total) for a in asset_counts
        }
        
        # Compute time patterns from interactions
        interactions = self.db.query(UserStockInteraction).filter(
            UserStockInteraction.user_id == user_id
        ).all()
        
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)
        total_duration = 0
        
        for interaction in interactions:
            hour_counts[interaction.started_at.hour] += 1
            day_counts[interaction.started_at.strftime("%A")] += 1
            total_duration += interaction.duration_seconds or 0
        
        # Top 3 peak hours
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        pattern.peak_usage_hours = [h[0] for h in sorted_hours[:3]]
        
        # Top 3 peak days
        sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)
        pattern.peak_usage_days = [d[0] for d in sorted_days[:3]]
        
        # Average session duration
        if interactions:
            pattern.average_session_duration = (total_duration / len(interactions)) / 60  # minutes
        
        # Engagement metrics
        pattern.total_predictions_requested = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.user_id == user_id
        ).count()
        
        pattern.total_unique_symbols_viewed = self.db.query(UserStockView).filter(
            UserStockView.user_id == user_id
        ).count()
        
        pattern.total_session_count = len(interactions)
        
        # First and last activity
        if interactions:
            pattern.first_activity = min(i.started_at for i in interactions)
            pattern.last_activity = max(i.started_at for i in interactions)
        
        pattern.pattern_computed_at = datetime.utcnow()
        
        self.db.commit()
        return pattern
    
    def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """
        Get insights about a user's behavior for display in the UI
        """
        pattern = self.db.query(UserBehaviorPattern).filter(
            UserBehaviorPattern.user_id == user_id
        ).first()
        
        if not pattern:
            pattern = self.compute_user_patterns(user_id)
        
        # Compute additional insights
        predictions = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.user_id == user_id,
            UserPredictionHistory.accuracy_score.isnot(None)
        ).all()
        
        avg_accuracy = None
        if predictions:
            avg_accuracy = sum(p.accuracy_score for p in predictions) / len(predictions)
        
        return {
            "most_viewed_symbols": pattern.most_viewed_symbols,
            "preferred_asset_types": pattern.most_viewed_asset_types,
            "peak_hours": pattern.peak_usage_hours,
            "peak_days": pattern.peak_usage_days,
            "avg_session_minutes": round(pattern.average_session_duration, 1),
            "total_predictions": pattern.total_predictions_requested,
            "total_symbols_explored": pattern.total_unique_symbols_viewed,
            "prediction_accuracy": round(avg_accuracy, 2) if avg_accuracy else None,
            "member_since": pattern.first_activity.isoformat() if pattern.first_activity else None,
            "last_active": pattern.last_activity.isoformat() if pattern.last_activity else None
        }
    
    def get_confidence_boost(
        self,
        user_id: int,
        symbol: str,
        base_confidence: float
    ) -> Dict[str, Any]:
        """
        Calculate confidence boost based on user's history with a symbol.
        Users who frequently analyze a stock may benefit from pattern-based insights.
        """
        # Get user's view history for this symbol
        view = self.db.query(UserStockView).filter(
            UserStockView.user_id == user_id,
            UserStockView.symbol == symbol
        ).first()
        
        # Get user's prediction history for accuracy
        predictions = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.user_id == user_id,
            UserPredictionHistory.symbol == symbol,
            UserPredictionHistory.accuracy_score.isnot(None)
        ).all()
        
        boost = 0.0
        reasons = []
        
        # Familiarity boost (user knows this stock well)
        if view and view.view_count > 10:
            boost += 0.02
            reasons.append(f"High familiarity ({view.view_count} views)")
        
        # Historical accuracy boost
        if predictions:
            avg_accuracy = sum(p.accuracy_score for p in predictions) / len(predictions)
            if avg_accuracy > 0.7:
                boost += 0.03
                reasons.append(f"Good historical accuracy ({avg_accuracy:.0%})")
        
        # Cap the boost
        boost = min(boost, 0.05)
        
        return {
            "base_confidence": base_confidence,
            "boost": boost,
            "adjusted_confidence": min(base_confidence + boost, 0.99),
            "reasons": reasons
        }
