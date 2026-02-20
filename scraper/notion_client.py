import logging

from scraper import config
from scraper.utils import get_resilient_session, normalize_title, text_to_blocks_simple

log = logging.getLogger(__name__)

HEADERS = None


def _headers():
    global HEADERS
    if HEADERS is None:
        HEADERS = {
            "Authorization": f"Bearer {config.NOTION_SECRET}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
    return HEADERS


# --- Queries ---


def get_all_notion_titles():
    log.info("Syncing with Notion database (full history)...")
    url = f"https://api.notion.com/v1/databases/{config.DATABASE_ID}/query"

    normalized_titles = set()
    has_more = True
    next_cursor = None

    try:
        while has_more:
            payload = {"page_size": 100}
            if next_cursor:
                payload["start_cursor"] = next_cursor

            session = get_resilient_session()
            response = session.post(url, headers=_headers(), json=payload)
            if response.status_code != 200:
                log.error(f"Notion sync error: {response.status_code}")
                break

            data = response.json()
            for page in data.get("results", []):
                try:
                    title_list = page.get("properties", {}).get("Name", {}).get("title", [])
                    if title_list:
                        raw_title = title_list[0].get("plain_text", "")
                        normalized_titles.add(normalize_title(raw_title))
                except Exception:
                    continue

            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        log.info(f"Sync complete. Found {len(normalized_titles)} existing posts.")
        return normalized_titles

    except Exception as e:
        log.error(f"Connection error during sync: {e}")
        return set()


def get_all_notion_pages(filter_payload=None):
    log.info("Fetching pages from Notion...")
    url = f"https://api.notion.com/v1/databases/{config.DATABASE_ID}/query"

    payload = filter_payload or {}
    pages = []
    has_more = True
    next_cursor = None

    while has_more:
        if next_cursor:
            payload["start_cursor"] = next_cursor
        session = get_resilient_session()
        response = session.post(url, headers=_headers(), json=payload)
        if response.status_code != 200:
            log.error(f"Notion query error: {response.text}")
            break
        data = response.json()
        pages.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    log.info(f"Found {len(pages)} pages.")
    return pages


def get_incomplete_pages():
    return get_all_notion_pages(
        {"filter": {"property": "YouTube URL", "url": {"is_empty": True}}}
    )


# --- Create / Update ---


def create_notion_page(data):
    url = "https://api.notion.com/v1/pages"

    props = {
        "Name": {"title": [{"text": {"content": str(data["title"])[:2000]}}]},
        "Date": {"date": {"start": data["date"]}},
        "Type": {"select": {"name": "Newsletter"}},
        "Content Status": {"select": {"name": "Complete"}},
    }
    if data.get("url"):
        props["URL"] = {"url": data["url"]}
    if data.get("yt_url"):
        props["YouTube URL"] = {"url": data["yt_url"]}

    children = []
    children.append({"object": "block", "type": "table_of_contents", "table_of_contents": {}})
    children.append({"object": "block", "type": "divider", "divider": {}})

    # Substack content section
    if data.get("content_blocks"):
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"text": {"content": "Substack Content"}}]},
        })
        if data.get("url"):
            children.append({"object": "block", "type": "bookmark", "bookmark": {"url": data["url"]}})
        children.extend(data["content_blocks"])
        children.append({"object": "block", "type": "divider", "divider": {}})

    # YouTube section
    if data.get("yt_url"):
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"text": {"content": "YouTube"}}]},
        })
        children.append({"object": "block", "type": "embed", "embed": {"url": data["yt_url"]}})
        if data.get("transcript"):
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": "Transcript:"}, "annotations": {"bold": True, "italic": True}}
                    ]
                },
            })
            children.extend(text_to_blocks_simple(data["transcript"]))

    session = get_resilient_session()
    try:
        # Create page with empty children first, then append in batches
        payload = {"parent": {"database_id": config.DATABASE_ID}, "properties": props, "children": []}
        response = session.post(url, headers=_headers(), json=payload)

        if response.status_code != 200:
            log.error(f"Notion create error: {response.text}")
            return False

        page_id = response.json()["id"]

        if children:
            append_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            for i in range(0, len(children), 100):
                batch = children[i : i + 100]
                try:
                    session.patch(append_url, headers=_headers(), json={"children": batch})
                except Exception:
                    pass
        return True

    except Exception as e:
        log.error(f"Network error creating page: {e}")
        return False


def set_page_cover(page_id, image_url):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"cover": {"type": "external", "external": {"url": image_url}}}

    session = get_resilient_session()
    response = session.patch(url, headers=_headers(), json=payload)
    if response.status_code == 200:
        log.info("Cover updated.")
    else:
        log.error(f"Cover update failed: {response.text}")


def update_notion_page(page_id, video_url, transcript, is_native=False):
    url_page = f"https://api.notion.com/v1/pages/{page_id}"
    url_blocks = f"https://api.notion.com/v1/blocks/{page_id}/children"
    session = get_resilient_session()

    if not is_native:
        session.patch(url_page, headers=_headers(), json={"properties": {"YouTube URL": {"url": video_url}}})

    children = []
    children.append({"object": "block", "type": "divider", "divider": {}})
    header_text = "Substack Video" if is_native else "YouTube (Repaired)"
    children.append({
        "object": "block",
        "type": "heading_1",
        "heading_1": {"rich_text": [{"text": {"content": header_text}}]},
    })

    if not is_native:
        children.append({"object": "block", "type": "embed", "embed": {"url": video_url}})
    else:
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {"rich_text": [{"text": {"content": "Watch Video on Substack"}}], "icon": {"emoji": "\U0001f4fa"}},
        })

    if transcript:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"text": {"content": "Transcript:"}, "annotations": {"bold": True, "italic": True}}
                ]
            },
        })
        children.extend(text_to_blocks_simple(transcript))

    for i in range(0, len(children), 100):
        try:
            session.patch(url_blocks, headers=_headers(), json={"children": children[i : i + 100]})
        except Exception:
            pass

    log.info("Page updated.")
