import json
import logging

from pywebpush import WebPushException, webpush

import config
import store

log = logging.getLogger("notifier.deliver")


def deliver(alert) -> bool:
    """Push an alert to every subscribed device.
    Returns True if at least one device accepted it."""
    log.info("ALERT: %s", alert["message"])

    subs = store.list_subscriptions()
    if not subs:
        log.warning("no subscribed devices, alert not delivered")
        return False

    payload = json.dumps(
        {
            "title": alert.get("title") or "Calendar",
            "body": alert["message"],
            "tag": f"{alert.get('event_id', 'test')}-{alert.get('alert_key', '')}",
        }
    )

    delivered = 0
    for endpoint, sub_json in subs:
        try:
            webpush(
                subscription_info=json.loads(sub_json),
                data=payload,
                vapid_private_key=config.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": config.VAPID_SUBJECT},
                ttl=3600,
            )
            delivered += 1
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                log.info("subscription expired, removing it")
                store.delete_subscription(endpoint)
            else:
                log.error("push failed (status %s): %s", status, e)
        except Exception:
            log.exception("unexpected push error")

    return delivered > 0