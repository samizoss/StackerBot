# Substack-to-Notion Scraper

Automatically syncs a Substack newsletter to a Notion database. Finds matching YouTube videos and fetches transcripts. Deploys to Railway with cron scheduling.

## What It Does

- Checks a Substack RSS feed on a schedule (twice daily)
- Scrapes full article content including paywalled posts (if you have a subscription)
- Converts HTML to rich Notion blocks (headings, lists, images, links, code, quotes)
- Optionally matches articles to a YouTube channel and fetches transcripts
- Creates fully formatted Notion pages with table of contents
- Backfills missing cover images automatically

## Quick Start (Railway)

### 1. Notion Setup

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and create a new integration
2. Copy the **Internal Integration Secret** (starts with `ntn_`)
3. Create a Notion database with these properties:

| Property | Type |
|----------|------|
| Name | Title |
| Date | Date |
| URL | URL |
| YouTube URL | URL |
| Type | Select |
| Content Status | Select |
| Source | Select |

4. Click **Share** on your database and add your integration

5. Copy the **Database ID** from the database URL:
   `https://notion.so/YOUR_WORKSPACE/DATABASE_ID_HERE?v=...`

### 2. Fork & Deploy

1. Fork this repo to your GitHub account
2. Go to [railway.app](https://railway.app) and create a new project from your fork
3. Add these environment variables in Railway's dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_SECRET` | Yes | Your Notion integration token |
| `DATABASE_ID` | Yes | Your Notion database ID |
| `SUBSTACK_RSS_URL` | Yes | RSS feed URL (e.g. `https://natesnewsletter.substack.com/feed`) |
| `SUBSTACK_NAME` | No | Label for the "Source" column in Notion (e.g. `Nate Jones`) |
| `SUBSTACK_COOKIE` | No | Your `substack.sid` cookie for paywalled content |
| `TRANSCRIPT_API_KEY` | No | [TranscriptAPI.com](https://transcriptapi.com) key for YouTube transcripts |
| `YOUTUBE_CHANNEL_ID` | No | YouTube channel ID for video matching |

4. Deploy. The cron job runs at 9 AM and 9 PM EST automatically.

### Finding Your Substack RSS URL

Every Substack has an RSS feed at: `https://YOUR-SUBSTACK.substack.com/feed`

### Finding Your Substack Cookie (for paywalled content)

1. Log into Substack in your browser
2. Open DevTools (F12) > Application > Cookies
3. Find `substack.sid` and copy the full value

### Finding a YouTube Channel ID

1. Go to the YouTube channel
2. View page source (Ctrl+U)
3. Search for `channel_id` — it starts with `UC`

## Local Development

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/substack-to-notion.git
cd substack-to-notion
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your values

# Run
python main.py sync           # Full sync (RSS + covers)
python main.py fix-covers     # Only backfill missing covers
python main.py repair-youtube # Fix pages missing YouTube links
```

## Multiple Substacks

To track multiple newsletters in one Notion database, create a separate Railway service for each Substack — all pointing to the same `DATABASE_ID`:

| Service | `SUBSTACK_RSS_URL` | `SUBSTACK_NAME` |
|---------|-------------------|-----------------|
| Service 1 | `https://natesnewsletter.substack.com/feed` | `Nate Jones` |
| Service 2 | `https://other.substack.com/feed` | `Other Author` |
| Service 3 | `https://another.substack.com/feed` | `Another Author` |

Each service uses the same repo, same `NOTION_SECRET`, and same `DATABASE_ID`. The `Source` column in Notion lets you filter by newsletter.

In Railway: click **New Service** > **GitHub Repo** > select this same repo > set different env vars.

## How It Works

1. **Fetch RSS** — Reads the Substack feed for all published posts
2. **Deduplicate** — Checks every post title against your Notion database (fuzzy matching at 85% similarity)
3. **Scrape Content** — Downloads the full article HTML and converts it to Notion blocks with formatting preserved
4. **YouTube Match** — Looks for embedded YouTube videos in the article, or matches the title against a YouTube channel's RSS feed
5. **Transcript** — If a YouTube video is found, fetches the transcript via TranscriptAPI
6. **Create Page** — Builds a formatted Notion page with table of contents, article content, YouTube embed, and transcript
7. **Cover Image** — Grabs the article's Open Graph image and sets it as the Notion page cover
