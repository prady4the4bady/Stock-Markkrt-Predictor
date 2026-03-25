"""
NexusTrader — New Listings REST API
Exposes the auto-discovered crypto and IPO listings to the frontend.
"""

import sqlite3
from fastapi import APIRouter, HTTPException, Query
from typing import Optional


def _classify(e: Exception) -> HTTPException:
    """Map a caught exception to an appropriate HTTPException."""
    msg = str(e)
    lmsg = msg.lower()
    if isinstance(e, ValueError) or "no data" in lmsg or "not found" in lmsg:
        return HTTPException(status_code=404, detail=msg)
    if isinstance(e, sqlite3.DatabaseError) or "database" in lmsg or "disk image" in lmsg:
        return HTTPException(status_code=503, detail="Data store unavailable — please retry shortly.")
    if "connection" in lmsg or "network" in lmsg or "timeout" in lmsg or "rate limit" in lmsg:
        return HTTPException(status_code=503, detail="Data provider temporarily unavailable.")
    if "permission" in lmsg or "access" in lmsg:
        return HTTPException(status_code=403, detail=msg)
    return HTTPException(status_code=500, detail=msg)

from ..agents.new_listings import (
    get_new_crypto,
    get_new_ipos,
    get_all_new,
    get_summary,
    new_listings_tracker,
)

router = APIRouter(prefix="/api/listings")


# ── GET /api/listings/summary ─────────────────────────────────────────────────
@router.get("/summary")
async def listings_summary():
    """
    Quick stats: total crypto tracked, new coins, IPOs upcoming.
    Lightweight — reads from SQLite counts only.
    """
    try:
        return get_summary()
    except Exception as e:
        raise _classify(e)


# ── GET /api/listings/crypto ──────────────────────────────────────────────────
@router.get("/crypto")
async def listings_crypto(
    limit: int = Query(default=100, ge=1, le=500),
    only_new: bool = Query(default=False, description="Only coins not in default universe"),
    min_volume: float = Query(default=0.0, ge=0, description="Min 24h volume in USDT"),
):
    """
    All Binance USDT pairs sorted by 24h volume.

    Query params
    ------------
    limit       — max rows (1-500, default 100)
    only_new    — filter to coins not in the DEFAULT_CRYPTO watchlist
    min_volume  — minimum 24h USDT volume (useful to filter micro-caps)
    """
    try:
        data = get_new_crypto(limit=limit, only_new=only_new, min_volume=min_volume)
        return {
            "items":   data,
            "count":   len(data),
            "filters": {
                "only_new":   only_new,
                "min_volume": min_volume,
                "limit":      limit,
            },
        }
    except Exception as e:
        raise _classify(e)


# ── GET /api/listings/stocks ──────────────────────────────────────────────────
@router.get("/stocks")
async def listings_stocks(
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: upcoming | priced | withdrawn",
    ),
):
    """
    Recent and upcoming stock IPOs sorted by IPO date (newest first).

    Query params
    ------------
    limit  — max rows (1-200, default 50)
    status — upcoming | priced | withdrawn | None (all)
    """
    valid_statuses = {"upcoming", "priced", "withdrawn", None}
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of: upcoming, priced, withdrawn",
        )
    try:
        data = get_new_ipos(limit=limit, status=status)
        return {
            "items":   data,
            "count":   len(data),
            "filters": {"status": status, "limit": limit},
        }
    except Exception as e:
        raise _classify(e)


# ── GET /api/listings/all ─────────────────────────────────────────────────────
@router.get("/all")
async def listings_all(
    limit: int = Query(default=200, ge=1, le=500),
):
    """
    Combined snapshot — new crypto coins + upcoming IPOs.
    Crypto is filtered to only_new=True and min_volume=100k USDT.
    """
    try:
        return get_all_new(limit=limit)
    except Exception as e:
        raise _classify(e)


# ── GET /api/listings/ipo ─────────────────────────────────────────────────────
@router.get("/ipo")
async def listings_ipo(
    limit: int = Query(default=30, ge=1, le=100),
):
    """Upcoming IPOs only — convenience alias for /stocks?status=upcoming."""
    try:
        data = get_new_ipos(limit=limit, status="upcoming")
        return {"items": data, "count": len(data)}
    except Exception as e:
        raise _classify(e)


# ── POST /api/listings/refresh ────────────────────────────────────────────────
@router.post("/refresh")
async def listings_refresh(
    asset_class: str = Query(
        default="all",
        description="Which feed to refresh: all | crypto | stocks",
    ),
):
    """
    Trigger an immediate out-of-band refresh (admin / debug use).
    Runs synchronously — may take 10-30 seconds.
    """
    valid = {"all", "crypto", "stocks"}
    if asset_class not in valid:
        raise HTTPException(
            status_code=422,
            detail=f"asset_class must be one of: {', '.join(sorted(valid))}",
        )
    try:
        new_listings_tracker.force_refresh(asset_class)
        return {"status": "refreshed", "asset_class": asset_class}
    except Exception as e:
        raise _classify(e)


# ── GET /api/listings/status ──────────────────────────────────────────────────
@router.get("/status")
async def listings_status():
    """Daemon health — is the background tracker running?"""
    return {
        "running": new_listings_tracker.is_running(),
        "summary": get_summary(),
    }
