import os
from datetime import time, timedelta

from dotenv import load_dotenv

load_dotenv()

CALENDAR_URL = os.getenv("CALENDAR_SERVICE_URL", "http://100.91.106.89:8010")
CALENDAR_TOKEN = os.getenv("CALENDAR_API_TOKEN", "")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "30"))
DB_PATH = os.getenv("NOTIFIER_DB", "notifier.db")

NOTIFIER_TOKEN = os.getenv("NOTIFIER_TOKEN", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "")
# Comma-separated origins allowed to call the API (the calendar-ui URL). "*" = any.
ALLOWED_ORIGINS = os.getenv("NOTIFIER_ALLOWED_ORIGINS", "*").split(",")

# An alert only fires if it became due within this window.
GRACE = timedelta(hours=2)

# Each alert: (key, when, phrase)
#   when = timedelta  -> that long before the event starts
#   when = time       -> at that clock time on the day of the event
STANDARD = [
    ("7d", timedelta(days=7), "in 1 week"),
    ("2d", timedelta(days=2), "in 2 days"),
    ("1d", timedelta(days=1), "tomorrow"),
    ("1h", timedelta(hours=1), "in 1 hour"),
]

BIRTHDAY = [
    ("7d", timedelta(days=7), "in 1 week"),
    ("1d", timedelta(days=1), "tomorrow"),
    ("9am", time(9, 0), "today"),
]

TYPES = {
    "exam": {"emoji": "🎓", "alerts": STANDARD, "show_time": True},
    "appointment": {"emoji": "🏥", "alerts": STANDARD, "show_time": True},
    "meeting": {"emoji": "💼", "alerts": STANDARD, "show_time": True},
    "deadline": {"emoji": "⚠️", "alerts": STANDARD, "show_time": True},
    "birthday": {"emoji": "🎂", "alerts": BIRTHDAY, "show_time": False},
    "other": {"emoji": "📅", "alerts": STANDARD, "show_time": True},
}

# Unknown types (e.g. "personal") use these rules.
DEFAULT_TYPE = "other"