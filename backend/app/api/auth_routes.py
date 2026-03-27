from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Optional
from pydantic import BaseModel, model_validator

from ..database import get_db
from ..models.user import User
from ..auth import (
    create_access_token, get_password_hash, 
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user,
    verify_password
)

router = APIRouter()

# Pydantic models for request body
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    privacy_consent: bool = False  # Required checkbox for privacy policy
    terms_accepted: bool = False   # Required checkbox for terms of service
    activity_tracking_consent: bool = False  # Optional checkbox for activity tracking

class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str] = None   # mirrors full_name for frontend compatibility
    full_name: Optional[str] = None
    is_premium: bool = False
    subscription_plan: str = "free"
    privacy_consent: bool = False
    terms_accepted: bool = False

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _set_username(self):
        if self.username is None:
            self.username = self.full_name
        return self

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Validate required consents
    if not user.privacy_consent:
        raise HTTPException(status_code=400, detail="You must accept the Privacy Policy to create an account")
    if not user.terms_accepted:
        raise HTTPException(status_code=400, detail="You must accept the Terms of Service to create an account")
    
    # Normalize email: lowercase + strip whitespace — must match login lookup
    normalized_email = user.email.strip().lower()

    db_user = db.query(User).filter(User.email == normalized_email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate password length and enforce minimum length
    password_bytes = user.password.encode('utf-8')
    print(f"[RegisterDebug] Received registration for {normalized_email} - bytes length: {len(password_bytes)}")
    if len(password_bytes) > 72:
        print(f"[RegisterDebug] Password bytes length {len(password_bytes)} exceeds 72")
        raise HTTPException(status_code=400, detail="Password too long (max 72 bytes). Please use a shorter password.")
    if len(password_bytes) < 8:
        print(f"[RegisterDebug] Password bytes length {len(password_bytes)} below minimum")
        raise HTTPException(status_code=400, detail="Password too short (minimum 8 characters).")


    try:
        hashed_password = get_password_hash(user.password)
    except Exception as e:
        # Log non-sensitive diagnostics for investigation
        password_bytes = user.password.encode('utf-8') if isinstance(user.password, str) else b''
        bytes_len = len(password_bytes)
        p_type = type(user.password).__name__
        print(f"[Register] Hashing error for {user.email}: {e} | type={p_type} | bytes_len={bytes_len}")
        # Return a generic error to the client to avoid leaking diagnostics
        raise HTTPException(status_code=400, detail="Password hashing error")

    new_user = User(
        email=normalized_email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        privacy_consent=user.privacy_consent,
        privacy_consent_date=datetime.utcnow(),
        terms_accepted=user.terms_accepted,
        terms_accepted_date=datetime.utcnow()
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        print(f"[Register] User commit error for {user.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create account. Please try again.")

    # Create user preferences — use upsert (get-or-create) to survive recycled IDs
    from ..models import UserPreferences
    try:
        existing_prefs = db.query(UserPreferences).filter(
            UserPreferences.user_id == new_user.id
        ).first()
        if existing_prefs:
            # Orphan row from a previous deleted user — update it for the new owner
            existing_prefs.track_activity = user.activity_tracking_consent
        else:
            db.add(UserPreferences(
                user_id=new_user.id,
                track_activity=user.activity_tracking_consent
            ))
        db.commit()
    except Exception as prefs_err:
        db.rollback()
        # Preferences failure is non-fatal — user was created; log and continue
        print(f"[Register] Preferences error for user {new_user.id}: {prefs_err}")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": new_user
    }

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    normalized_email = form_data.username.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Track failed login attempts
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    db.commit()
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


class RefreshRequest(BaseModel):
    token: str


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    from ..auth import refresh_access_token
    new_token = refresh_access_token(body.token)
    if not new_token:
        raise HTTPException(status_code=401, detail="Token invalid or expired")
    return {"access_token": new_token, "token_type": "bearer"}
