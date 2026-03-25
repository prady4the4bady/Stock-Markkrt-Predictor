"""
NexusTrader — Timezone utilities.

Reads the IANA timezone name from the X-Timezone request header that the
frontend sends automatically (e.g. 'Asia/Kolkata', 'America/New_York').

Usage in a route:
    from ..utils.timezone_utils import get_request_tz, now_local

    tz = get_request_tz(request)
    timestamp = now_local(tz)          # current time in user's tz as ISO string
    localized = localize_iso(iso, tz)  # convert a UTC ISO string to user's tz
"""
import re
from datetime import datetime, timezone as _UTC_TZ
from typing import Union
from fastapi import Request

# Basic sanity-check for IANA timezone names (e.g. "Asia/Kolkata", "UTC", "America/New_York")
_TZ_RE = re.compile(r'^[A-Za-z][A-Za-z0-9/_+\-]{1,49}$')

_UTC = _UTC_TZ.utc


def _parse_tz(tz_name: str):
    """Return a tzinfo for tz_name, or UTC on any failure."""
    if not tz_name or not _TZ_RE.match(tz_name):
        return _UTC
    # Try stdlib zoneinfo first (Python 3.9+), fall back to pytz
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, KeyError):
            return _UTC
    except ImportError:
        pass
    try:
        import pytz
        return pytz.timezone(tz_name)
    except Exception:
        return _UTC


def get_request_tz(request: Request):
    """
    Return a tzinfo object derived from the X-Timezone request header.
    Falls back to UTC if the header is absent or contains an unknown zone.

    Example header:
        X-Timezone: Asia/Kolkata
    """
    tz_name = request.headers.get("X-Timezone", "").strip()
    return _parse_tz(tz_name)


def localize_iso(iso_str: str, tzinfo) -> str:
    """
    Convert a UTC ISO-8601 string to the given timezone.
    Returns the original string unchanged if parsing fails.

    Example:
        localize_iso("2026-03-24T10:00:00", ZoneInfo("Asia/Kolkata"))
        # → "2026-03-24T15:30:00+05:30"
    """
    if not iso_str or tzinfo is _UTC:
        return iso_str
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_UTC)
        return dt.astimezone(tzinfo).isoformat()
    except Exception:
        return iso_str


def now_local(tzinfo) -> str:
    """Return the current time as an ISO string in the given timezone."""
    return datetime.now(tz=tzinfo).isoformat()
