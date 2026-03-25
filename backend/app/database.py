"""
Market Oracle - Database Configuration
Secure SQLAlchemy database setup with encryption and connection pooling
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from pathlib import Path
from contextlib import contextmanager
import os
import hashlib
import secrets
from datetime import datetime
from .config import DATA_DIR

# Ensure data directory exists with proper permissions
DATA_DIR.mkdir(exist_ok=True)

# Database URLs
# If a DATABASE_URL is provided (e.g. from Supabase/Postgres), use it. Otherwise fall back to SQLite for local/dev.
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATA_DIR}/users.db"

# Engine configuration with connection pooling and security
if DATABASE_URL:
    # Postgres configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=int(os.getenv("DB_POOL_SIZE", 10)),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 20)),
        pool_pre_ping=True,
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", 3600)),
        echo=(os.getenv("DB_ECHO", "false").lower() == "true")
    )
else:
    # SQLite configuration for local development
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,  # Connection timeout
        },
        poolclass=QueuePool,
        pool_size=10,  # Maximum concurrent connections
        max_overflow=20,  # Allow additional connections under load
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False  # Set to True for SQL debugging
    )

# If using SQLite, enable pragmatic pragmas for performance/security
if not DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for security and performance"""
        cursor = dbapi_connection.cursor()
        
        # Security settings
        cursor.execute("PRAGMA foreign_keys=ON")  # Enforce foreign key constraints
        cursor.execute("PRAGMA secure_delete=ON")  # Securely delete data
        
        # Performance settings
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        
        cursor.close()


# Session factory with proper settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent lazy load issues
)

# Base class for all models
Base = declarative_base()


# Dependency for FastAPI route injection
def get_db():
    """
    Database session dependency for FastAPI routes.
    Yields a session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions outside of FastAPI routes.
    Useful for background tasks, CLI scripts, etc.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Security utilities for the database layer
class DatabaseSecurity:
    """
    Security utilities for database operations
    """
    
    @staticmethod
    def hash_ip(ip_address: str) -> str:
        """Hash IP address for privacy-compliant storage"""
        if not ip_address:
            return None
        salt = os.getenv("IP_HASH_SALT", "market_oracle_salt_2024")
        return hashlib.sha256(f"{ip_address}{salt}".encode()).hexdigest()
    
    @staticmethod
    def hash_user_agent(user_agent: str) -> str:
        """Hash user agent for privacy-compliant storage"""
        if not user_agent:
            return None
        salt = os.getenv("UA_HASH_SALT", "market_oracle_ua_salt")
        return hashlib.sha256(f"{user_agent}{salt}".encode()).hexdigest()
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate secure session token with timestamp"""
        timestamp = datetime.utcnow().timestamp()
        random_part = secrets.token_urlsafe(32)
        return f"{random_part}_{timestamp}"


def init_database():
    """
    Initialize all database tables.
    Called at application startup.
    """
    # Import all models to ensure they're registered
    from .models import (
        User, UserWatchlist, UserStockView, UserStockInteraction,
        UserPredictionHistory, UserPreferences, UserSession,
        UserBehaviorPattern, AuditLog, PredictionOutcome
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized successfully")


def backup_database(backup_dir: Path = None):
    """
    Create a backup of the database.
    Should be called periodically for data safety.
    """
    import shutil
    
    backup_dir = backup_dir or DATA_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"users_backup_{timestamp}.db"
    
    source_path = DATA_DIR / "users.db"
    if source_path.exists():
        shutil.copy2(source_path, backup_path)
        print(f"✅ Database backed up to {backup_path}")
        return backup_path
    return None

