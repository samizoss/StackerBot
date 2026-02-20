import logging
import time

from scraper import notion_client, substack, youtube
from scraper.utils import fix_date_iso, is_duplicate, normalize_title

log = logging.getLogger(__name__)


def run():
    log.info("--- Starting daily sync ---")

    existing_titles = notion_client.get_all_notion_titles()
    entries = substack.fetch_rss_entries()

    new_posts_count = 0

    for entry in entries:
        title = entry.title.strip()
        link = entry.link.split("?")[0]
        pub_date = fix_date_iso(entry.published_parsed)

        if is_duplicate(title, existing_titles):
            log.info(f"Skipping (already in DB): {title[:30]}...")
            continue

        log.info(f"New post found: {title}")
        new_posts_count += 1

        content_blocks, embedded_yt_id = substack.parse_substack_content(link)

        yt_url = None
        transcript = ""

        if embedded_yt_id:
            log.info(f"Found embedded video ID: {embedded_yt_id}")
            yt_url = f"https://www.youtube.com/watch?v={embedded_yt_id}"
        else:
            log.info("No embedded video, checking YouTube RSS...")
            yt_url = youtube.find_matching_video_rss(title)

        if yt_url:
            transcript = youtube.get_transcript_from_api(yt_url)
        else:
            log.info("No YouTube video found for this post.")

        success = notion_client.create_notion_page({
            "title": title,
            "date": pub_date,
            "url": link,
            "content_blocks": content_blocks,
            "transcript": transcript,
            "yt_url": yt_url,
        })

        if success:
            log.info("Successfully imported to Notion.")
            existing_titles.add(normalize_title(title))

        time.sleep(2)

    if new_posts_count == 0:
        log.info("No new posts found. Database is up to date.")
    else:
        log.info(f"Imported {new_posts_count} new items.")

    # Also run cover backfill (fast and idempotent)
    from tasks.fix_covers import run as fix_covers_run

    fix_covers_run()
