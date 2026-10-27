from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import FreshnessStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def freshness_status(
    *,
    last_checked: datetime | None,
    last_changed: datetime | None,
    monitoring_frequency_days: int,
    version_status: str,
    source_status: str,
    now: datetime | None = None,
) -> FreshnessStatus:
    if version_status in {"superseded", "withdrawn"} or source_status != "active":
        return FreshnessStatus.SUPERSEDED
    if not last_checked:
        return FreshnessStatus.STALE

    checked_at = last_checked if last_checked.tzinfo else last_checked.replace(tzinfo=timezone.utc)
    if last_changed:
        changed_at = last_changed if last_changed.tzinfo else last_changed.replace(tzinfo=timezone.utc)
        if changed_at > checked_at:
            return FreshnessStatus.CHANGE_DETECTED
    age = (now or utc_now()) - checked_at
    review_after = timedelta(days=monitoring_frequency_days)
    stale_after = review_after * 2
    if age > stale_after:
        return FreshnessStatus.STALE
    if age > review_after:
        return FreshnessStatus.REVIEW_DUE
    return FreshnessStatus.VERIFIED
