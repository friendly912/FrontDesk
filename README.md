# Frontdesk

WhatsApp auto-reply + booking ledger for local shops, matching the flow in
`frontdesk-pitch.html`: a customer texts, gets an instant reply with
hours/services/booking link, and the message lands as a row in the shop's
ledger.

## How it works

`POST /webhook/whatsapp/{shop_id}` is the Twilio WhatsApp webhook. On each
inbound message it:

1. Validates the Twilio request signature.
2. Loads that shop's config from `shops/{shop_id}.json`.
3. Appends a row (timestamp, sender, message, status `New`) to the shop's
   ledger — a local CSV file by default, or a Google Sheet once you switch
   `BOOKINGS_BACKEND` (see below).
4. Replies with the shop's hours, services, and booking link via TwiML.

Each shop gets its own webhook URL and its own config file, so one server
can serve several shops.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Twilio

1. Create a Twilio account and set up the WhatsApp sandbox (or a production
   WhatsApp sender once approved).
2. Put `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` in `.env`.
3. Point the sandbox's "when a message comes in" webhook at
   `https://<your-public-url>/webhook/whatsapp/<shop_id>`.

### Booking ledger

`BOOKINGS_BACKEND` in `.env` picks where bookings get logged:

- **`csv` (default, no external account needed)** — bookings are appended to
  `LOCAL_DATA_DIR/<shop_id>/bookings.csv` (created automatically). This is
  enough to demo the full flow — including watching new rows land in real
  time — without setting up anything in Google Cloud. Useful if your Google
  account can't do the 2FA Cloud Console requires yet.
- **`google_sheets`** — requires a Google Cloud service account:
  1. Create the service account, enable the Sheets API, and download its
     JSON key to `secrets/service-account.json`.
  2. Share the target Google Sheet with the service account's email
     (Editor access).
  3. Put the sheet ID (from its URL) in the shop's config as
     `google_sheet_id`. The sheet needs a tab matching `sheet_tab`
     (default `Bookings`) with 4 columns: date, from, message, status.

  Switching later doesn't touch any code — just flip `BOOKINGS_BACKEND` to
  `google_sheets` in `.env` (or in Render's Environment tab) once you have
  the service account.

When the `csv` backend is active, `GET /debug/bookings/{shop_id}` reads the
file back over HTTP — handy when the server isn't on a machine you can
`cat` the file on directly (e.g. a Render deploy), and it's a plain URL
someone can open in a browser (on a phone or laptop) after sending a test
WhatsApp message, then refresh to see the new row. It returns 404 if the
shop is unknown or hasn't logged anything yet, and 404 if `BOOKINGS_BACKEND`
isn't `csv` (there's no file to read for `google_sheets`). If `DEBUG_TOKEN`
is set in `.env`, requests need the matching value either as a
`X-Debug-Token` header or a `?token=` query param, or they get a 403 — the
endpoint returns raw customer phone numbers and messages, so always set
this before deploying anywhere public:

```bash
curl -H "X-Debug-Token: $DEBUG_TOKEN" \
  https://frontdesk-mvp.onrender.com/debug/bookings/example-shop
```

Or as a link anyone can just open (e.g. share with the person testing on
their own phone):

```
https://frontdesk-mvp.onrender.com/debug/bookings/example-shop?token=<DEBUG_TOKEN>
```

### Shop config

Copy `shops/example-shop.json` to `shops/<shop_id>.json` and fill in hours,
services, booking link, and sheet ID.

### Run it

```bash
uvicorn app.main:app --reload
```

Expose it publicly for Twilio to reach (e.g. `ngrok http 8000`), and set
`PUBLIC_BASE_URL` in `.env` to that public URL if the app sits behind a
proxy/tunnel — signature validation checks against the exact URL Twilio
posted to.

### Tests

```bash
pytest
```

## Deploying to Render

`render.yaml` defines this as a Render Blueprint, so it deploys in one step:
Render dashboard → **New → Blueprint** → point it at this GitHub repo. Render
reads `render.yaml` and provisions the web service automatically.

Env vars marked `sync: false` in `render.yaml` aren't stored in the repo —
Render prompts you to fill them in when the blueprint is applied (or later
under the service's **Environment** tab):

- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` — from the Twilio console.
- `DEBUG_TOKEN` — any random string; required to use the `/debug/bookings`
  endpoint below once the service is public.

`render.yaml` defaults `BOOKINGS_BACKEND` to `csv`, so the deploy works with
just the two Twilio values above — no Google Cloud needed. Note that
Render's free/starter web services have ephemeral disk: it survives while
the instance is running but resets on redeploy, which is fine for a demo
session but not for durable storage.

When you're ready to switch to Google Sheets: change `BOOKINGS_BACKEND` to
`google_sheets` in the Environment tab, then add the service account key as
a **Secret File** (service → **Environment** → **Secret Files** → new file
named `service-account.json` with the key's JSON as its contents). Render
mounts secret files at `/etc/secrets/<name>`, which is exactly what
`GOOGLE_SERVICE_ACCOUNT_FILE` in `render.yaml` already points at.

`PUBLIC_BASE_URL` in `render.yaml` assumes the service is named
`frontdesk-mvp` (Render's default subdomain is
`https://<service-name>.onrender.com`). If you rename the service, update
that value to match — it's used for Twilio signature validation, so a
mismatch makes every webhook request look invalid (403s).

Once it's live, point the Twilio WhatsApp Sandbox's webhook at:
`https://frontdesk-mvp.onrender.com/webhook/whatsapp/<shop_id>`

Watch bookings land during a demo with `GET /debug/bookings/<shop_id>` (see
above) — no shell access to the instance needed.

**Free plan note**: it spins down after ~15 minutes idle and takes 30-50s to
wake on the next request. Fine between test messages, but hit `/health` a
minute or two before a live client demo to warm it up — or use the paid
Starter plan (~$7/mo) to remove cold-start risk entirely during the call.

## Known MVP limitations

- Every inbound message is logged as a raw row (sender, message text,
  status `New`); it doesn't parse out a structured service/time the way the
  pitch's sample sheet shows. A person still reads the message and
  confirms. Structured extraction (or a booking form that writes directly
  to the sheet) is a natural fast-follow.
- One Twilio WhatsApp-enabled number generally serves one webhook
  configuration, so in production each shop typically needs its own
  Twilio number — the shared sandbox works for development only.
- Shop config is read from local JSON files and cached in memory; changing
  a config file requires restarting the server.
- The `csv` booking backend is local disk, not shared or durable across
  redeploys — fine for a pilot/demo, but `google_sheets` (or a real
  database) is the intended path once this needs to persist for real.
