# notifier

Small service that watches [calendar-service](https://github.com/Luissoares11/calendar-service) and sends event reminders to my iPhone as Web Push notifications.

It polls the calendar, works out which alerts are due, remembers what it already sent, and pushes the rest. No dependency on EDITH. If EDITH is down, reminders still fire.

## How it works

Every `POLL_SECONDS` (default 30):

1. **Fetch** all events from calendar-service (`GET /events?list=true&all=true`).
2. **Expand** recurring events into their real occurrences (weekly, monthly, yearly).
3. **Check rules** for the event type and see which alerts are due right now.
4. **Dedupe** against SQLite. Each alert is keyed by `(event_id, occurrence start, alert key)`.
5. **Deliver** a Web Push to every subscribed device. If at least one accepts it, the alert is marked as sent.

If nobody is subscribed or delivery fails, the alert is not marked as sent and is retried on the next cycle until its window closes.

## Alert rules

| Type | Alerts |
|---|---|
| `exam` 🎓 | 1 week, 2 days, 1 day, 1 hour before |
| `appointment` 🏥 | 1 week, 2 days, 1 day, 1 hour before |
| `meeting` 💼 | 1 week, 2 days, 1 day, 1 hour before |
| `deadline` ⚠️ | 1 week, 2 days, 1 day, 1 hour before |
| `other` 📅 | 1 week, 2 days, 1 day, 1 hour before |
| `birthday` 🎂 | 1 week before, 1 day before, 9:00 on the day |

Unknown types (for example `personal`) use the `other` rules. Rules live in `config.py`.

An alert only fires if it became due in the last 2 hours (`GRACE`) and the event has not started. That covers short downtime and stops a new event from instantly firing alerts that are already in the past. The `9am` birthday alert stays valid until midnight.

## Time and recurrence

- All times are handled in `Europe/Lisbon`, including the winter/summer offset change.
- calendar-service returns recurring events with their **original** start date. The notifier rebuilds each occurrence from the local wall-clock time, so a yearly event keeps the same local hour across DST.
- Day-31 and Feb-29 dates are clamped to the last day of the month.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | Status and number of subscribed devices |
| GET | `/vapid-public-key` | none | Public key the PWA needs to subscribe |
| POST | `/subscribe` | bearer | Store a push subscription |
| POST | `/test` | bearer | Send a test notification to all devices |

Auth is `Authorization: Bearer <NOTIFIER_TOKEN>`.

## Configuration

Set these in `.env` :

| Variable | Required | Default | Notes |
|---|---|---|---|
| `CALENDAR_API_TOKEN` | yes | | Bearer token for calendar-service |
| `NOTIFIER_TOKEN` | yes | | Token for `/subscribe` and `/test` |
| `VAPID_PRIVATE_KEY` | yes | | Generated once |
| `VAPID_PUBLIC_KEY` | yes | | Generated once |
| `VAPID_SUBJECT` | yes | | `mailto:` address, required by Apple |
| `CALENDAR_SERVICE_URL` | no | `your-service-ip` | Use the LAN IP if the container cannot reach the Tailscale IP |
| `POLL_SECONDS` | no | `30` | |
| `NOTIFIER_DB` | no | `notifier.db` | Set to `/data/notifier.db` in Docker |
| `NOTIFIER_ALLOWED_ORIGINS` | no | `*` | Comma-separated. Set to the calendar-ui origin |

Generate the VAPID keys once and keep them. If they change, every device has to subscribe again.

## Run locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8030
```

Run a single worker. More than one worker means more than one polling loop and duplicate alerts.

## Deploy (Docker)

```
git clone git@github.com:Luissoares11/notifier-service.git
cd notifier-service
nano .env
docker compose up -d --build
docker compose logs -f notifier
```

- The container listens on `8030`, published on `127.0.0.1` only.
- SQLite lives in the `notifier-data` volume, so rebuilds keep sent alerts and subscriptions.
- Expose it over HTTPS with Tailscale (the PWA needs HTTPS to call it):

```
sudo tailscale serve --bg --https=8445 http://localhost:8030
tailscale serve status
```

Check it:

```
curl https://<vm>.<tailnet>.ts.net:8445/health
```

## Subscribing a phone

1. Install calendar-ui to the iPhone home screen (iOS 16.4 or newer).
2. Open it with Tailscale on and tap anywhere. iOS asks for notification permission once.
3. `/health` should now show `subscriptions: 1`.
4. Send a test:

```
curl -X POST -H "Authorization: Bearer $NOTIFIER_TOKEN" https://<vm>.<tailnet>.ts.net:8445/test
```

Push delivery goes through Apple, so the phone does not need Tailscale to receive notifications. Subscriptions that Apple reports as gone (404 or 410) are removed automatically.

## Project layout

```
notifier/
├── main.py            # FastAPI app, polling loop, endpoints
├── rules.py           # which alerts are due now, recurrence expansion
├── config.py          # settings, per-type alert rules
├── store.py           # SQLite: sent alerts and push subscriptions
├── deliver.py         # Web Push sending
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Notes and limits

- Alerts only fire while the service is running, and only inside their window. Keep it up.
- The calendar `all=true` fetch returns every event each cycle. Fine at this scale.
- Deadline completion is not checked yet. Once calendar-service has a completion flag, completed deadlines should be skipped in `rules.py`.
- Logs are in UTC. Times inside alert messages are Lisbon time.