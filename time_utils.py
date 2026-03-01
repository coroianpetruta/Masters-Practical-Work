"""Time parsing and binning utilities."""

from datetime import datetime, timezone
from typing import Any, List, Optional

def parse_dt(value: Any) -> Optional[datetime]:
    """
    Neo4j may return datetime objects (neo4j.time.DateTime) or strings.
    We normalize to Python datetime (UTC-aware if possible).
    """
    if value is None:
        return None

    # Neo4j python driver may give objects with to_native()
    if hasattr(value, "to_native"):
        value = value.to_native()

    if isinstance(value, datetime):
        # If naive, assume UTC
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, str):
        s = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            # last resort: common formats
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    pass
    return None


def floor_to_bin(dt: datetime, granularity: str) -> datetime:
    if granularity == "Year":
        return datetime(dt.year, 1, 1, tzinfo=timezone.utc)
    # Month
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)


def next_bin_start(bin_start: datetime, granularity: str) -> datetime:
    if granularity == "Year":
        return datetime(bin_start.year + 1, 1, 1, tzinfo=timezone.utc)
    # Month
    if bin_start.month == 12:
        return datetime(bin_start.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(bin_start.year, bin_start.month + 1, 1, tzinfo=timezone.utc)


def make_bins(min_dt: datetime, max_dt: datetime, granularity: str) -> List[datetime]:
    """
    Returns list of bin starts [t0, t1, ...] that cover [min_dt, max_dt] (inclusive).
    """
    start = floor_to_bin(min_dt, granularity)
    end = floor_to_bin(max_dt, granularity)

    bins = [start]
    cur = start
    while cur < end:
        cur = next_bin_start(cur, granularity)
        bins.append(cur)
    return bins


def label_bin(dt: datetime, granularity: str) -> str:
    if granularity == "Year":
        return f"{dt.year}"
    return f"{dt.year}-{dt.month:02d}"
