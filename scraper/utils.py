import re
import time
from datetime import datetime
from difflib import SequenceMatcher

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def get_resilient_session():
    session = requests.Session()
    retry = Retry(total=3, read=3, connect=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504, 429])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def normalize_title(text):
    if not text:
        return ""
    text = re.sub(r"[^a-zA-Z0-9]", "", str(text))
    return text.lower()


def is_duplicate(new_title, existing_titles_norm):
    new_norm = normalize_title(new_title)

    if new_norm in existing_titles_norm:
        return True

    for existing in existing_titles_norm:
        if len(existing) > 15 and existing in new_norm:
            return True
        if len(new_norm) > 15 and new_norm in existing:
            return True
        if len(existing) > 10:
            ratio = SequenceMatcher(None, new_norm, existing).ratio()
            if ratio > 0.85:
                return True
    return False


def fuzzy_match(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fix_date_iso(date_struct):
    try:
        return time.strftime("%Y-%m-%d", date_struct)
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def get_video_id_from_url(url):
    if not url:
        return None
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", str(url))
    if match:
        return match.group(1)
    return None


def text_to_blocks(text):
    blocks = []
    if not text:
        return blocks
    text = text.replace("\r", "")
    if "\n" not in text and len(text) > 500:
        text = text.replace(". ", ".\n\n")
    chunks = text.split("\n\n")
    for chunk in chunks:
        clean = chunk.strip()
        if not clean:
            continue
        if len(clean) > 1900:
            for i in range(0, len(clean), 1900):
                blocks.append(_paragraph_block(clean[i : i + 1900]))
        else:
            blocks.append(_paragraph_block(clean))
    return blocks


def text_to_blocks_simple(text):
    blocks = []
    if not text:
        return blocks
    chunks = text.split("\n\n")
    for chunk in chunks:
        clean = chunk.strip()
        if not clean:
            continue
        if len(clean) > 1900:
            for i in range(0, len(clean), 1900):
                blocks.append(_paragraph_block(clean[i : i + 1900]))
        else:
            blocks.append(_paragraph_block(clean))
    return blocks


def _paragraph_block(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }
