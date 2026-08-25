"""
Timezone and datetime synchronization utilities for LinkedIn AI Ghostwriter.
Ensures post scheduling and timestamps align perfectly with the user's local computer time.
"""

from __future__ import annotations

import os
import zoneinfo
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

# Common timezone abbreviations mapped to standard IANA timezone names
TZ_ABBREVIATION_MAP: Dict[str, str] = {
    "BST": "Europe/London",
    "GMT": "Europe/London",
    "UTC": "UTC",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "IST": "Asia/Kolkata",
    "JST": "Asia/Tokyo",
    "KST": "Asia/Seoul",
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
}

# Popular world timezones
POPULAR_TIMEZONES: List[str] = [
    "Europe/London",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Vancouver",
    "America/Sao_Paulo",
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
    "UTC",
]


def get_system_default_timezone() -> str:
    """
    Detect the local computer/system timezone dynamically.
    Checks system symlinks (/etc/localtime), system files, and local UTC offsets.
    """
    # 1. Check /etc/localtime symlink (macOS / Linux standard)
    try:
        if os.path.islink("/etc/localtime"):
            target = os.readlink("/etc/localtime")
            if "zoneinfo/" in target:
                tz_extracted = target.split("zoneinfo/")[-1].strip()
                if tz_extracted:
                    try:
                        zoneinfo.ZoneInfo(tz_extracted)
                        return tz_extracted
                    except Exception:
                        pass
    except Exception:
        pass

    # 2. Check /etc/timezone file (Debian / Ubuntu / Docker)
    try:
        if os.path.exists("/etc/timezone"):
            with open("/etc/timezone", "r", encoding="utf-8") as f:
                tz_name = f.read().strip()
                if tz_name:
                    try:
                        zoneinfo.ZoneInfo(tz_name)
                        return tz_name
                    except Exception:
                        pass
    except Exception:
        pass

    # 3. Inspect Python's local astimezone
    try:
        local_tz = datetime.now().astimezone().tzinfo
        if hasattr(local_tz, "key") and local_tz.key:
            return local_tz.key
        if hasattr(local_tz, "zone") and local_tz.zone:
            return local_tz.zone
        
        # Check abbreviation
        now_dt = datetime.now()
        tz_name = now_dt.astimezone().strftime("%Z")
        if tz_name in TZ_ABBREVIATION_MAP:
            return TZ_ABBREVIATION_MAP[tz_name]

        # Match offset to candidate timezones
        local_offset = now_dt.astimezone().utcoffset()
        if local_offset is not None:
            for cand in POPULAR_TIMEZONES:
                try:
                    cand_tz = zoneinfo.ZoneInfo(cand)
                    if now_dt.astimezone(cand_tz).utcoffset() == local_offset:
                        return cand
                except Exception:
                    pass
    except Exception:
        pass

    return "Europe/London"


def get_timezone(tz_name: Optional[str] = None) -> zoneinfo.ZoneInfo:
    """
    Safely resolve a ZoneInfo timezone object.
    If tz_name is None, empty, or 'auto', automatically detects the computer's local timezone.
    """
    if not tz_name or not isinstance(tz_name, str) or tz_name.lower() in ("auto", "none", ""):
        detected = get_system_default_timezone()
        try:
            return zoneinfo.ZoneInfo(detected)
        except Exception:
            return zoneinfo.ZoneInfo("UTC")

    tz_clean = tz_name.strip()
    if tz_clean in TZ_ABBREVIATION_MAP:
        tz_clean = TZ_ABBREVIATION_MAP[tz_clean]

    try:
        return zoneinfo.ZoneInfo(tz_clean)
    except Exception:
        try:
            fallback = get_system_default_timezone()
            return zoneinfo.ZoneInfo(fallback)
        except Exception:
            return zoneinfo.ZoneInfo("UTC")


def get_user_now(tz_name: Optional[str] = None) -> datetime:
    """Get current datetime in the user's computer timezone."""
    tz = get_timezone(tz_name)
    return datetime.now(tz)


def parse_datetime_safe(dt_val: Union[str, datetime]) -> datetime:
    """
    Safely parse an ISO string or datetime object into a timezone-aware UTC datetime.
    Naive datetimes are interpreted in the user's local system timezone before converting to UTC.
    """
    local_tz = get_timezone()

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
        tz_abbr = user_dt.strftime("%Z")
        raw_offset = user_dt.strftime("%z")
        if raw_offset and len(raw_offset) >= 5:
            formatted_offset = f"UTC{raw_offset[:3]}:{raw_offset[3:]}"
            if tz_abbr and tz_abbr != raw_offset:
                formatted += f" ({tz_abbr} / {formatted_offset})"
            else:
                formatted += f" ({formatted_offset})"
        elif tz_abbr:
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
