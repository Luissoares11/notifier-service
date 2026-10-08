import sqlite3
from contextlib import closing

from config import DB_PATH


def _conn():
    return sqlite3.connect(DB_PATH)


def init():
    with closing(_conn()) as c, c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS sent_alerts (
                event_id TEXT NOT NULL,
                event_start TEXT NOT NULL,
                alert_key TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (event_id, event_start, alert_key)
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS subscriptions (
                endpoint TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )


def already_sent(event_id, event_start, alert_key) -> bool:
    with closing(_conn()) as c:
        row = c.execute(
            "SELECT 1 FROM sent_alerts WHERE event_id=? AND event_start=? AND alert_key=?",
            (event_id, event_start, alert_key),
        ).fetchone()
    return row is not None


def mark_sent(event_id, event_start, alert_key):
    with closing(_conn()) as c, c:
        c.execute(
            "INSERT OR IGNORE INTO sent_alerts (event_id, event_start, alert_key) VALUES (?,?,?)",
            (event_id, event_start, alert_key),
        )


def save_subscription(endpoint, data_json):
    with closing(_conn()) as c, c:
        c.execute(
            "INSERT OR REPLACE INTO subscriptions (endpoint, data) VALUES (?,?)",
            (endpoint, data_json),
        )


def list_subscriptions():
    with closing(_conn()) as c:
        return c.execute("SELECT endpoint, data FROM subscriptions").fetchall()


def delete_subscription(endpoint):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM subscriptions WHERE endpoint=?", (endpoint,))


def count_subscriptions() -> int:
    with closing(_conn()) as c:
        return c.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]