import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """
    Telegram webhook endpoint for Vercel Python serverless functions.

    Vercel's Python runtime requires handler to be a class that inherits
    from http.server.BaseHTTPRequestHandler.
    """

    def do_POST(self):
        # Read the request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            update = json.loads(body)
        except Exception:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bad Request: invalid JSON")
            return

        # Lazy import to avoid Vercel build-time scanner failures.
        # The bot module imports aiogram, hikerapi, and config which require
        # environment variables -- those are only available at runtime.
        import asyncio
        from bot import handle_update

        try:
            asyncio.run(handle_update(update))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(handle_update(update))

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        # Return 405 for any method other than POST
        self.send_response(405)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Method Not Allowed")
