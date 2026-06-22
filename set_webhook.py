"""Helper script to set Telegram webhook to Vercel deployment."""
import httpx
from config import BOT_TOKEN

URL = "https://instagram-downloader-bot-murex.vercel.app/api/index"
API = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

print(f"Setting webhook to: {URL}")
r = httpx.post(API, data={"url": URL}, timeout=30)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")

if r.status_code == 200 and r.json().get("ok"):
    print("SUCCESS: Webhook set!")
else:
    print("FAILED: Could not set webhook")
