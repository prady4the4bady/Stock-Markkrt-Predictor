"""
Market Oracle - User Analytics Engine
Analyzes user behavior patterns to enhance prediction confidence
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
import json

from .models import (
    User, UserStockView, UserStockInteraction, 
    UserPredictionHistory, UserBehaviorPattern, UserWatchlist
)


class UserAnalyticsEngine:
    """
    Advanced analytics engine that analyzes user behavior
    to improve prediction confidence and provide insights.
    """
    
    # Sector mappings for stocks
    SECTOR_MAP = {
        # US Technology
        "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
        "AMZN": "Technology", "META": "Technology", "NVDA": "Technology",
        "AMD": "Technology", "INTC": "Technology", "NFLX": "Technology",
        # US Finance
        "JPM": "Finance", "V": "Finance", "MA": "Finance", "BAC": "Finance",
        # US Consumer
        "WMT": "Consumer", "KO": "Consumer", "PG": "Consumer", "DIS": "Consumer",
        # US Healthcare
        "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare",
        # Crypto
        "BTC/USDT": "Crypto", "ETH/USDT": "Crypto", "SOL/USDT": "Crypto",
        "XRP/USDT": "Crypto", "ADA/USDT": "Crypto", "DOGE/USDT": "Crypto",
        # Indian Technology
        "TCS.NS": "Technology", "INFY.NS": "Technology", "WIPRO.NS": "Technology",
        "HCLTECH.NS": "Technology", "TECHM.NS": "Technology",
        # Indian Finance
        "HDFCBANK.NS": "Finance", "ICICIBANK.NS": "Finance", "SBIN.NS": "Finance",
        "KOTAKBANK.NS": "Finance", "AXISBANK.NS": "Finance", "INDUSINDBK.NS": "Finance",
        "BAJFINANCE.NS": "Finance", "BAJAJFINSV.NS": "Finance",
        "SBILIFE.NS": "Finance", "HDFCLIFE.NS": "Finance",
        # Indian Energy & Industrial
        "RELIANCE.NS": "Energy", "ONGC.NS": "Energy", "NTPC.NS": "Energy",
        "POWERGRID.NS": "Energy", "BPCL.NS": "Energy", "COALINDIA.NS": "Energy",
        "LT.NS": "Industrial", "ADANIENT.NS": "Industrial", "ADANIPORTS.NS": "Industrial",
        # Indian Consumer
        "HINDUNILVR.NS": "Consumer", "ITC.NS": "Consumer", "NESTLEIND.NS": "Consumer",
        "BRITANNIA.NS": "Consumer", "TATACONSUM.NS": "Consumer", "ASIANPAINT.NS": "Consumer",
        "TITAN.NS": "Consumer", "MARUTI.NS": "Consumer", "EICHERMOT.NS": "Consumer",
        "HEROMOTOCO.NS": "Consumer", "TATAMOTORS.NS": "Consumer", "M&M.NS": "Consumer",
        # Indian Healthcare
        "SUNPHARMA.NS": "Healthcare", "DRREDDY.NS": "Healthcare", "DIVISLAB.NS": "Healthcare",
        "CIPLA.NS": "Healthcare", "APOLLOHOSP.NS": "Healthcare",
        # Indian Telecom
        "BHARTIARTL.NS": "Telecom",
        # Indian Materials
        "TATASTEEL.NS": "Materials", "JSWSTEEL.NS": "Materials", "HINDALCO.NS": "Materials",
        "ULTRACEMCO.NS": "Materials", "SHREECEM.NS": "Materials", "GRASIM.NS": "Materials",
        "UPL.NS": "Materials",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_expertise_score(self, user_id: int, symbol: str) -> Dict[str, Any]:
        """
        Calculate a user's expertise score for a specific symbol.
        Higher expertise may indicate better understanding of the asset.
        """
        # Get view history
        view = self.db.query(UserStockView).filter(
            UserStockView.user_id == user_id,
            UserStockView.symbol == symbol
        ).first()
        
        # Get prediction history with accuracy
        predictions = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.user_id == user_id,
            UserPredictionHistory.symbol == symbol
        ).all()
        
        scores = {
            "view_score": 0.0,
            "prediction_score": 0.0,
            "accuracy_score": 0.0,
            "overall_expertise": 0.0,
            "confidence_modifier": 0.0
        }
        
        # View-based expertise (0-30 points)
        if view:
            # More views = more familiarity
            view_points = min(view.view_count * 2, 20)
            # Time spent also matters
            time_points = min(view.total_view_duration_seconds / 600, 10)  # 10min cap
            scores["view_score"] = view_points + time_points
        
        # Prediction-based expertise (0-30 points)
        if predictions:
            # More predictions = more engagement
            pred_points = min(len(predictions) * 3, 20)
            scores["prediction_score"] = pred_points
            
            # Accuracy score (0-40 points)
            accurate_preds = [p for p in predictions if p.accuracy_score is not None]
            if accurate_preds:
                avg_accuracy = sum(p.accuracy_score for p in accurate_preds) / len(accurate_preds)
                scores["accuracy_score"] = avg_accuracy * 40
        
        # Calculate overall expertise (0-100)
        scores["overall_expertise"] = (
            scores["view_score"] + 
            scores["prediction_score"] + 
            scores["accuracy_score"]
        )
        
        # Confidence modifier (+0% to +5%)
        if scores["overall_expertise"] > 50:
            scores["confidence_modifier"] = min(
                (scores["overall_expertise"] - 50) / 10 * 0.01,
                0.05
            )
        
        return scores
    
    def get_sector_expertise(self, user_id: int) -> Dict[str, float]:
        """
        Calculate user's expertise by sector.
        Returns a dict of sector -> expertise score (0-100)
        """
        views = self.db.query(UserStockView).filter(
            UserStockView.user_id == user_id
        ).all()
        
        sector_scores = defaultdict(lambda: {"views": 0, "duration": 0})
        
        for view in views:
            sector = self.SECTOR_MAP.get(view.symbol, "Other")
            sector_scores[sector]["views"] += view.view_count
            sector_scores[sector]["duration"] += view.total_view_duration_seconds
        
        # Normalize to 0-100
        max_views = max((s["views"] for s in sector_scores.values()), default=1)
        max_duration = max((s["duration"] for s in sector_scores.values()), default=1)
        
        result = {}
        for sector, data in sector_scores.items():
            view_score = (data["views"] / max_views) * 50
            duration_score = (data["duration"] / max_duration) * 50
            result[sector] = round(view_score + duration_score, 1)
        
        return result
    
    def get_user_activity_timeline(
        self,
        user_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get user's activity timeline for the past N days.
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        interactions = self.db.query(UserStockInteraction).filter(
            UserStockInteraction.user_id == user_id,
            UserStockInteraction.started_at >= since
        ).order_by(desc(UserStockInteraction.started_at)).all()
        
        timeline = []
        for interaction in interactions:
            timeline.append({
                "date": interaction.started_at.strftime("%Y-%m-%d"),
                "symbol": interaction.symbol,
                "asset_type": interaction.asset_type,
                "duration_minutes": round((interaction.duration_seconds or 0) / 60, 1),
                "prediction_requested": interaction.prediction_requested,
                "prediction_days": interaction.prediction_days
            })
        
        return timeline
    
    def get_activity_heatmap(self, user_id: int) -> Dict[str, Any]:
        """
        Generate activity heatmap data (hour x day of week).
        """
        interactions = self.db.query(UserStockInteraction).filter(
            UserStockInteraction.user_id == user_id
        ).all()
        
        # Initialize 24x7 matrix
        heatmap = np.zeros((24, 7))
        
        for interaction in interactions:
            hour = interaction.started_at.hour
            day = interaction.started_at.weekday()
            heatmap[hour][day] += 1
        
        return {
            "matrix": heatmap.tolist(),
            "hours": list(range(24)),
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "total_interactions": len(interactions)
        }
    
    def get_prediction_accuracy_report(
        self,
        user_id: int,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate detailed accuracy report for user's predictions.
        """
        query = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.user_id == user_id
        )
        
        if symbol:
            query = query.filter(UserPredictionHistory.symbol == symbol)
        
        predictions = query.all()
        
        total = len(predictions)
        with_accuracy = [p for p in predictions if p.accuracy_score is not None]
        
        if not with_accuracy:
            return {
                "total_predictions": total,
                "evaluated_predictions": 0,
                "pending_evaluation": total,
                "average_accuracy": None,
                "accuracy_by_symbol": {},
                "accuracy_by_days": {}
            }
        
        # Overall accuracy
        avg_accuracy = sum(p.accuracy_score for p in with_accuracy) / len(with_accuracy)
        
        # By symbol
        symbol_accuracy = defaultdict(list)
        for p in with_accuracy:
            symbol_accuracy[p.symbol].append(p.accuracy_score)
        
        accuracy_by_symbol = {
            sym: round(sum(scores) / len(scores), 3)
            for sym, scores in symbol_accuracy.items()
        }
        
        # By prediction days
        days_accuracy = defaultdict(list)
        for p in with_accuracy:
            days_accuracy[p.prediction_days].append(p.accuracy_score)
        
        accuracy_by_days = {
            days: round(sum(scores) / len(scores), 3)
            for days, scores in days_accuracy.items()
        }
        
        return {
            "total_predictions": total,
            "evaluated_predictions": len(with_accuracy),
            "pending_evaluation": total - len(with_accuracy),
            "average_accuracy": round(avg_accuracy, 3),
            "accuracy_by_symbol": accuracy_by_symbol,
            "accuracy_by_days": accuracy_by_days
        }
    
    def suggest_stocks(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Suggest stocks based on user's viewing patterns and sector interests.
        """
        from .config import DEFAULT_STOCKS, DEFAULT_CRYPTO
        
        # Get sector expertise
        sector_scores = self.get_sector_expertise(user_id)
        
        # Get already viewed stocks
        viewed = self.db.query(UserStockView.symbol).filter(
            UserStockView.user_id == user_id
        ).all()
        viewed_symbols = {v.symbol for v in viewed}
        
        # Get watchlist
        watchlist = self.db.query(UserWatchlist.symbol).filter(
            UserWatchlist.user_id == user_id,
            UserWatchlist.is_active == True
        ).all()
        watchlist_symbols = {w.symbol for w in watchlist}
        
        suggestions = []
        
        # Find top sectors
        top_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for sector, score in top_sectors:
            # Find stocks in this sector not yet viewed
            for symbol, sym_sector in self.SECTOR_MAP.items():
                if sym_sector == sector and symbol not in viewed_symbols:
                    suggestions.append({
                        "symbol": symbol,
                        "sector": sector,
                        "reason": f"Based on your interest in {sector}",
                        "in_watchlist": symbol in watchlist_symbols,
                        "sector_score": score
                    })
        
        # If not enough suggestions, add popular ones
        popular = ["AAPL", "TSLA", "NVDA", "BTC/USDT", "ETH/USDT"]
        for symbol in popular:
            if symbol not in viewed_symbols and len(suggestions) < limit * 2:
                suggestions.append({
                    "symbol": symbol,
                    "sector": self.SECTOR_MAP.get(symbol, "Other"),
                    "reason": "Popular choice",
                    "in_watchlist": symbol in watchlist_symbols,
                    "sector_score": 0
                })
        
        # Sort by relevance and return top N
        suggestions.sort(key=lambda x: x["sector_score"], reverse=True)
        return suggestions[:limit]
    
    def get_comprehensive_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive analytics dashboard for a user.
        """
        # Basic stats
        total_views = self.db.query(func.sum(UserStockView.view_count)).filter(
            UserStockView.user_id == user_id
        ).scalar() or 0
        
        total_symbols = self.db.query(UserStockView).filter(
            UserStockView.user_id == user_id
        ).count()
        
        total_predictions = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.user_id == user_id
        ).count()
        
        watchlist_count = self.db.query(UserWatchlist).filter(
            UserWatchlist.user_id == user_id,
            UserWatchlist.is_active == True
        ).count()
        
        # Time-based analysis
        first_activity = self.db.query(func.min(UserStockInteraction.started_at)).filter(
            UserStockInteraction.user_id == user_id
        ).scalar()
        
        last_activity = self.db.query(func.max(UserStockInteraction.started_at)).filter(
            UserStockInteraction.user_id == user_id
        ).scalar()
        
        days_active = 0
        if first_activity and last_activity:
            days_active = (last_activity - first_activity).days + 1
        
        return {
            "overview": {
                "total_views": total_views,
                "unique_symbols": total_symbols,
                "total_predictions": total_predictions,
                "watchlist_size": watchlist_count,
                "days_active": days_active,
                "first_activity": first_activity.isoformat() if first_activity else None,
                "last_activity": last_activity.isoformat() if last_activity else None
            },
            "sector_expertise": self.get_sector_expertise(user_id),
            "activity_heatmap": self.get_activity_heatmap(user_id),
            "accuracy_report": self.get_prediction_accuracy_report(user_id),
            "suggestions": self.suggest_stocks(user_id),
            "recent_activity": self.get_user_activity_timeline(user_id, days=7)
        }


class PredictionAccuracyTracker:
    """
    Background service to compute prediction accuracy
    when the predicted dates have passed.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_pending_accuracies(self, data_manager) -> int:
        """
        Find predictions that need accuracy computation and update them.
        Returns the count of updated predictions.
        """
        today = datetime.utcnow().date()
        
        # Find predictions where:
        # 1. accuracy_score is null
        # 2. The last predicted date has passed
        pending = self.db.query(UserPredictionHistory).filter(
            UserPredictionHistory.accuracy_score.is_(None)
        ).all()
        
        updated_count = 0
        
        for prediction in pending:
            # Check if all predicted dates have passed
            predicted_dates = prediction.predicted_dates
            if not predicted_dates:
                continue
            
            last_date = datetime.strptime(predicted_dates[-1], "%Y-%m-%d").date()
            if last_date >= today:
                continue  # Not yet ready for evaluation
            
            try:
                # Fetch actual prices for the predicted dates
                is_crypto = prediction.asset_type == "crypto"
                df = data_manager.fetch_stock_data(prediction.symbol) if not is_crypto \
                    else data_manager.fetch_crypto_data(prediction.symbol)
                
                if df.empty:
                    continue
                
                # Convert to dict for easy lookup
                df['timestamp'] = df['timestamp'].astype(str)
                price_map = dict(zip(df['timestamp'], df['close']))
                
                # Get actual prices
                actual_prices = []
                predicted_prices = prediction.predicted_prices
                
                for date in predicted_dates:
                    if date in price_map:
                        actual_prices.append(price_map[date])
                    else:
                        actual_prices.append(None)
                
                # Compute accuracy (MAPE-based)
                if all(p is not None for p in actual_prices):
                    errors = []
                    for pred, actual in zip(predicted_prices, actual_prices):
                        if actual > 0:
                            error = abs(pred - actual) / actual
                            errors.append(error)
                    
                    if errors:
                        mape = sum(errors) / len(errors)
                        # Convert to accuracy score (1 - MAPE, capped at 0)
                        accuracy = max(0, 1 - mape)
                        
                        prediction.actual_prices = actual_prices
                        prediction.accuracy_score = round(accuracy, 4)
                        prediction.outcome_computed_at = datetime.utcnow()
                        updated_count += 1
                
            except Exception as e:
                print(f"Error computing accuracy for prediction {prediction.id}: {e}")
                continue
        
        if updated_count > 0:
            self.db.commit()
        
        return updated_count
