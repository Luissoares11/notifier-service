import calendar
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from config import DEFAULT_TYPE, GRACE, TYPES

log = logging.getLogger("notifier.rules")

TZ = ZoneInfo("Europe/Lisbon")
RECURRING = ("weekly", "monthly", "yearly")


def _window(start, when):
    """Return (alert_at, cutoff): the alert may fire when alert_at <= now < cutoff."""
    if isinstance(when, time):
        alert_at = datetime.combine(start.date(), when, tzinfo=start.tzinfo)
        next_midnight = datetime.combine(
            start.date() + timedelta(days=1), time.min, tzinfo=start.tzinfo
        )
        return alert_at, next_midnight
    alert_at = start - when
    return alert_at, min(alert_at + GRACE, start)


def _occurrences(start, recurrence, now):
    """Occurrences of an event that could have an alert active around `now`.
    `start` must already be in TZ. Non-recurring events return just themselves."""
    if recurrence not in RECURRING:
        return [start]

    base = start.replace(tzinfo=None)  # local wall-clock time
    local_now = now.astimezone(TZ).replace(tzinfo=None)
    lo = local_now - timedelta(days=1)
    hi = local_now + timedelta(days=8)
    out = []

    if recurrence == "weekly":
        k = max(0, -((base - lo) // timedelta(weeks=1)))
        occ = base + timedelta(weeks=k)
        while occ <= hi:
            out.append(occ)
            occ += timedelta(weeks=1)
    else:
        step = 12 if recurrence == "yearly" else 1
        base_idx = base.year * 12 + base.month - 1
        lo_idx = lo.year * 12 + lo.month - 1
        hi_idx = hi.year * 12 + hi.month - 1
        for idx in range(lo_idx, hi_idx + 1):
            if idx < base_idx or (idx - base_idx) % step:
                continue
            year, month0 = divmod(idx, 12)
            month = month0 + 1
            day = min(base.day, calendar.monthrange(year, month)[1])  # Feb 29 / day 31 clamp
            occ = base.replace(year=year, month=month, day=day)
            if lo <= occ <= hi:
                out.append(occ)

    return [o.replace(tzinfo=TZ) for o in out]


def due_alerts(events, now):
    """Return the alerts due at `now` (timezone-aware datetime)."""
    out = []
    for ev in events:
        try:
            start = datetime.fromisoformat(ev["start_time"])
            event_id = ev["id"]
        except (KeyError, TypeError, ValueError):
            log.warning("skipping malformed event: %r", ev)
            continue

        if start.tzinfo is None:
            start = start.replace(tzinfo=TZ)
        else:
            start = start.astimezone(TZ)

        cfg = TYPES.get(ev.get("type"), TYPES[DEFAULT_TYPE])
        fmt = "%a %d %b, %H:%M" if cfg["show_time"] else "%a %d %b"

        for occ in _occurrences(start, ev.get("recurrence"), now):
            when_text = occ.strftime(fmt)
            for key, when, phrase in cfg["alerts"]:
                alert_at, cutoff = _window(occ, when)
                if alert_at <= now < cutoff:
                    out.append(
                        {
                            "event_id": event_id,
                            "event_start": occ.isoformat(),
                            "alert_key": key,
                            "title": ev.get("title", ""),
                            "type": ev.get("type", ""),
                            "message": f"{cfg['emoji']} {ev.get('title', 'Event')}: {phrase} ({when_text})",
                        }
                    )
    return out  