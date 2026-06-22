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
        try:
            import asyncio
            from bot import handle_update
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Import error: {e}".encode())
            return

        loop = None
        try:
            # BaseHTTPRequestHandler runs in a thread pool, so we must create
            # a fresh event loop for each invocation.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handle_update(update))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Handler error: {e}".encode())
            return
        finally:
            if loop is not None:
                loop.close()

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
