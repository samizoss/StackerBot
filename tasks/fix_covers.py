import logging
import time

from scraper import notion_client, substack

log = logging.getLogger(__name__)


def run():
    log.info("--- Starting cover image fixer ---")

    all_pages = notion_client.get_all_notion_pages(
        {"filter": {"property": "URL", "url": {"is_not_empty": True}}}
    )

    count = 0
    for page in all_pages:
        if page.get("cover"):
            continue

        try:
            props = page.get("properties", {})
            title_list = props.get("Name", {}).get("title", [])
            if not title_list:
                continue
            title = title_list[0].get("plain_text", "Untitled")

            substack_url = props.get("URL", {}).get("url")
            if not substack_url:
                continue

            log.info(f"Checking cover: {title[:40]}...")

            image_url = substack.get_substack_cover_image(substack_url)

            if image_url:
                log.info(f"Found image: {image_url[:50]}...")
                notion_client.set_page_cover(page["id"], image_url)
                count += 1
                time.sleep(0.5)
            else:
                log.info("No image found.")

        except Exception as e:
            log.error(f"Error processing page: {e}")

    log.info(f"Cover fixer done. Updated {count} covers.")
