"""
Market Oracle - Database Initialization Script
Run this script to initialize or reset the database with all tables.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import Base, engine, init_database, backup_database, DATA_DIR
from app.models import (
    User, UserWatchlist, UserStockView, UserStockInteraction,
    UserPredictionHistory, UserPreferences, UserSession,
    UserBehaviorPattern, AuditLog
)


def create_tables():
    """Create all database tables."""
    print("🔧 Creating database tables...")
    init_database()
    print("✅ All tables created successfully!")


def show_table_info():
    """Display information about all tables."""
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("\n📊 Database Tables:")
    print("=" * 60)
    
    for table in tables:
        columns = inspector.get_columns(table)
        indexes = inspector.get_indexes(table)
        
        print(f"\n📁 {table}")
        print("-" * 40)
        print("  Columns:")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"    - {col['name']}: {col['type']} ({nullable})")
        
        if indexes:
            print("  Indexes:")
            for idx in indexes:
                print(f"    - {idx['name']}: {idx['column_names']}")


def backup():
    """Create a backup of the database."""
    backup_path = backup_database()
    if backup_path:
        print(f"✅ Backup created: {backup_path}")
    else:
        print("❌ No database found to backup")


def reset_database():
    """Drop all tables and recreate them (WARNING: DATA LOSS!)"""
    confirm = input("⚠️ WARNING: This will delete ALL data. Type 'YES' to confirm: ")
    if confirm != 'YES':
        print("❌ Aborted.")
        return
    
    print("🔄 Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("🔧 Recreating tables...")
    create_tables()
    print("✅ Database reset complete!")


def show_stats():
    """Show database statistics."""
    from sqlalchemy.orm import Session
    from sqlalchemy import func
    
    with Session(engine) as session:
        print("\n📈 Database Statistics:")
        print("=" * 60)
        
        users = session.query(func.count(User.id)).scalar()
        watchlist = session.query(func.count(UserWatchlist.id)).scalar()
        views = session.query(func.count(UserStockView.id)).scalar()
        interactions = session.query(func.count(UserStockInteraction.id)).scalar()
        predictions = session.query(func.count(UserPredictionHistory.id)).scalar()
        
        print(f"  Users: {users}")
        print(f"  Watchlist Items: {watchlist}")
        print(f"  Stock Views: {views}")
        print(f"  Interactions: {interactions}")
        print(f"  Predictions Tracked: {predictions}")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════╗
    ║       🗄️  MARKET ORACLE - DATABASE MANAGER       ║
    ╚══════════════════════════════════════════════════╝
    """)
    
    print(f"Database location: {DATA_DIR / 'users.db'}")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "init":
            create_tables()
        elif command == "info":
            show_table_info()
        elif command == "backup":
            backup()
        elif command == "reset":
            reset_database()
        elif command == "stats":
            show_stats()
        else:
            print(f"Unknown command: {command}")
    else:
        print("""
Usage:
  python init_database.py init     - Create all tables
  python init_database.py info     - Show table information
  python init_database.py backup   - Create database backup
  python init_database.py reset    - Reset database (WARNING: deletes all data!)
  python init_database.py stats    - Show database statistics
        """)
        
        # Default: Initialize if not exists
        db_path = DATA_DIR / "users.db"
        if not db_path.exists():
            print("\n🆕 Database not found. Creating new database...")
            create_tables()
        else:
            print("\n✅ Database already exists.")
            show_stats()
