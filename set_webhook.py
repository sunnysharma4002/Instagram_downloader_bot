import os
import sys

from aiogram import Bot

from config import BOT_TOKEN

WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "").rstrip("/")
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/api/telegram")
ALLOWED_UPDATES = os.environ.get("ALLOWED_UPDATES")  # optional CSV


def main() -> None:
    if not WEBHOOK_BASE_URL:
        print("Missing env var WEBHOOK_BASE_URL (e.g. https://your-project.vercel.app)")
        sys.exit(1)

    webhook_url = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

    bot = Bot(token=BOT_TOKEN)

    allowed_updates = None
    if ALLOWED_UPDATES:
        allowed_updates = [x.strip() for x in ALLOWED_UPDATES.split(",") if x.strip()]

    # Telegram requires a public HTTPS URL.
    kwargs = {}
    if allowed_updates is not None:
        kwargs["allowed_updates"] = allowed_updates

    # Set webhook
    # Note: aiogram's Bot method name may vary by version; Bot.set_webhook is typical.
    bot.set_webhook(url=webhook_url, **kwargs)

    print(f"Webhook set to: {webhook_url}")


if __name__ == "__main__":
    main()
