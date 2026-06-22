# Instagram Downloader Telegram Bot

A Telegram bot that downloads Instagram content — posts, reels, stories, highlights — instantly and for free.

## Supported Links

- `instagram.com/p/...` — Posts
- `instagram.com/reel/...` — Reels
- `instagram.com/tv/...` — IGTV
- `instagram.com/stories/username/id` — Single story
- `instagram.com/stories/username/` — All user stories
- `instagram.com/highlights/...` — Highlights
- `instagram.com/s/...` — Share links

Just send a link — the bot handles the rest.

---

## Build Your Own Instagram Bot

This bot is powered by **[HikerAPI](https://hikerapi.com)** — the fastest Instagram API on the market.

### Get 100 Free API Requests

**[Sign up with this link](https://hikerapi.com/p/hsazcgym)** and get **100 free requests** — no credit card required. Enough to build and test your own Instagram bot, scraper, or analytics tool.

What you get with HikerAPI:

- **Profiles, posts, stories, reels, highlights** — all media types
- **Followers, following, comments, likes** — full social graph
- **OSINT data** — emails, phones, locations, account age
- **No rate limits on paid plans** — scale as you grow
- **99.9% uptime** — production-ready infrastructure

> **[Get your free 100 requests here](https://hikerapi.com/p/hsazcgym)**

---

## Setup

1. Get a Telegram bot token from [@BotFather](https://t.me/BotFather)
2. Get a HikerAPI access key — **[100 free requests here](https://hikerapi.com/p/hsazcgym)**
3. Copy `default.env` to `.env` and fill in your tokens:
   ```
   cp default.env .env
   ```
4. Run with Docker Compose:
   
```
   docker compose up -d --build
   ```

---

## Deploy to Vercel (Telegram Webhook)

This bot is configured for **webhook** mode on Vercel (the old long-polling mode is disabled in `bot.py`).

### 1) Create a Vercel project
- Import this repo into Vercel
- Vercel will deploy the serverless route:
  - `api/telegram.py`  → `POST /api/telegram`

### 2) Set environment variables
Add these in **Vercel Project Settings → Environment Variables**:

- `BOT_TOKEN` (Telegram bot token)
- `HIKERAPI_TOKEN` (HikerAPI key)

For webhook registration, also add (or set locally when running `set_webhook.py`):

- `WEBHOOK_BASE_URL` = `https://your-project.vercel.app`
- `WEBHOOK_PATH` (optional) = `/api/telegram`
- `ALLOWED_UPDATES` (optional) = comma-separated list (Telegram update types)

### 3) Register the webhook (run once)
After deploying (so you have a real public URL), run:

```bash
WEBHOOK_BASE_URL="https://your-project.vercel.app" \
WEBHOOK_PATH="/api/telegram" \
python set_webhook.py
```

This calls Telegram’s `setWebhook` so Telegram starts sending updates to your Vercel endpoint.

### 4) Test
In Telegram:
- Send `/start`
- The bot should respond with the welcome message

### Notes / Troubleshooting
- Telegram requires the webhook URL to be publicly reachable via **HTTPS**.
- If updates don’t arrive:
  - verify your `WEBHOOK_BASE_URL`
  - verify Telegram webhook info in Telegram’s `getWebhookInfo`
