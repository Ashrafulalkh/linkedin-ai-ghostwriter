"""
Timezone and datetime synchronization utilities for LinkedIn AI Ghostwriter.
Ensures post scheduling and timestamps align with the user's local computer time.
"""

from __future__ import annotations

import zoneinfo
from datetime import datetime, timezone
from typing import List, Optional, Union

# Common major world timezones for easy selection/fallback
POPULAR_TIMEZONES: List[str] = [
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Vancouver",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Amsterdam",
    "Europe/Warsaw",
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Asia/Jerusalem",
    "Asia/Dubai",
    "Asia/Karachi",
    "Asia/Kolkata",
    "Asia/Dhaka",
    "Asia/Bangkok",
    "Asia/Singapore",
    "Asia/Hong_Kong",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
]


def get_timezone(tz_name: Optional[str] = None) -> zoneinfo.ZoneInfo:
    """
    Safely resolve a ZoneInfo timezone object from a timezone name.
    Falls back to UTC if the timezone name is invalid or unavailable.
    """
    if not tz_name or not isinstance(tz_name, str):
        return zoneinfo.ZoneInfo("UTC")

    tz_clean = tz_name.strip()
    try:
        return zoneinfo.ZoneInfo(tz_clean)
    except Exception:
        # Fallback to local system timezone or UTC
        try:
            local_tz = datetime.now().astimezone().tzinfo
            if isinstance(local_tz, zoneinfo.ZoneInfo):
                return local_tz
        except Exception:
            pass
        return zoneinfo.ZoneInfo("UTC")


def get_user_now(tz_name: Optional[str] = None) -> datetime:
    """Get current datetime in the user's specified computer timezone."""
    tz = get_timezone(tz_name)
    return datetime.now(tz)


def parse_datetime_safe(dt_val: Union[str, datetime]) -> datetime:
    """
    Safely parse an ISO string or datetime object into a timezone-aware UTC datetime.
    Naive inputs are interpreted in the local system timezone before converting to UTC.
    """
    local_tz = datetime.now().astimezone().tzinfo or timezone.utc

    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=local_tz).astimezone(timezone.utc)
        return dt_val.astimezone(timezone.utc)

    if not isinstance(dt_val, str) or not dt_val.strip():
        return datetime.now(timezone.utc)

    val = dt_val.strip()
    if val.endswith("Z"):
        val = val[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(val)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=local_tz)
        return parsed.astimezone(timezone.utc)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(val, fmt)
                return parsed.replace(tzinfo=local_tz).astimezone(timezone.utc)
            except Exception:
                pass
        return datetime.now(timezone.utc)


def user_dt_to_utc_iso(user_dt: datetime, tz_name: Optional[str] = None) -> str:
    """
    Convert a user local datetime (from date/time pickers) into a UTC ISO string for storage.
    """
    tz = get_timezone(tz_name)
    if user_dt.tzinfo is None:
        user_aware = user_dt.replace(tzinfo=tz)
    else:
        user_aware = user_dt.astimezone(tz)

    utc_dt = user_aware.astimezone(timezone.utc)
    return utc_dt.isoformat()


def utc_iso_to_user_dt(iso_str: str, tz_name: Optional[str] = None) -> datetime:
    """
    Convert a stored UTC ISO string into the user's computer timezone.
    """
    utc_dt = parse_datetime_safe(iso_str)
    tz = get_timezone(tz_name)
    return utc_dt.astimezone(tz)


def format_for_user(
    iso_or_dt: Union[str, datetime],
    tz_name: Optional[str] = None,
    fmt: str = "%b %d, %Y at %I:%M %p",
    include_tz: bool = True,
) -> str:
    """
    Format a timestamp into a friendly human-readable string in the user's computer timezone.
    """
    if isinstance(iso_or_dt, str) and not iso_or_dt.strip():
        return ""

    user_dt = utc_iso_to_user_dt(iso_or_dt, tz_name) if isinstance(iso_or_dt, str) else iso_or_dt.astimezone(get_timezone(tz_name))
    formatted = user_dt.strftime(fmt)
    if include_tz:
        tz_abbr = user_dt.strftime("%Z") or user_dt.strftime("%z")
        if tz_abbr:
            formatted += f" ({tz_abbr})"
    return formatted


def format_relative_countdown(target_iso: str, tz_name: Optional[str] = None) -> str:
    """
    Calculate human-readable relative countdown from user's current computer time to target timestamp.
    """
    if not target_iso or not target_iso.strip():
        return ""

    target_dt = parse_datetime_safe(target_iso)
    now_utc = datetime.now(timezone.utc)
    delta = target_dt - now_utc
    total_seconds = delta.total_seconds()

    if total_seconds <= 0:
        return "due now (processing...)"

    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")

    return f"in {' '.join(parts)}"
