import json
import logging
import secrets
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import requests
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import config
import store
from deliver import deliver
from rules import due_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("notifier")

bearer = HTTPBearer()


def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not config.NOTIFIER_TOKEN or not secrets.compare_digest(
        creds.credentials, config.NOTIFIER_TOKEN
    ):
        raise HTTPException(status_code=401, detail="invalid token")


def fetch_events():
    r = requests.get(
        f"{config.CALENDAR_URL}/events",
        params={"list": "true", "all": "true"},
        headers={"Authorization": f"Bearer {config.CALENDAR_TOKEN}"},
        timeout=10,
    )
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(body.get("message", "calendar-service returned success=false"))
    return body.get("events", [])


def run_once():
    now = datetime.now(timezone.utc)
    for alert in due_alerts(fetch_events(), now):
        key = (alert["event_id"], alert["event_start"], alert["alert_key"])
        if store.already_sent(*key):
            continue
        if deliver(alert):
            store.mark_sent(*key)


def poll_loop():
    log.info("polling %s every %ss", config.CALENDAR_URL, config.POLL_SECONDS)
    while True:
        try:
            run_once()
        except requests.RequestException as e:
            log.error("calendar-service unreachable: %s", e)
        except Exception:
            log.exception("cycle failed")
        time.sleep(config.POLL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init()
    threading.Thread(target=poll_loop, daemon=True).start()
    yield


app = FastAPI(title="notifier", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok", "subscriptions": store.count_subscriptions()}


@app.get("/vapid-public-key")
def vapid_public_key():
    return {"key": config.VAPID_PUBLIC_KEY}


@app.post("/subscribe", dependencies=[Depends(verify_token)])
def subscribe(sub: dict):
    if not sub.get("endpoint") or not sub.get("keys"):
        raise HTTPException(status_code=400, detail="not a valid push subscription")
    store.save_subscription(sub["endpoint"], json.dumps(sub))
    return {"success": True}


@app.post("/test", dependencies=[Depends(verify_token)])
def test_push():
    ok = deliver({"title": "Notifier", "message": "🔔 Test notification, it works"})
    return {"success": ok}