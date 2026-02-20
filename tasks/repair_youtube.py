import logging
import time

from scraper import notion_client, substack, youtube

log = logging.getLogger(__name__)


def run():
    log.info("--- Starting YouTube repair ---")

    incomplete_pages = notion_client.get_incomplete_pages()

    for page in incomplete_pages:
        page_id = page["id"]
        try:
            title = page["properties"]["Name"]["title"][0]["plain_text"]
            substack_url = page["properties"]["URL"]["url"]
        except (KeyError, IndexError):
            continue

        log.info(f"Checking: {title[:40]}...")
        vid_type, vid_data = substack.find_video_on_substack_page(substack_url)

        transcript = ""
        final_url = ""
        is_native = False

        if vid_type == "youtube":
            final_url = f"https://www.youtube.com/watch?v={vid_data}"
            transcript = youtube.get_transcript_from_video_id(vid_data)
        elif vid_type == "native_vtt":
            is_native = True
            final_url = substack_url
            transcript = youtube.get_transcript_from_vtt_url(vid_data)

        if transcript or vid_type == "youtube":
            if transcript:
                log.info(f"Transcript found ({len(transcript)} chars)")
            notion_client.update_notion_page(page_id, final_url, transcript, is_native)
        else:
            log.info("No video access. Skipping.")

        time.sleep(1)

    log.info("YouTube repair complete.")
