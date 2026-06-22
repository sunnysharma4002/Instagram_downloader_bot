import asyncio
import logging
import random
import re

import httpx
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message,
    BufferedInputFile,
    InputMediaPhoto,
    InputMediaVideo,
)
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramEntityTooLarge, TelegramRetryAfter
from hikerapi import AsyncClient

from config import BOT_TOKEN, HIKERAPI_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

router = Router()
hk = AsyncClient(token=HIKERAPI_TOKEN, timeout=60)

# Fix: anchored regex, dots in path allowed, non-greedy host match only for instagram.com
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_./?=&%-]+"
)

PROMO_MESSAGES = [
    "\u26a1 <a href='https://hikerapi.com/p/hsazcgym'>HikerAPI</a> \u2014 Fast Instagram API for developers",
    "\u26a1 <a href='https://lamatok.com/p/s6kl8mtn'>Lamatok</a> \u2014 Fast TikTok API for developers",
    "\u26a1 <a href='https://datalikers.com/p/1by27bwg'>Datalikers</a> \u2014 Instagram & TikTok data: datasets, MCP, low-cost API",
]

# Fix: PROMO_MESSAGE -> random.choice(PROMO_MESSAGES) at runtime, not at module level
WELCOME_MESSAGE = (
    "\U0001f44b <b>Welcome to Instagram Downloader Bot!</b>\n\n"
    "Send me any Instagram link and I'll download the content for you.\n\n"
    "<b>Supported links:</b>\n"
    "\u2022 Posts, Reels, IGTV\n"
    "\u2022 Stories\n"
    "\u2022 Highlights\n"
    "\u2022 Share links (/s/)\n\n"
    "Just paste an Instagram URL and I'll handle the rest!"
)

HELP_MESSAGE = (
    "\U0001f4d6 <b>How to use this bot:</b>\n\n"
    "<b>1.</b> Copy an Instagram link\n"
    "<b>2.</b> Paste it here\n"
    "<b>3.</b> Wait for the media to be downloaded\n\n"
    "<b>Supported URL formats:</b>\n"
    "\u2022 <code>instagram.com/p/...</code> \u2014 Posts\n"
    "\u2022 <code>instagram.com/reel/...</code> \u2014 Reels\n"
    "\u2022 <code>instagram.com/tv/...</code> \u2014 IGTV\n"
    "\u2022 <code>instagram.com/stories/username/id</code> \u2014 Single story\n"
    "\u2022 <code>instagram.com/stories/username/</code> \u2014 All stories\n"
    "\u2022 <code>instagram.com/s/...</code> \u2014 Share links\n"
    "\u2022 <code>instagram.com/highlights/...</code> \u2014 Highlights"
)


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_instagram_url(url: str) -> tuple[str, dict]:
    clean = url.split("?")[0].rstrip("/")

    m = re.search(r"/highlights/(\d+)", clean)
    if m:
        return "highlight", {"highlight_id": m.group(1), "url": url}

    m = re.search(r"/stories/([\w.\-]+)/(\d+)", clean)
    if m:
        return "story_single", {"username": m.group(1), "story_id": m.group(2), "url": url}

    m = re.search(r"/stories/([\w.\-]+)/?$", clean)
    if m:
        return "stories_all", {"username": m.group(1)}

    if re.search(r"/(p|reel|tv)/", clean):
        return "media", {"url": url}

    if "/s/" in clean:
        return "share", {"url": url}

    return "media", {"url": url}


# ---------------------------------------------------------------------------
# Media download & send helpers
# ---------------------------------------------------------------------------

async def download_resource(url: str) -> bytes:
    return await hk.save_media(url)


async def download_with_refresh(media_id: str | None, resource_url: str) -> bytes:
    current_url = resource_url
    for attempt in range(3):
        try:
            return await download_resource(current_url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403 and media_id and attempt < 2:
                logger.warning("Forbidden on attempt %d, refreshing media %s", attempt + 1, media_id)
                refreshed = await hk.media_by_id_v1(media_id)
                current_url = _extract_best_url(refreshed)
            else:
                raise
    raise Exception("Failed to download after 3 attempts")


def _extract_best_url(media: dict) -> str:
    if media.get("media_type") == 2 and media.get("video_url"):
        return media["video_url"]
    return media.get("thumbnail_url", "")


async def send_with_retry(coro_factory, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except TelegramRetryAfter as e:
            if attempt < max_retries - 1:
                logger.warning("Rate limited, retrying in %d seconds", e.retry_after)
                await asyncio.sleep(e.retry_after)
            else:
                raise


def _extract_caption(media: dict) -> str:
    cap = media.get("caption")
    if isinstance(cap, dict):
        return cap.get("text", "")
    return media.get("caption_text", "") or (cap if isinstance(cap, str) else "")


async def send_single_media(message: Message, media: dict) -> None:
    media_type = media.get("media_type", 1)
    media_id = str(media.get("pk") or media.get("id") or "")
    caption = _extract_caption(media)

    if media_type == 2:
        video_url = media.get("video_url", "")
        try:
            data = await download_with_refresh(media_id, video_url)
        except Exception as e:
            logger.warning("Failed to download video %s: %s", media_id, e)
            await message.answer(
                f"\U0001f3ac Failed to download video.\n<a href='{video_url}'>Direct link</a>",
                parse_mode=ParseMode.HTML,
            )
            return
        f = BufferedInputFile(data, filename=f"{media_id}.mp4")
        try:
            await send_with_retry(lambda f=f, c=caption: message.answer_video(video=f, caption=c or None))
        except TelegramEntityTooLarge:
            await message.answer(
                f"\U0001f3ac Video is too large for Telegram.\n<a href='{video_url}'>Direct link</a>",
                parse_mode=ParseMode.HTML,
            )
            return
        # Raw file
        try:
            raw = BufferedInputFile(data, filename=f"{media_id}.mp4")
            await send_with_retry(lambda r=raw: message.answer_document(document=r, disable_content_type_detection=True))
        except Exception as e:
            logger.warning("Failed to send raw document: %s", e)
    else:
        thumbnail_url = media.get("thumbnail_url", "")
        try:
            data = await download_with_refresh(media_id, thumbnail_url)
        except Exception as e:
            logger.warning("Failed to download photo %s: %s", media_id, e)
            await message.answer(
                f"\U0001f5bc Failed to download photo.\n<a href='{thumbnail_url}'>Direct link</a>",
                parse_mode=ParseMode.HTML,
            )
            return
        f = BufferedInputFile(data, filename=f"{media_id}.jpg")
        try:
            await send_with_retry(lambda f=f, c=caption: message.answer_photo(photo=f, caption=c or None))
        except TelegramEntityTooLarge:
            await message.answer(
                f"\U0001f5bc Photo is too large for Telegram.\n<a href='{thumbnail_url}'>Direct link</a>",
                parse_mode=ParseMode.HTML,
            )
            return
        try:
            raw = BufferedInputFile(data, filename=f"{media_id}.jpg")
            await send_with_retry(lambda r=raw: message.answer_document(document=r, disable_content_type_detection=True))
        except Exception as e:
            logger.warning("Failed to send raw document: %s", e)


async def send_carousel(message: Message, media: dict) -> None:
    resources = media.get("resources", [])
    if not resources:
        await message.answer("No media found in this carousel.")
        return

    media_id = str(media.get("pk") or media.get("id") or "")
    caption = _extract_caption(media)
    input_items = []
    for res in resources:
        try:
            if res.get("media_type") == 2 and res.get("video_url"):
                data = await download_with_refresh(media_id, res["video_url"])
                input_items.append(InputMediaVideo(media=BufferedInputFile(data, filename="video.mp4")))
            else:
                data = await download_with_refresh(media_id, res.get("thumbnail_url", ""))
                input_items.append(InputMediaPhoto(media=BufferedInputFile(data, filename="photo.jpg")))
        except Exception as e:
            logger.warning("Failed to download carousel item: %s", e)

    if not input_items:
        await message.answer("Failed to download carousel items.")
        return

    if caption and input_items:
        input_items[0].caption = caption

    for i in range(0, len(input_items), 10):
        chunk = input_items[i : i + 10]
        try:
            await send_with_retry(lambda c=chunk: message.answer_media_group(media=c))
        except TelegramEntityTooLarge:
            await message.answer("Some media in this album is too large for Telegram.")


async def send_media_item(message: Message, media: dict) -> None:
    if media.get("media_type") == 8:
        await send_carousel(message, media)
    else:
        await send_single_media(message, media)


async def send_multiple_items(message: Message, items: list, label: str = "items") -> None:
    if not items:
        await message.answer(f"No {label} found.")
        return

    await message.answer(f"\U0001f4e6 Found {len(items)} {label}. Downloading...")
    for idx, item in enumerate(items, 1):
        try:
            await send_media_item(message, item)
        except Exception as e:
            logger.error("Failed to send item %d/%d: %s", idx, len(items), e)
            await message.answer(f"Failed to download item {idx}/{len(items)}.")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_MESSAGE, parse_mode=ParseMode.HTML)


@router.message(F.text == "/help")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_MESSAGE, parse_mode=ParseMode.HTML)


@router.message(F.text)
async def handle_message(message: Message, bot: Bot) -> None:
    text = message.text or ""
    match = INSTAGRAM_URL_PATTERN.search(text)
    if not match:
        await message.answer(
            "Please send me an Instagram link to download content.\n"
            "Use /help to see supported formats."
        )
        return

    url = match.group(0)
    link_type, params = parse_instagram_url(url)

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    try:
        if link_type == "media":
            media = await hk.media_by_url_v1(params["url"])
            await send_media_item(message, media)

        elif link_type == "story_single":
            story = await hk.story_by_url_v1(params["url"])
            await send_media_item(message, story)

        elif link_type == "stories_all":
            stories = await hk.user_stories_by_username_v1(params["username"])
            await send_multiple_items(message, stories, label="stories")

        elif link_type == "highlight":
            highlight = await hk.highlight_by_url_v1(params["url"])
            items = highlight.get("items", []) if isinstance(highlight, dict) else []
            if items:
                await send_multiple_items(message, items, label="highlight items")
            else:
                await send_media_item(message, highlight)

        elif link_type == "share":
            share_data = await hk.share_by_url_v1(params["url"])
            await send_media_item(message, share_data)

        await message.answer(random.choice(PROMO_MESSAGES), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    except Exception as e:
        error_str = str(e).lower()
        if "not found" in error_str or "404" in error_str:
            await message.answer("\u274c Content not found. The post may have been deleted or the URL is invalid.")
        elif "403" in error_str or "private" in error_str:
            await message.answer("\U0001f512 This account is private. Cannot access the content.")
        else:
            logger.error("Error: %s", e, exc_info=True)
            await message.answer("\u26a0\ufe0f Something went wrong. Please try again later.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Webhook support (Vercel)
# ---------------------------------------------------------------------------

# Create the dispatcher once at module level with the router attached.
# A router cannot be attached to more than one dispatcher, and recreating
# the dispatcher on every request would require re-registering all handlers.
_dp = Dispatcher()
_dp.include_router(router)


async def handle_update(update: dict) -> None:
    """
    Process a single Telegram update (webhook mode).

    Creates a fresh Bot per request (aiogram bot sessions are bound to the
    event loop, and Vercel's BaseHTTPRequestHandler runs each request in a
    potentially different thread with its own event loop).
    """
    bot = Bot(token=BOT_TOKEN)
    try:
        await _dp.feed_webhook_update(bot, update)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    raise RuntimeError(
        "This bot is now configured for webhook mode. "
        "Deploy to Vercel and call the webhook endpoint instead of running polling."
    )
