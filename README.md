# Frontdesk

WhatsApp auto-reply + Google Sheets booking ledger for local shops, matching
the flow in `frontdesk-pitch.html`: a customer texts, gets an instant reply
with hours/services/booking link, and the message lands as a row in the
shop's Google Sheet.

## How it works

`POST /webhook/whatsapp/{shop_id}` is the Twilio WhatsApp webhook. On each
inbound message it:

1. Validates the Twilio request signature.
2. Loads that shop's config from `shops/{shop_id}.json`.
3. Appends a row (timestamp, sender, message, status `New`) to the shop's
   Google Sheet.
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

### Google Sheets

1. Create a Google Cloud service account, enable the Sheets API, and
   download its JSON key to `secrets/service-account.json`.
2. Share the target Google Sheet with the service account's email
   (Editor access).
3. Put the sheet ID (from its URL) in the shop's config as
   `google_sheet_id`. The sheet needs a tab matching `sheet_tab`
   (default `Bookings`) with 4 columns: date, from, message, status.

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
