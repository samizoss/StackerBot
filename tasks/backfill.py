import logging
import time
from datetime import datetime

from scraper import notion_client, substack, youtube
from scraper.utils import is_duplicate, normalize_title

log = logging.getLogger(__name__)


def run():
    log.info("--- Starting full backfill ---")

    existing_titles = notion_client.get_all_notion_titles()
    all_posts = substack.fetch_full_archive()

    new_count = 0
    skip_count = 0

    for post in all_posts:
        title = post.get("title", "").strip()
        slug = post.get("slug", "")
        canonical_url = post.get("canonical_url", "")
        url = canonical_url or slug
        post_date = post.get("post_date", "")

        if not title:
            continue

        if is_duplicate(title, existing_titles):
            skip_count += 1
            continue

        # Parse date
        try:
            dt = datetime.fromisoformat(post_date.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")

        log.info(f"Importing: {title[:60]}...")
        new_count += 1

        content_blocks, embedded_yt_id = substack.parse_substack_content(url)

        yt_url = None
        transcript = ""

        if embedded_yt_id:
            yt_url = f"https://www.youtube.com/watch?v={embedded_yt_id}"
        else:
            yt_url = youtube.find_matching_video_rss(title)

        if yt_url:
            transcript = youtube.get_transcript_from_api(yt_url)

        success = notion_client.create_notion_page({
            "title": title,
            "date": date_str,
            "url": url,
            "content_blocks": content_blocks,
            "transcript": transcript,
            "yt_url": yt_url,
        })

        if success:
            log.info(f"  Imported ({new_count}).")
            existing_titles.add(normalize_title(title))

        time.sleep(2)

    log.info(f"Backfill complete. Imported {new_count} new posts, skipped {skip_count} duplicates.")
