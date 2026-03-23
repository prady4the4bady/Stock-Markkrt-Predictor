"""Run the create_supabase_table.sql against DATABASE_URL from .env"""
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment (.env?)")

print("Using DATABASE_URL:", DATABASE_URL[:60] + "... (hidden)")
# Create engine with SSL for cloud Postgres (Supabase often requires sslmode=require)
connect_args = {}
if DATABASE_URL.startswith('postgres') or DATABASE_URL.startswith('postgresql'):
    connect_args = {"connect_timeout": 10, "sslmode": "require"}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

sql_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'create_supabase_table.sql')
with open(sql_path, 'r', encoding='utf-8') as f:
    sql = f.read()

# Retry loop to handle transient DNS/connect issues
import time
for attempt in range(1, 6):
    try:
        with engine.begin() as conn:
            print("Executing SQL to create predictions table...")
            conn.execute(text(sql))
            print("SQL executed successfully")
            break
    except Exception as e:
        print(f"Attempt {attempt} failed: {e}")
        if attempt < 5:
            print("Retrying in 5s...")
            time.sleep(5)
        else:
            print("All retries failed. Please check network/DATABASE_URL/credentials.")
            raise

print("Done")
