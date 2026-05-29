# Multi-Substack Single-Service Refactor

**Date:** 2026-05-29
**Status:** Approved (design)

## Problem

StackerBot is hard-wired to a single Substack: `config.py` reads one `SUBSTACK_RSS_URL` /
`SUBSTACK_NAME`, so each newsletter requires its own Railway service. The user runs 5 services
(Nate Jones, Lenny Rachitsky, Dan Kershaw, Philanthropy 451, Limited Edition Jonathan), which
means 5× the management and 5× the manual work for any one-off task like a backfill.

Goal: **one service, one run, all subscriptions** — for both the twice-daily sync and backfill.

## Out of scope

- YouTube **channel-RSS matching** is removed (no feed used it). The `youtube_channel_id` field
  and `config.YOUTUBE_CHANNEL_ID` go away, and `youtube.find_matching_video_rss` is deleted.
- **Kept:** embedded-video detection (videos inside a post, surfaced by the HTML parser) and
  transcript fetching via TranscriptAPI — these need no per-feed config.
- `fix_covers` and `repair_youtube` are unchanged — they already operate database-wide.

## Design

### 1. Feed registry — `substacks.json` (repo root)

```json
[
  { "name": "Nate Jones",              "rss_url": "https://natesnewsletter.substack.com/feed" },
  { "name": "Lenny Rachitsky",         "rss_url": "https://www.lennysnewsletter.com/feed" },
  { "name": "Dan Kershaw",             "rss_url": "https://....substack.com/feed" },
  { "name": "Philanthropy 451",        "rss_url": "https://....substack.com/feed" },
  { "name": "Limited Edition Jonathan","rss_url": "https://....substack.com/feed" }
]
```

`name` → the Notion `Source` select. `rss_url` → the feed. Adding a newsletter later = add an
entry and push. RSS URLs and names are not secret, so they live in the repo (version-controlled,
reviewable). Secrets stay in env.

### 2. `config.py`

- Load `substacks.json` into `config.SUBSTACKS` (list of `{name, rss_url}` dicts).
- Keep env vars: `NOTION_SECRET`, `DATABASE_ID`, `SUBSTACK_COOKIE`, `TRANSCRIPT_API_KEY`
  (all shared across feeds).
- Remove `SUBSTACK_NAME` and `YOUTUBE_CHANNEL_ID`.
- **Back-compat fallback:** if `substacks.json` is absent but the legacy `SUBSTACK_RSS_URL` env is
  set, build a 1-item `SUBSTACKS` list from `SUBSTACK_RSS_URL` + `SUBSTACK_NAME`. This keeps any
  not-yet-migrated deploy working.
- `validate()` requires `NOTION_SECRET`, `DATABASE_ID`, and a non-empty `SUBSTACKS`.

### 3. Function signature changes (Approach A — explicit params)

| Function | Before | After |
|---|---|---|
| `substack.fetch_rss_entries` | reads `config.SUBSTACK_RSS_URL` | `fetch_rss_entries(rss_url)` |
| `substack.fetch_full_archive` | reads `config.SUBSTACK_RSS_URL` | `fetch_full_archive(rss_url)` |
| `notion_client.create_notion_page` | reads `config.SUBSTACK_NAME` for Source | reads `data["source"]` |
| `youtube.find_matching_video_rss` | — | **deleted** |

### 4. `daily_sync.py` and `backfill.py`

Wrap the existing per-post body in a per-feed loop:

```python
for feed in config.SUBSTACKS:
    try:
        # existing logic, using feed["rss_url"] and passing feed["name"] as data["source"]
    except Exception as e:
        log.error(f"Feed failed: {feed['name']}: {e}")
        continue
```

- **Per-feed error isolation:** one feed erroring logs and continues; it never aborts the others.
  (This is also a defense against the silent-failure class of bug — a single bad feed can't take
  down the whole run.)
- Drop the `else: find_matching_video_rss(...)` branch; keep the `if embedded_yt_id:` branch.
- `existing_titles` (the Notion dedupe set) is fetched **once** before the loop and shared across
  feeds — the Notion DB is shared, so this is correct and avoids N redundant full-DB queries.
- End-of-run summary: per-feed counts + a grand total.
- `daily_sync` calls `fix_covers` once after all feeds (unchanged).

### 5. Operations after the refactor

- **One Railway service** with env: `NOTION_SECRET`, `DATABASE_ID`, `SUBSTACK_COOKIE` (refreshed),
  `TRANSCRIPT_API_KEY`. Cron unchanged (`0 15,3 * * *`).
- **Backfill = one run:** temporarily set the service's start command to `python main.py backfill`
  → it loops every feed and fills the March-19→today gap for all of them → revert to
  `python main.py sync`.
- Delete the other 4 services once the single service is verified.

## Testing

- Unit: `config` builds `SUBSTACKS` from a sample `substacks.json`; back-compat fallback from
  `SUBSTACK_RSS_URL`; `validate()` rejects empty feed list.
- Unit: `create_notion_page` uses `data["source"]` for the Source property.
- Smoke: run `sync` locally against the real `substacks.json` with credentials; confirm each feed
  is fetched, dedupe works, and a forced exception in one feed doesn't stop the others.
