import logging

import feedparser

from scraper import config
from scraper.utils import fuzzy_match, get_resilient_session, get_video_id_from_url

log = logging.getLogger(__name__)


def find_matching_video_rss(substack_title):
    if not config.YOUTUBE_CHANNEL_ID:
        return None

    log.info("Checking YouTube RSS for match...")
    youtube_rss = f"https://www.youtube.com/feeds/videos.xml?channel_id={config.YOUTUBE_CHANNEL_ID}"
    feed = feedparser.parse(youtube_rss)

    best_match = None
    highest_score = 0
    clean_substack = substack_title.lower().strip()

    for entry in feed.entries[:100]:
        # Exact substring match first
        if clean_substack in entry.title.lower() or entry.title.lower() in clean_substack:
            log.info(f"Exact match found: '{entry.title}'")
            return entry.link

        score = fuzzy_match(substack_title, entry.title)
        if score > highest_score:
            highest_score = score
            best_match = entry

    if highest_score > 0.70 and best_match:
        log.info(f"Close match found: '{best_match.title}' ({highest_score:.2f})")
        return best_match.link

    if highest_score > 0.50 and best_match:
        log.info(f"Weak match (skipping): '{best_match.title}' ({highest_score:.2f})")

    return None


def get_transcript_from_api(video_url):
    if not config.TRANSCRIPT_API_KEY:
        return ""
    if not video_url or "youtube" not in str(video_url):
        return ""

    log.info(f"Fetching transcript for: {video_url}")
    session = get_resilient_session()
    try:
        response = session.get(
            "https://transcriptapi.com/api/v2/youtube/transcript",
            headers={"Authorization": f"Bearer {config.TRANSCRIPT_API_KEY}"},
            params={"video_url": video_url, "format": "json"},
        )
        if response.status_code == 200:
            data = response.json()
            if "transcript" in data:
                full_text = " ".join([item["text"] for item in data["transcript"]])
                full_text = full_text.replace("  ", " ").strip()
                log.info(f"Transcript found ({len(full_text)} chars)")
                return full_text
    except Exception as e:
        log.error(f"Transcript API error: {e}")
    return ""


def get_transcript_from_video_id(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    return get_transcript_from_api(video_url)


def clean_vtt(text):
    lines = text.split("\n")
    unique_lines = []
    last = ""
    for line in lines:
        if "-->" in line or line.strip() == "" or line.strip().isdigit() or "WEBVTT" in line:
            continue
        clean = line.strip()
        if clean != last:
            unique_lines.append(clean)
        last = clean
    return " ".join(unique_lines)


def get_transcript_from_vtt_url(vtt_url):
    log.info("Downloading VTT file...")
    headers = config.BROWSER_HEADERS.copy()
    if config.SUBSTACK_COOKIE:
        headers["Cookie"] = config.SUBSTACK_COOKIE
    try:
        import requests

        resp = requests.get(vtt_url, headers=headers)
        if resp.status_code == 200:
            return clean_vtt(resp.text)
        else:
            log.error(f"VTT download failed: status {resp.status_code}")
    except Exception as e:
        log.error(f"VTT network error: {e}")
    return ""
