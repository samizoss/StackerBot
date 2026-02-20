# StackerBot

Automatically syncs your Substack newsletters to Notion. Pulls full article content (including paid posts), matches YouTube videos, fetches transcripts, and builds beautifully formatted Notion pages — all on autopilot.

## What It Does

- Checks a Substack RSS feed on a schedule (twice daily)
- Scrapes full article content including paywalled posts (if you have a subscription)
- Converts HTML to rich Notion blocks (headings, lists, images, links, code, quotes)
- Optionally matches articles to a YouTube channel and fetches transcripts
- Creates fully formatted Notion pages with table of contents
- Backfills missing cover images automatically
- Can import a Substack's full archive (not just the 20 most recent)

## Setup Guide

### Step 1: Fork This Repo

1. Click the **Fork** button at the top right of this page
2. This creates your own copy at `github.com/YOUR_USERNAME/StackerBot`

### Step 2: Create a Notion Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New integration**
3. Name it whatever you want (e.g. "StackerBot")
4. Copy the **Internal Integration Secret** — it starts with `ntn_`

### Step 3: Create Your Notion Database

Create a new **full-page database** in Notion with these exact property names and types:

| Property | Type |
|----------|------|
| Name | Title |
| Date | Date |
| URL | URL |
| YouTube URL | URL |
| Type | Select |
| Content Status | Select |
| Source | Select |

Then **share the database with your integration**:
1. Open your database page
2. Click **Share** (top right)
3. Search for your integration name and add it

Finally, **copy your Database ID** from the URL bar:
```
https://notion.so/YOUR_WORKSPACE/DATABASE_ID_HERE?v=...
                                  ^^^^^^^^^^^^^^^^
                                  copy this part
```

### Step 4: Deploy on Railway

1. Go to [railway.com](https://railway.com) and sign up (free tier works)
2. Click **New Project** > **Deploy from GitHub repo**
3. Select your forked `StackerBot` repo
4. Once the service is created, go to the **Variables** tab
5. Add these environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_SECRET` | Yes | Your Notion integration token (starts with `ntn_`) |
| `DATABASE_ID` | Yes | Your Notion database ID from Step 3 |
| `SUBSTACK_RSS_URL` | Yes | The RSS feed URL (see below) |
| `SUBSTACK_NAME` | No | Label for the "Source" column (e.g. `Nate Jones`) |
| `SUBSTACK_COOKIE` | No | Your `substack.sid` cookie — needed for paid/paywalled content |
| `TRANSCRIPT_API_KEY` | No | [TranscriptAPI.com](https://transcriptapi.com) key for YouTube transcripts |
| `YOUTUBE_CHANNEL_ID` | No | YouTube channel ID for video matching |

6. Railway will auto-deploy. The cron job runs at **9 AM and 9 PM EST** automatically.

That's it! New Substack posts will appear in your Notion database twice a day.

### Finding Your Substack RSS URL

Every Substack has an RSS feed at:
```
https://YOUR-SUBSTACK.substack.com/feed
```

For example: `https://natesnewsletter.substack.com/feed`

If the Substack uses a custom domain (like `www.lennysnewsletter.com`), the feed is at:
```
https://www.lennysnewsletter.com/feed
```

### Finding Your Substack Cookie (for paywalled content)

You only need this if you're a **paid subscriber** and want to pull paywalled articles:

1. Log into Substack in your browser
2. Open DevTools (F12) > **Application** tab > **Cookies** > substack.com
3. Find the cookie named `substack.sid`
4. Copy the **full value** (it's long — starts with `s%3A`)

Set the variable as: `substack.sid=THE_VALUE_YOU_COPIED`

### Finding a YouTube Channel ID

1. Go to the YouTube channel page
2. View page source (Ctrl+U / Cmd+U)
3. Search for `channel_id` — it starts with `UC`

## Multiple Substacks

To track multiple newsletters in one Notion database, create a **separate Railway service** for each Substack — all pointing to the same `DATABASE_ID`.

In your Railway project:
1. Click **New Service** > **GitHub Repo** > select your StackerBot fork
2. Add the same `NOTION_SECRET` and `DATABASE_ID`
3. Set a different `SUBSTACK_RSS_URL` and `SUBSTACK_NAME`
4. Repeat for each newsletter

Example setup:

| Service | `SUBSTACK_RSS_URL` | `SUBSTACK_NAME` |
|---------|-------------------|-----------------|
| Service 1 | `https://natesnewsletter.substack.com/feed` | `Nate Jones` |
| Service 2 | `https://other.substack.com/feed` | `Other Author` |
| Service 3 | `https://another.substack.com/feed` | `Another Author` |

The `Source` column in Notion lets you filter by newsletter.

## Commands

```bash
python main.py sync           # Daily sync — fetch new posts + fix covers
python main.py backfill       # Import FULL archive (all posts, not just recent 20)
python main.py fix-covers     # Backfill missing cover images only
python main.py repair-youtube # Fix pages missing YouTube links
```

**Backfill tip:** The daily sync only catches the 20 most recent posts (RSS limit). To import a Substack's full history, run `backfill` once. It uses Substack's archive API and requires the `SUBSTACK_COOKIE` for full access.

## Local Development

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/StackerBot.git
cd StackerBot
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your values

# Run
python main.py sync
```

## How It Works

1. **Fetch RSS** — Reads the Substack feed for recent posts
2. **Deduplicate** — Checks every post title against your Notion database (fuzzy matching at 92% similarity)
3. **Scrape Content** — Downloads the full article HTML and converts it to Notion blocks with formatting preserved
4. **YouTube Match** — Looks for embedded YouTube videos in the article, or matches the title against a YouTube channel's RSS feed
5. **Transcript** — If a YouTube video is found, fetches the transcript via TranscriptAPI
6. **Create Page** — Builds a formatted Notion page with table of contents, article content, YouTube embed, and transcript
7. **Cover Image** — Grabs the article's Open Graph image and sets it as the Notion page cover
