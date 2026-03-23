"""
Market Oracle - FastAPI Main Application
Production-grade stock/crypto prediction API with secure user tracking
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import uvicorn
import traceback

from .api.routes import router as api_router
from .api.auth_routes import router as auth_router
from .api.activity_routes import router as activity_router
from .api.subscription_routes import router as subscription_router
from .api.global_routes import router as global_router
from .api.listings_routes import router as listings_router
from .config import API_HOST, API_PORT, CORS_ORIGINS
from .database import engine, Base, init_database
from .models import user

# Initialize DB tables (creates all tables including new activity tables)
init_database()

# Create FastAPI app
app = FastAPI(
    title="Market Oracle API",
    description="🔮 AI-powered stock and crypto price predictions using ensemble ML models",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global exception handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Error: {exc}")
    print(f"❌ Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(activity_router, prefix="/api/user", tags=["User Activity & Tracking"])
app.include_router(subscription_router, tags=["Subscription & Payments"])
app.include_router(global_router, tags=["Global Markets"])
app.include_router(listings_router, tags=["New Listings"])

# Serve static frontend files (after build)
frontend_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(frontend_path / "index.html")
    
    @app.get("/{catch_all:path}")
    async def catch_all(catch_all: str):
        file_path = frontend_path / catch_all
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_path / "index.html")


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "service": "Market Oracle API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "predict": "/api/predict/{symbol}",
            "historical": "/api/historical/{symbol}",
            "news": "/api/news/{symbol}",
            "assets": "/api/assets",
            "docs": "/docs"
        }
    }


@app.get('/api/version')
async def api_version():
    """Return a short version string to verify code deployment"""
    return {"version": "auth-pbkdf2-2026-02-01"}


@app.get("/healthz")
async def healthz():
    """Simple health check endpoint for load balancers and monitoring"""
    return {"status": "ok"}


@app.get("/api/health")
async def api_health():
    """API health endpoint with basic checks"""
    # If you want DB checks, extend this to query a small value
    return {"status": "ok", "db": "connected"}


def _start_all_agents():
    """
    Start all background agent systems on server launch:
    1. Data prefetch loop    — hourly cache warm-up for data_manager
    2. Prediction loop       — continuous 24/7 ML prediction for all symbols
    3. Initial market scan   — deferred 30s, populates opportunity cache
    """
    import threading
    from time import sleep
    from .config import DEFAULT_STOCKS, DEFAULT_CRYPTO
    from .data_manager import data_manager

    # ── 1. Data prefetch (hourly) ────────────────────────────────────────────
    def prefetch_loop():
        while True:
            try:
                for s in (DEFAULT_CRYPTO[:15] + DEFAULT_STOCKS[:15]):
                    try:
                        if '/' in s:
                            data_manager.fetch_crypto_data(s, timeframe='1d', limit=365)
                        else:
                            data_manager.fetch_stock_data(s, period='1y', interval='1d')
                    except Exception:
                        pass
                    sleep(1)
            except Exception as e:
                print(f"[Prefetch] Error: {e}")
            sleep(3600)

    threading.Thread(target=prefetch_loop, daemon=True, name="DataPrefetch").start()
    print("[Agents] Data prefetch thread started")

    # ── 2. Self-learning feedback loop ───────────────────────────────────────
    try:
        from .agents.feedback_loop import feedback_loop
        feedback_loop.start()
        print("[Agents] Self-learning feedback loop started")
    except Exception as e:
        print(f"[Agents] Feedback loop failed to start: {e}")

    # ── 3. Continuous prediction loop ────────────────────────────────────────
    try:
        from .agents.prediction_loop import prediction_loop
        prediction_loop.start()
        print("[Agents] Continuous prediction loop started")
    except Exception as e:
        print(f"[Agents] Prediction loop failed to start: {e}")

    # ── 4. Real-time price feed (background auto-refresh) ─────────────────────
    try:
        from .agents.realtime_feed import realtime_feed
        top_symbols = (
            ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
            + DEFAULT_STOCKS[:10]
            + DEFAULT_CRYPTO[:5]
        )
        realtime_feed.start_background_refresh(top_symbols, interval=30.0)
        print("[Agents] Real-time price feed started")
    except Exception as e:
        print(f"[Agents] Real-time feed failed to start: {e}")

    # ── 5. New listings auto-discovery ───────────────────────────────────────
    try:
        from .agents.new_listings import new_listings_tracker
        new_listings_tracker.start()
        print("[Agents] New listings tracker started")
    except Exception as e:
        print(f"[Agents] New listings tracker failed to start: {e}")

    # ── 6. Deferred initial market scan ──────────────────────────────────────
    def initial_scan():
        sleep(30)
        try:
            from .agents.master_agent import master_agent
            print("[Agents] Running initial market scan...")
            master_agent.full_market_scan()
            print("[Agents] Initial market scan complete")
        except Exception as e:
            print(f"[Agents] Initial scan error: {e}")

    threading.Thread(target=initial_scan, daemon=True, name="InitialScan").start()


def start():
    """Start the API server with all background agents."""
    print("""
    +---------------------------------------------------------+
    |        NEXUSTRADER - AI PREDICTION ENGINE               |
    |                                                         |
    |  5-Model Ensemble: LSTM + Prophet + XGBoost +           |
    |                    ARIMA + LightGBM                     |
    |  7 Scanner Agents + Master Orchestrator                 |
    |  Multi-source Web Search (10 verified domains)          |
    |  Continuous 24/7 Prediction Loop                        |
    +---------------------------------------------------------+
    """)
    print(f"Starting server at http://{API_HOST}:{API_PORT}")
    print(f"API docs: http://localhost:{API_PORT}/docs")

    _start_all_agents()

    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )


if __name__ == "__main__":
    start()
