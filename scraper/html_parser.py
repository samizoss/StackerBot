from bs4 import NavigableString, Tag

from scraper.utils import get_video_id_from_url


def parse_rich_text(tag):
    rich_text = []
    if isinstance(tag, NavigableString):
        if str(tag).strip():
            return [{"type": "text", "text": {"content": str(tag)[:2000]}}]
        return []

    for child in tag.children:
        if isinstance(child, NavigableString):
            text_content = str(child)
            if text_content:
                rich_text.append({"type": "text", "text": {"content": text_content[:2000]}})
        elif isinstance(child, Tag):
            text_content = child.get_text()
            if not text_content:
                continue
            annotations = {
                "bold": child.name in ["b", "strong"],
                "italic": child.name in ["i", "em"],
                "strikethrough": child.name in ["s", "strike", "del"],
                "underline": child.name in ["u"],
                "code": child.name in ["code"],
            }
            text_obj = {
                "type": "text",
                "text": {"content": text_content[:2000]},
                "annotations": annotations,
            }
            if child.name == "a" and child.get("href"):
                text_obj["text"]["link"] = {"url": child["href"]}
            if child.find("a"):
                link = child.find("a")
                if link and link.get("href"):
                    text_obj["text"]["link"] = {"url": link["href"]}
            rich_text.append(text_obj)

    if not rich_text and tag.get_text().strip():
        return [{"type": "text", "text": {"content": tag.get_text()[:2000]}}]
    return rich_text


def process_element_to_block(element):
    # Code blocks
    if element.name == "pre":
        code_text = element.get_text()[:2000]
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": code_text}}],
                "language": "plain text",
            },
        }

    # Headings
    if element.name in ["h1", "h2", "h3"]:
        level = "heading_2" if element.name in ["h1", "h2"] else "heading_3"
        rt = parse_rich_text(element)
        if rt:
            return {"object": "block", "type": level, level: {"rich_text": rt}}

    # List items
    if element.name == "li":
        rt = parse_rich_text(element)
        if rt:
            return {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rt},
            }

    if element.name == "ul":
        return None

    # Blockquotes
    if element.name == "blockquote":
        rt = parse_rich_text(element)
        if rt:
            return {"object": "block", "type": "quote", "quote": {"rich_text": rt}}

    # Images
    if element.name in ("img", "figure") or element.find("img"):
        img = element if element.name == "img" else element.find("img")
        if img and img.get("src"):
            src = img.get("src")
            if src.startswith("http"):
                return {
                    "object": "block",
                    "type": "image",
                    "image": {"type": "external", "external": {"url": src}},
                }

    # Paragraphs
    if element.name == "p":
        text_content = element.get_text().strip()
        if not text_content:
            return None
        if len(text_content) > 1900:
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text_content[:1900]}}]
                },
            }
        rt = parse_rich_text(element)
        if rt:
            return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt}}

    return None


def html_to_notion_blocks(soup_content):
    blocks = []
    found_yt_id = None

    def process_container(container):
        nonlocal found_yt_id
        for element in container.find_all(recursive=False):
            # Detect embedded YouTube
            if element.name == "iframe" and "youtube" in str(element.get("src", "")):
                found_yt_id = get_video_id_from_url(element["src"])
            if element.find("a") and "youtube.com/watch" in str(
                element.find("a").get("href", "")
            ):
                found_yt_id = get_video_id_from_url(element.find("a")["href"])

            # Recurse into divs
            if element.name == "div":
                process_container(element)
                continue

            # Recurse into links wrapping images
            if element.name == "a" and element.find("img"):
                process_container(element)
                continue

            # Handle lists
            if element.name in ["ul", "ol"]:
                for li in element.find_all("li", recursive=False):
                    b = process_element_to_block(li)
                    if b:
                        if element.name == "ol":
                            b["type"] = "numbered_list_item"
                            b["numbered_list_item"] = b.pop("bulleted_list_item")
                        blocks.append(b)
                continue

            block = process_element_to_block(element)
            if block:
                blocks.append(block)

    process_container(soup_content)
    return blocks, found_yt_id
