import json
from typing import Any


# Vercel expects an ASGI/WSGI compatible export depending on runtime.
# In Python serverless, the common pattern is to expose `handler(request)`
# or `app = ...`. We’ll provide a `handler` that works with many Vercel Python setups.
#
# If your Vercel Python runtime expects a different entry, adjust the export name.
def handler(request: Any):
    """
    Telegram webhook endpoint.

    - Accepts POST with JSON body (Telegram Update)
    - Forwards update dict into aiogram webhook processing
    """
    if getattr(request, "method", None) != "POST":
        return {
            "statusCode": 405,
            "body": "Method Not Allowed",
            "headers": {"Content-Type": "text/plain"},
        }

    try:
        # Vercel Python request body access varies by runtime.
        # Prefer request.json() if available; fallback to raw body.
        if hasattr(request, "json"):
            update = request.json()
        else:
            raw = request.body  # bytes in many runtimes
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            update = json.loads(raw)
    except Exception:
        return {
            "statusCode": 400,
            "body": "Bad Request: invalid JSON",
            "headers": {"Content-Type": "text/plain"},
        }

    # Lazy import to avoid Vercel build-time scanner failures.
    # The bot module imports aiogram, hikerapi, and config which require
    # environment variables -- those are only available at runtime, not during
    # Vercel's deployment scan phase.
    import asyncio
    from bot import handle_update

    try:
        asyncio.run(handle_update(update))
    except RuntimeError:
        # If there's already an event loop (rare depending on runtime), fall back.
        loop = asyncio.get_event_loop()
        loop.run_until_complete(handle_update(update))

    return {
        "statusCode": 200,
        "body": "OK",
        "headers": {"Content-Type": "text/plain"},
    }
