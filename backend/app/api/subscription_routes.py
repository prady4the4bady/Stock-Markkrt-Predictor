"""
Market Oracle - Subscription Routes
PayPal subscription management for premium features
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import httpx
import os

from ..database import get_db
from ..models.user import User
from .auth_routes import get_current_active_user

router = APIRouter(prefix="/api/subscription", tags=["subscription"])

# PayPal Configuration - Set these in environment variables for production
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox or live

PAYPAL_API_URL = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "features": [
            "3 predictions per day",
            "1-hour forecast only",
            "Basic chart (1h range)",
            "1 watchlist slot",
            "Delayed data (15 min)",
            "No model insights"
        ],
        "predictions_per_day": 3,
        "watchlist_limit": 1,
        "max_forecast_days": 0.04,  # 1 hour only
        "allowed_ranges": ["1h"],
        "show_model_weights": False,
        "show_confidence_details": False,
        "show_technical_indicators": False,
        "realtime_data": False,
        "export_enabled": False
    },
    "pro": {
        "name": "Pro",
        "price": 9.99,
        "paypal_plan_id": os.getenv("PAYPAL_PRO_PLAN_ID", ""),
        "features": [
            "50 predictions per day",
            "Up to 7-day forecasts",
            "All chart ranges",
            "10 watchlist slots",
            "Real-time data",
            "Model confidence scores",
            "Basic technical indicators",
            "Export to CSV"
        ],
        "predictions_per_day": 50,
        "watchlist_limit": 10,
        "max_forecast_days": 7,
        "allowed_ranges": ["1h", "12h", "1d", "1w", "1mo", "3mo"],
        "show_model_weights": True,
        "show_confidence_details": True,
        "show_technical_indicators": True,
        "realtime_data": True,
        "export_enabled": True
    },
    "elite": {
        "name": "Elite",
        "price": 24.99,
        "paypal_plan_id": os.getenv("PAYPAL_ELITE_PLAN_ID", ""),
        "features": [
            "Unlimited predictions",
            "Up to 30-day forecasts",
            "All chart ranges + Max",
            "Unlimited watchlist",
            "Real-time data",
            "Full model access & weights",
            "All technical indicators",
            "API access",
            "Priority support 24/7",
            "Custom alerts"
        ],
        "predictions_per_day": -1,  # Unlimited
        "watchlist_limit": -1,  # Unlimited
        "max_forecast_days": 30,
        "allowed_ranges": ["1h", "12h", "1d", "1w", "1mo", "3mo", "6mo", "1y", "5y"],
        "show_model_weights": True,
        "show_confidence_details": True,
        "show_technical_indicators": True,
        "realtime_data": True,
        "export_enabled": True
    }
}


class SubscriptionRequest(BaseModel):
    plan: str
    subscription_id: Optional[str] = None


class PayPalOrderRequest(BaseModel):
    plan: str


async def get_paypal_access_token():
    """Get PayPal OAuth access token"""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="PayPal not configured")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYPAL_API_URL}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to authenticate with PayPal")
        
        return response.json()["access_token"]


@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    return {
        "plans": SUBSCRIPTION_PLANS,
        "paypal_client_id": PAYPAL_CLIENT_ID if PAYPAL_CLIENT_ID else None
    }


@router.get("/status")
async def get_subscription_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status with limits"""
    plan = current_user.subscription_plan or "free"
    plan_details = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["free"])
    
    is_active = True
    if current_user.subscription_end:
        is_active = current_user.subscription_end > datetime.utcnow()
        if not is_active:
            # Subscription expired, revert to free
            current_user.subscription_plan = "free"
            current_user.is_premium = False
            db.commit()
            plan = "free"
            plan_details = SUBSCRIPTION_PLANS["free"]
    
    # Get today's prediction count
    today = datetime.utcnow().date()
    predictions_today = current_user.predictions_today or 0
    last_prediction_date = current_user.last_prediction_date
    
    # Reset count if it's a new day
    if last_prediction_date:
        # Handle both date and datetime objects
        last_date = last_prediction_date.date() if hasattr(last_prediction_date, 'date') else last_prediction_date
        if last_date < today:
            predictions_today = 0
    
    # Build limits object for frontend
    limits = {
        "predictions_per_day": plan_details.get("predictions_per_day", 3),
        "watchlist_limit": plan_details.get("watchlist_limit", 1),
        "max_forecast_days": plan_details.get("max_forecast_days", 0.04),
        "allowed_ranges": plan_details.get("allowed_ranges", ["1h"]),
        "show_model_weights": plan_details.get("show_model_weights", False),
        "show_confidence_details": plan_details.get("show_confidence_details", False),
        "show_technical_indicators": plan_details.get("show_technical_indicators", False),
        "realtime_data": plan_details.get("realtime_data", False),
        "export_enabled": plan_details.get("export_enabled", False)
    }
    
    return {
        "plan": plan,
        "plan_name": plan_details.get("name", "Free"),
        "is_premium": current_user.is_premium,
        "subscription_end": current_user.subscription_end.isoformat() if current_user.subscription_end else None,
        "is_active": is_active,
        "predictions_today": predictions_today,
        "limits": limits
    }


@router.post("/create-order")
async def create_paypal_order(
    request: PayPalOrderRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create a PayPal checkout order for a subscription plan (30-day access)"""
    plan = request.plan
    if plan not in SUBSCRIPTION_PLANS or plan == "free":
        raise HTTPException(status_code=400, detail="Invalid plan")

    plan_details = SUBSCRIPTION_PLANS[plan]
    price = plan_details["price"]
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    try:
        access_token = await get_paypal_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYPAL_API_URL}/v2/checkout/orders",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "amount": {
                            "currency_code": "USD",
                            "value": f"{price:.2f}"
                        },
                        "description": f"NexusTrader {plan_details['name']} Plan - 30 Day Access",
                        "custom_id": f"{current_user.id}:{plan}"
                    }],
                    "application_context": {
                        "brand_name": "NexusTrader",
                        "locale": "en-US",
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                        "return_url": f"{frontend_url}/subscription/success?plan={plan}",
                        "cancel_url": f"{frontend_url}/subscription"
                    }
                }
            )

            if response.status_code not in [200, 201]:
                print(f"PayPal error: {response.text}")
                raise HTTPException(status_code=500, detail="Failed to create PayPal order")

            order_data = response.json()
            approve_link = next(
                (link for link in order_data.get("links", []) if link.get("rel") == "approve"),
                None
            )

            return {
                "order_id": order_data.get("id"),
                "status": order_data.get("status"),
                "links": order_data.get("links", []),
                "approve_url": approve_link.get("href") if approve_link else None
            }

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"PayPal request failed: {str(e)}")


@router.post("/capture-order/{order_id}")
async def capture_paypal_order(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Capture a PayPal checkout order after user approval"""
    try:
        access_token = await get_paypal_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }
            )

            if response.status_code not in [200, 201]:
                print(f"PayPal capture error: {response.text}")
                raise HTTPException(status_code=500, detail="Failed to capture PayPal order")

            capture_data = response.json()

            if capture_data.get("status") != "COMPLETED":
                raise HTTPException(status_code=400, detail="Payment not completed")

            # Determine plan from custom_id (preferred) or amount (fallback)
            purchase_unit = capture_data["purchase_units"][0]
            custom_id = purchase_unit.get("custom_id", "")
            plan = None

            if ":" in custom_id:
                # Format: "{user_id}:{plan}"
                _, plan_from_id = custom_id.split(":", 1)
                if plan_from_id in SUBSCRIPTION_PLANS and plan_from_id != "free":
                    plan = plan_from_id

            if not plan:
                # Fallback: determine plan from captured amount
                amount = float(purchase_unit["payments"]["captures"][0]["amount"]["value"])
                plan = "elite" if amount >= 24 else "pro"

            # Update user subscription (30-day access)
            current_user.subscription_plan = plan
            current_user.is_premium = True
            current_user.subscription_end = datetime.utcnow() + timedelta(days=30)
            db.commit()

            return {
                "status": "success",
                "plan": plan,
                "subscription_end": current_user.subscription_end.isoformat(),
                "message": f"Successfully subscribed to {SUBSCRIPTION_PLANS[plan]['name']} plan!"
            }

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"PayPal request failed: {str(e)}")


@router.post("/activate")
async def activate_subscription(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Activate subscription after PayPal approval — verifies subscription_id with PayPal if provided"""
    plan = request.plan
    subscription_id = request.subscription_id

    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    if plan == "free":
        current_user.subscription_plan = "free"
        current_user.is_premium = False
        current_user.subscription_end = None
        db.commit()
        return {
            "status": "success",
            "plan": "free",
            "subscription_end": None,
            "features": SUBSCRIPTION_PLANS["free"]["features"]
        }

    # Verify PayPal subscription if a subscription_id is provided
    if subscription_id and PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET:
        try:
            access_token = await get_paypal_access_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{PAYPAL_API_URL}/v1/billing/subscriptions/{subscription_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
            if resp.status_code == 200:
                sub = resp.json()
                status = sub.get("status", "")
                if status not in ("ACTIVE", "APPROVED"):
                    raise HTTPException(status_code=400, detail=f"PayPal subscription status: {status}")
                # Confirm subscriber email matches current user
                subscriber_email = sub.get("subscriber", {}).get("email_address", "")
                if subscriber_email and subscriber_email.lower() != current_user.email.lower():
                    raise HTTPException(status_code=403, detail="Subscription belongs to a different account")
            else:
                # Subscription lookup failed — don't silently activate
                raise HTTPException(status_code=400, detail="Could not verify PayPal subscription")
        except HTTPException:
            raise
        except Exception as e:
            print(f"[PayPal verify] {e}")
            raise HTTPException(status_code=500, detail="PayPal verification failed")

    # Activate subscription
    current_user.subscription_plan = plan
    current_user.is_premium = True
    current_user.subscription_end = datetime.utcnow() + timedelta(days=30)
    db.commit()

    return {
        "status": "success",
        "plan": plan,
        "subscription_end": current_user.subscription_end.isoformat(),
        "features": SUBSCRIPTION_PLANS[plan]["features"]
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel subscription (will remain active until end date)"""
    if current_user.subscription_plan == "free":
        raise HTTPException(status_code=400, detail="No active subscription to cancel")
    
    # In production, also cancel PayPal subscription
    # For now, just mark for non-renewal (keep active until subscription_end)
    
    return {
        "status": "cancelled",
        "message": "Subscription cancelled. You will retain access until " + 
                   (current_user.subscription_end.strftime("%Y-%m-%d") if current_user.subscription_end else "end of period"),
        "subscription_end": current_user.subscription_end.isoformat() if current_user.subscription_end else None
    }


class PredictionCheckRequest(BaseModel):
    forecast_days: float
    range_period: str


@router.post("/check-prediction")
async def check_prediction_limit(
    request: PredictionCheckRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if user can make a prediction and validate parameters"""
    plan = current_user.subscription_plan or "free"
    plan_details = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["free"])
    
    # Reset daily count if new day
    today = datetime.utcnow().date()
    last_pred_date = current_user.last_prediction_date
    # Handle both date and datetime objects
    if last_pred_date:
        last_date = last_pred_date.date() if hasattr(last_pred_date, 'date') else last_pred_date
    else:
        last_date = None
    
    if last_date != today:
        current_user.predictions_today = 0
        current_user.last_prediction_date = today
        db.commit()
    
    predictions_per_day = plan_details.get("predictions_per_day", 3)
    max_forecast_days = plan_details.get("max_forecast_days", 0.04)
    allowed_ranges = plan_details.get("allowed_ranges", ["1h"])
    
    errors = []
    upgrade_reasons = []
    
    # Check daily limit
    if predictions_per_day != -1 and current_user.predictions_today >= predictions_per_day:
        errors.append(f"Daily prediction limit reached ({predictions_per_day}/day)")
        upgrade_reasons.append("unlimited_predictions")
    
    # Check forecast period
    if max_forecast_days != -1 and request.forecast_days > max_forecast_days:
        if max_forecast_days == 0.04:
            errors.append("Free plan only allows 1-hour forecasts")
        else:
            errors.append(f"Your plan allows up to {max_forecast_days} day forecasts")
        upgrade_reasons.append("longer_forecasts")
    
    # Check range period
    if request.range_period not in allowed_ranges:
        errors.append(f"Range '{request.range_period}' not available on your plan")
        upgrade_reasons.append("more_ranges")
    
    if errors:
        return {
            "allowed": False,
            "errors": errors,
            "upgrade_reasons": upgrade_reasons,
            "remaining_predictions": max(0, predictions_per_day - current_user.predictions_today) if predictions_per_day != -1 else -1
        }
    
    return {
        "allowed": True,
        "remaining_predictions": (predictions_per_day - current_user.predictions_today - 1) if predictions_per_day != -1 else -1
    }


@router.post("/use-prediction")
async def use_prediction(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Record a prediction use (called after successful prediction)"""
    plan = current_user.subscription_plan or "free"
    plan_details = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["free"])
    predictions_per_day = plan_details.get("predictions_per_day", 3)
    
    # Reset daily count if new day
    today = datetime.utcnow().date()
    last_pred_date = current_user.last_prediction_date
    # Handle both date and datetime objects
    if last_pred_date:
        last_date = last_pred_date.date() if hasattr(last_pred_date, 'date') else last_pred_date
    else:
        last_date = None
    
    if last_date != today:
        current_user.predictions_today = 0
        current_user.last_prediction_date = today
    
    # Increment counter (unless unlimited)
    if predictions_per_day != -1:
        current_user.predictions_today = (current_user.predictions_today or 0) + 1
    
    db.commit()
    
    return {
        "predictions_today": current_user.predictions_today,
        "remaining": max(0, predictions_per_day - current_user.predictions_today) if predictions_per_day != -1 else -1
    }


@router.post("/webhook")
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle PayPal webhooks for subscription events"""
    try:
        body = await request.json()
        event_type = body.get("event_type", "")
        
        # Handle different webhook events
        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            # Subscription activated
            subscription = body.get("resource", {})
            subscriber_email = subscription.get("subscriber", {}).get("email_address")
            
            if subscriber_email:
                user = db.query(User).filter(User.email == subscriber_email).first()
                if user:
                    # Determine plan from subscription
                    plan_id = subscription.get("plan_id", "")
                    if plan_id == os.getenv("PAYPAL_ELITE_PLAN_ID"):
                        user.subscription_plan = "elite"
                    else:
                        user.subscription_plan = "pro"
                    user.is_premium = True
                    user.subscription_end = datetime.utcnow() + timedelta(days=30)
                    db.commit()
        
        elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            # Subscription cancelled
            subscription = body.get("resource", {})
            subscriber_email = subscription.get("subscriber", {}).get("email_address")
            
            if subscriber_email:
                user = db.query(User).filter(User.email == subscriber_email).first()
                if user:
                    # Keep access until subscription_end, then revert to free
                    pass  # Access maintained until expiry
        
        elif event_type == "PAYMENT.SALE.COMPLETED":
            # Recurring payment completed
            subscription = body.get("resource", {})
            # Extend subscription
        
        return {"status": "received"}
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}
