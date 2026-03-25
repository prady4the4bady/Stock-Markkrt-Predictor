"""
NexusTrader — Centralised error handlers.

Registers FastAPI exception handlers that map every known failure mode
to the correct HTTP status code and a user-friendly message.

Error map:
  ValueError            → 400 / 404  (bad symbol or missing data)
  sqlite3.DatabaseError → 503        (yfinance cache corrupt — auto-repaired)
  ExternalRateLimitError→ 429        (upstream provider throttling)
  ccxt / network errors → 503        (data provider unavailable)
  RequestValidationError→ 422        (bad query params / body)
  HTTPException         → pass-through
  Everything else       → 500        (sanitised — no stack trace to client)
"""
import sqlite3
import traceback
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ── Helpers ──────────────────────────────────────────────────────────────────

_HTTP_MESSAGES = {
    400: "Bad request — check the parameters you sent.",
    401: "Authentication required — please log in.",
    403: "You don't have permission to access this resource.",
    404: "Symbol not found — verify the ticker is correct.",
    405: "Method not allowed.",
    408: "Request timed out — please try again.",
    422: "Validation error — one or more fields are invalid.",
    429: "Too many requests — please wait a moment and try again.",
    500: "Internal server error — we're looking into it.",
    502: "Bad gateway — upstream service is unavailable.",
    503: "Service temporarily unavailable — please retry shortly.",
}

def _json(status: int, code: str, message: str, detail: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": code, "message": message, "detail": detail},
    )


# ── Handlers ─────────────────────────────────────────────────────────────────

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Pass-through for HTTPExceptions already raised by route handlers."""
    message = _HTTP_MESSAGES.get(exc.status_code, "An error occurred.")
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _json(exc.status_code, f"HTTP_{exc.status_code}", message, detail)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic / FastAPI query-param or body validation failures → 422."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = " → ".join(str(loc) for loc in first.get("loc", []))
    msg = first.get("msg", "Validation failed.")
    detail = f"Field '{field}': {msg}" if field else msg
    return _json(422, "VALIDATION_ERROR", "Invalid request — please check your input.", detail)


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """ValueError raised in route/model code → 404 or 400 depending on message."""
    msg = str(exc)
    lmsg = msg.lower()
    if "no data" in lmsg or "not found" in lmsg or "no ticker" in lmsg or "invalid ticker" in lmsg:
        return _json(404, "SYMBOL_NOT_FOUND",
                     "No data found for this symbol — is it a valid ticker?", msg)
    return _json(400, "BAD_REQUEST", "Invalid value in request.", msg)


async def database_error_handler(request: Request, exc: sqlite3.DatabaseError) -> JSONResponse:
    """
    SQLite corruption (usually yfinance timezone cache) → auto-repair and 503.
    The client should retry; on the next request the cache will be fresh.
    """
    try:
        from ..main import _repair_yfinance_cache
        _repair_yfinance_cache()
        print("[ErrorHandler] yfinance cache repaired after DatabaseError.")
    except Exception as repair_exc:
        print(f"[ErrorHandler] Cache repair failed: {repair_exc}")

    return _json(
        503, "CACHE_REPAIRED",
        "A data-cache issue was detected and automatically repaired — please retry your request.",
        type(exc).__name__,
    )


async def rate_limit_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """ExternalRateLimitError from data_manager → 429."""
    return _json(
        429, "PROVIDER_RATE_LIMITED",
        "The data provider is temporarily rate-limiting us — please wait ~60 s and try again.",
        str(exc),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all safety net → 500.  Stack trace printed server-side, never sent to client."""
    print(f"[ERROR] Unhandled {type(exc).__name__} on {request.method} {request.url.path}: {exc}")
    traceback.print_exc()
    return _json(500, "INTERNAL_ERROR",
                 "An unexpected error occurred on our end — we're looking into it.",
                 type(exc).__name__)


# ── Registration ──────────────────────────────────────────────────────────────

def register_error_handlers(app) -> None:
    """Call once after `app = FastAPI(...)` to wire up all handlers."""
    from ..data_manager import ExternalRateLimitError

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(sqlite3.DatabaseError, database_error_handler)
    app.add_exception_handler(ExternalRateLimitError, rate_limit_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
