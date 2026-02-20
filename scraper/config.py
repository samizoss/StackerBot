import os
from dotenv import load_dotenv

load_dotenv()

# Required
NOTION_SECRET = os.environ.get("NOTION_SECRET", "")
DATABASE_ID = os.environ.get("DATABASE_ID", "")
SUBSTACK_RSS_URL = os.environ.get("SUBSTACK_RSS_URL", "")

# Optional
SUBSTACK_NAME = os.environ.get("SUBSTACK_NAME", "")
SUBSTACK_COOKIE = os.environ.get("SUBSTACK_COOKIE", "")
TRANSCRIPT_API_KEY = os.environ.get("TRANSCRIPT_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def validate():
    missing = []
    if not NOTION_SECRET:
        missing.append("NOTION_SECRET")
    if not DATABASE_ID:
        missing.append("DATABASE_ID")
    if not SUBSTACK_RSS_URL:
        missing.append("SUBSTACK_RSS_URL")
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
