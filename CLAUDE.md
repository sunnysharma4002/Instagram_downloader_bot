# Instagram Downloader Telegram Bot - Development Notes

## Project Structure

```
bot.py          - Main entry point, aiogram handlers, media sending logic
api_client.py   - HikerAPI client using hikerapi SDK + httpx for CDN downloads
config.py       - Environment variable configuration
requirements.txt
Dockerfile
docker-compose.yml
```

## Architecture

- **Framework**: aiogram 3.22 (async Telegram bot framework)
- **API client**: hikerapi AsyncClient — natively async
- **CDN downloads**: httpx async for downloading media bytes
- **State**: Stateless, no database
- **Deployment**: Docker with docker-compose

## Key Design Decisions

- Media is downloaded into memory (BufferedInputFile) before sending to Telegram. This avoids issues with expired Instagram CDN URLs.
- On "Forbidden for url" errors during download, the bot refreshes media metadata via `/v1/media/by/id` and retries with the new URL (up to 3 attempts).
- TelegramEntityTooLarge errors are caught and the bot falls back to sending the direct URL as a link.
- TelegramRetryAfter is handled with automatic sleep and retry (up to 3 times).
- Carousels (media_type 8) are sent as media groups, chunked into groups of 10 (Telegram's limit).

## HikerAPI Endpoints Used

- `GET /v1/media/by/url` — Fetch post/reel/tv info
- `GET /v1/media/by/id` — Refresh expired media URLs
- `GET /v1/story/by/url` — Fetch single story
- `GET /v1/story/by/id` — Fetch story by ID
- `GET /v1/user/stories/by/username` — Fetch all user stories
- `GET /v1/highlight/by/url` — Fetch highlight
- `GET /v1/highlight/by/id` — Fetch highlight by ID
- `GET /v1/user/highlights/by/username` — Fetch all user highlights
- `GET /v1/share/by/url` — Resolve /s/ share links

Auth: `x-access-key` header with the HIKERAPI_TOKEN.

## URL Parsing

The `parse_instagram_url()` function in bot.py classifies URLs into types:
- `/highlights/<id>` -> highlight
- `/stories/<username>/<id>` -> story_single
- `/stories/<username>` -> stories_all
- `/p/`, `/reel/`, `/tv/` -> media
- `/s/` -> share

## Media Types (Instagram)

- `media_type 1` = Photo -> `send_photo`
- `media_type 2` = Video -> `send_video`
- `media_type 8` = Carousel/Album -> `send_media_group`

## Running Locally

```bash
export BOT_TOKEN=your_token
export HIKERAPI_TOKEN=your_token
pip install -r requirements.txt
python bot.py
```

## Environment Variables

- `BOT_TOKEN` — Telegram bot token from BotFather
- `HIKERAPI_TOKEN` — HikerAPI access key from hikerapi.com
