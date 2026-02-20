import logging
import re

import feedparser
import requests
from bs4 import BeautifulSoup

from scraper import config
from scraper.html_parser import html_to_notion_blocks
from scraper.utils import get_resilient_session, get_video_id_from_url

log = logging.getLogger(__name__)


def fetch_rss_entries():
    log.info(f"Fetching RSS from {config.SUBSTACK_RSS_URL}")
    feed = feedparser.parse(config.SUBSTACK_RSS_URL)
    log.info(f"Found {len(feed.entries)} entries in RSS feed.")
    return feed.entries


def fetch_full_archive():
    """Fetches ALL posts via Substack's archive API (not limited to 20 like RSS)."""
    base_url = config.SUBSTACK_RSS_URL.replace("/feed", "")
    log.info(f"Fetching full archive from {base_url}")

    headers = config.BROWSER_HEADERS.copy()
    if config.SUBSTACK_COOKIE:
        headers["Cookie"] = config.SUBSTACK_COOKIE

    all_posts = []
    offset = 0
    while offset < 10000:
        r = requests.get(
            f"{base_url}/api/v1/archive?sort=new&offset={offset}&limit=50",
            headers=headers,
            timeout=15,
        )
        if r.status_code != 200:
            log.error(f"Archive API error: {r.status_code} at offset {offset}")
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        all_posts.extend(batch)
        log.info(f"  Fetched {len(all_posts)} posts so far...")
        if len(batch) < 50:
            break
        offset += 50

    log.info(f"Full archive: {len(all_posts)} total posts.")
    return all_posts


def parse_substack_content(url):
    headers = config.BROWSER_HEADERS.copy()
    if config.SUBSTACK_COOKIE:
        headers["Cookie"] = config.SUBSTACK_COOKIE
    session = get_resilient_session()
    try:
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        content_div = (
            soup.find("div", class_="available-content")
            or soup.find("div", class_="body")
            or soup.find("article")
        )
        if content_div:
            return html_to_notion_blocks(content_div)
    except Exception as e:
        log.error(f"Scrape error for {url}: {e}")
    return [], None


def get_substack_cover_image(url):
    if not url:
        return None
    headers = config.BROWSER_HEADERS.copy()
    if config.SUBSTACK_COOKIE:
        headers["Cookie"] = config.SUBSTACK_COOKIE
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_img and twitter_img.get("content"):
            return twitter_img["content"]
    except Exception as e:
        log.error(f"Cover scrape error: {e}")
    return None


def find_video_on_substack_page(url):
    log.info("Visiting Substack page for video detection...")
    headers = config.BROWSER_HEADERS.copy()
    if config.SUBSTACK_COOKIE:
        headers["Cookie"] = config.SUBSTACK_COOKIE

    try:
        response = requests.get(url, headers=headers)
        html = response.text

        # Check for native VTT
        vtt_matches = re.findall(r"(https:[^\"']+\.vtt)", html)
        if not vtt_matches:
            vtt_matches = re.findall(r"(https:\\/\\/[^\"']+\.vtt)", html)
        if vtt_matches:
            vtt_url = vtt_matches[0].replace("\\/", "/")
            log.info("Found hidden VTT URL.")
            return "native_vtt", vtt_url

        # Check for YouTube embeds
        soup = BeautifulSoup(html, "html.parser")
        for iframe in soup.find_all("iframe"):
            src = str(iframe.get("src", ""))
            if "youtube" in src or "youtu.be" in src:
                vid = get_video_id_from_url(src)
                if vid:
                    return "youtube", vid

    except Exception as e:
        log.error(f"Error scraping page: {e}")
    return None, None
