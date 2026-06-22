import asyncio
import os
import sys

from aiogram import Bot

from config import BOT_TOKEN

# Auto-detect Vercel URL:
# 1. Try WEBHOOK_BASE_URL env var (explicit override)
# 2. Try VERCEL_URL env var (set by Vercel during deployment)
# 3. Fall back to the default Vercel project URL
VERCEL_DOMAIN = os.environ.get("WEBHOOK_BASE_URL") or os.environ.get("VERCEL_URL")
if VERCEL_DOMAIN:
    VERCEL_DOMAIN = VERCEL_DOMAIN.rstrip("/")
    if not VERCEL_DOMAIN.startswith("http"):
        VERCEL_DOMAIN = f"https://{VERCEL_DOMAIN}"
else:
    VERCEL_DOMAIN = "https://instagram-downloader-bot-murex.vercel.app"

WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/api/index")
ALLOWED_UPDATES = os.environ.get("ALLOWED_UPDATES")


async def main() -> None:
    webhook_url = f"{VERCEL_DOMAIN}{WEBHOOK_PATH}"

    bot = Bot(token=BOT_TOKEN)

    allowed_updates = None
    if ALLOWED_UPDATES:
        allowed_updates = [x.strip() for x in ALLOWED_UPDATES.split(",") if x.strip()]

    kwargs = {}
    if allowed_updates is not None:
        kwargs["allowed_updates"] = allowed_updates

    # Verify current webhook status first
    info = await bot.get_webhook_info()
    if info.url == webhook_url:
        print(f"Webhook already set to: {webhook_url}")
    else:
        if info.url:
            print(f"Updating webhook from: {info.url}")
        await bot.set_webhook(url=webhook_url, **kwargs)
        print(f"Webhook set to: {webhook_url}")

    # Print summary
    print(f"  Pending updates: {info.pending_update_count}")
    print(f"  Has custom cert: {info.has_custom_certificate}")

    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
