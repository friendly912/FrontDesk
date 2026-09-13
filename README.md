# Frontdesk

LINE auto-reply + booking ledger for local shops, matching the flow in
`frontdesk-pitch.html`: a customer messages the shop's LINE account, gets an
instant reply with hours/services/booking link, and the message lands as a
row in the shop's ledger.

## How it works

`POST /webhook/line/{shop_id}` is the LINE Messaging API webhook. On each
inbound message event it:

1. Validates the `X-Line-Signature` header (HMAC-SHA256 over the raw body
   using the channel secret).
2. Loads that shop's config from `shops/{shop_id}.json`.
3. Appends a row (timestamp, sender's LINE user ID, message, status `New`)
   to the shop's ledger — a local CSV file by default, or a Google Sheet
   once you switch `BOOKINGS_BACKEND` (see below).
4. Replies with the shop's hours, services, and booking link via the LINE
   Reply API, using the event's `replyToken`.

Each shop gets its own webhook URL and its own config file, so one server
can serve several shops.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### LINE

1. Create a LINE Official Account and enable the **Messaging API** for it —
   easiest via the [LINE Developers Console](https://developers.line.biz/console/):
   create a provider, then a Messaging API channel under it.
2. On the channel's **Messaging API** tab, copy the **Channel secret** into
   `LINE_CHANNEL_SECRET`, and issue/copy a **Channel access token** (long-lived)
   into `LINE_CHANNEL_ACCESS_TOKEN` in `.env`.
3. Set **Webhook URL** to `https://<your-public-url>/webhook/line/<shop_id>`
   and turn **Use webhook** on. The console's "Verify" button sends a test
   request with no events — the app returns 200 for that, so Verify should
   succeed once the URL is reachable.
4. In the LINE Official Account Manager (the separate dashboard for the
   account itself, not the Developers Console) → **Settings → Response
   settings**, turn **off** "Auto-response messages" and "Greeting
   messages" so LINE's built-in canned replies don't fire alongside — or
   instead of — this app's reply. Leave "Webhooks" **on**.
5. Add the account as a friend to test: scan its QR code (shown on the
   Messaging API tab) or search its LINE ID from the app.

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
     (default `Bookings`) with 4 columns: date, from_id, message, status.

  Switching later doesn't touch any code — just flip `BOOKINGS_BACKEND` to
  `google_sheets` in `.env` (or in Render's Environment tab) once you have
  the service account.

When the `csv` backend is active, `GET /debug/bookings/{shop_id}` renders
the file as a simple HTML table — handy when the server isn't on a machine
you can `cat` the file on directly (e.g. a Render deploy), and it's a plain
URL someone can open in a browser (on a phone or laptop) after sending a
test LINE message. The page auto-refreshes every 5 seconds, so leaving it
open shows new rows land without touching anything. Add `?format=csv` to
get the raw CSV instead (e.g. to download it). The endpoint returns 404 if
the shop is unknown or hasn't logged anything yet, and 404 if
`BOOKINGS_BACKEND` isn't `csv` (there's no file to read for
`google_sheets`). If `DEBUG_TOKEN` is set in `.env`, requests need the
matching value either as a `X-Debug-Token` header or a `?token=` query
param, or they get a 403 — the endpoint returns raw customer LINE user IDs
and messages, so always set this before deploying anywhere public:

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

Expose it publicly for LINE to reach (e.g. `ngrok http 8000`), and paste
that URL into the channel's Webhook URL setting as described above.

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

- `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN` — from the LINE
  Developers Console's Messaging API tab.
- `DEBUG_TOKEN` — any random string; required to use the `/debug/bookings`
  endpoint below once the service is public.

`render.yaml` defaults `BOOKINGS_BACKEND` to `csv`, so the deploy works with
just the two LINE values above — no Google Cloud needed. Note that Render's
free/starter web services have ephemeral disk: it survives while the
instance is running but resets on redeploy, which is fine for a demo
session but not for durable storage.

When you're ready to switch to Google Sheets: change `BOOKINGS_BACKEND` to
`google_sheets` in the Environment tab, then add the service account key as
a **Secret File** (service → **Environment** → **Secret Files** → new file
named `service-account.json` with the key's JSON as its contents). Render
mounts secret files at `/etc/secrets/<name>`, which is exactly what
`GOOGLE_SERVICE_ACCOUNT_FILE` in `render.yaml` already points at.

Once it's live, set the LINE channel's Webhook URL to:
`https://frontdesk-mvp.onrender.com/webhook/line/<shop_id>`

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
- One LINE Official Account maps to one webhook URL, so in production each
  shop typically needs its own Official Account — LINE's free plan allows
  creating more than one, so this works for a handful of pilot shops
  without extra cost.
- Shop config is read from local JSON files and cached in memory; changing
  a config file requires restarting the server.
- The `csv` booking backend is local disk, not shared or durable across
  redeploys — fine for a pilot/demo, but `google_sheets` (or a real
  database) is the intended path once this needs to persist for real.
