# YouTube Intelligence

An automated pipeline that monitors YouTube channels, fetches transcripts, and builds a compounding LLM wiki for learning — inspired by [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Zero YouTube API keys required.

## Architecture

```mermaid
graph TB
    subgraph "GitHub Actions - Daily 3 AM UTC"
        A["Stage 1: RSS Check"] --> B["Stage 2: Transcript Fetch"]
    end

    subgraph "Local - Claude Code Session"
        C["Wiki Update<br/>Ollama / DeepSeek"]
    end

    subgraph YouTube
        Y1["Channel RSS Feeds"]
        Y2["Captions API"]
    end

    subgraph Storage
        S1[("Supabase<br/>yt_channels<br/>yt_videos<br/>yt_transcripts")]
    end

    subgraph "Wiki (markdown)"
        W1["concepts/"]
        W2["people/"]
        W3["sources/"]
        W4["themes/"]
    end

    Y1 -->|Long-form only| A
    Y2 -->|Transcripts| B
    A -->|Store| S1
    B -->|Store| S1
    S1 -->|Raw transcripts| C
    C -->|Extract knowledge| W1
    C -->|Extract knowledge| W2
    C -->|Extract knowledge| W3
```

## Pipeline Flow

```mermaid
sequenceDiagram
    participant GH as GitHub Actions
    participant YT as YouTube RSS
    participant API as youtube-transcript-api
    participant SB as Supabase
    participant CC as Claude Code + Ollama
    participant WK as wiki/

    Note over GH: Daily at 3:00 AM UTC

    GH->>SB: Get followed channels
    SB-->>GH: Channel list + RSS URLs

    loop Each Channel
        GH->>YT: Fetch RSS feed
        YT-->>GH: Latest 15 videos
        GH->>GH: Filter out Shorts (/shorts/ URL)
        GH->>SB: Insert new long-form videos
    end

    GH->>SB: Get videos pending transcript

    loop Each Pending Video
        GH->>API: Fetch transcript via video_id
        API-->>GH: Full transcript text
        GH->>SB: Store transcript + word count
    end

    Note over CC: User runs "update the wiki" in Claude Code

    CC->>SB: Get videos with transcripts not yet wiki-processed

    loop Each Video
        CC->>SB: Get raw transcript
        CC->>CC: Ollama extracts concepts, people, takeaways
        CC->>WK: Create/update concept pages
        CC->>WK: Create/update people pages
        CC->>WK: Create source page
        CC->>SB: Mark wiki_processed = true
    end

    CC->>WK: Rebuild index.md
```

## Data Model

```mermaid
erDiagram
    yt_channels {
        text channel_id PK
        text handle
        text name
        text rss_url
        timestamptz added_at
    }

    yt_videos {
        text video_id PK
        text channel_id FK
        text title
        timestamptz published_at
        text video_url
        boolean transcript_fetched
        boolean wiki_processed
        timestamptz discovered_at
    }

    yt_transcripts {
        text video_id PK
        text transcript
        text language
        integer word_count
        timestamptz fetched_at
    }

    yt_channels ||--o{ yt_videos : has
    yt_videos ||--o| yt_transcripts : has
```

## How Each Stage Works

### Stage 1: RSS Check (automated)
- Reads channels from `yt_channels` in Supabase
- Fetches each channel's RSS feed — no API key needed
- **Filters out YouTube Shorts** by checking for `/shorts/` in the RSS link URL
- Inserts only new long-form videos into `yt_videos`

### Stage 2: Transcript Fetch (automated)
- Picks up videos where `transcript_fetched = false`
- Uses `youtube-transcript-api` — no API key needed
- Prefers manual English captions, falls back to auto-generated
- Rate-limited with 2-3 second delays between requests
- Stores full transcript + word count in `yt_transcripts`

### Wiki Update (manual, Claude Code session)
- Reads raw transcripts directly from Supabase
- Uses local Ollama/DeepSeek to extract concepts, people, and takeaways
- Creates/updates interlinked markdown pages in `wiki/`
- Each new video makes the entire wiki richer — concepts get more sources, people get more appearances
- Updates `wiki/index.md` and `wiki/log.md`

## Project Structure

```
youtube_intelligence/
├── .github/workflows/
│   └── daily_pipeline.yml      # GitHub Actions daily at 3 AM UTC
├── pipeline/
│   ├── config.py               # Supabase config + pipeline settings
│   ├── rss_checker.py          # RSS parsing + Shorts filter
│   ├── transcript.py           # Transcript fetching (no API key)
│   ├── storage.py              # Supabase CRUD (singleton client)
│   ├── run.py                  # Orchestrator (2 stages: rss, transcripts)
│   ├── wiki_update.py          # Transcript → wiki knowledge extraction
│   └── requirements.txt        # 3 dependencies
├── wiki/
│   ├── index.md                # Catalog of all wiki pages
│   ├── log.md                  # Chronological ingest log
│   ├── contradictions.md       # Where experts disagree
│   ├── concepts/               # Concept pages (cross-referenced)
│   ├── people/                 # Entity pages for experts/guests
│   ├── sources/                # Per-video knowledge pages
│   └── themes/                 # Cross-cutting synthesis
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r pipeline/requirements.txt
```

### 2. Set environment variables
```bash
cp .env.example .env
# Add your SUPABASE_URL and SUPABASE_SERVICE_KEY
```

### 3. Run the pipeline
```bash
python -m pipeline.run                    # both stages
python -m pipeline.run --stage rss        # RSS check only
python -m pipeline.run --stage transcripts # transcripts only
```

### 4. Update the wiki (locally, needs Ollama)
```bash
python -m pipeline.wiki_update
```

## Adding New Channels

```sql
INSERT INTO yt_channels (channel_id, handle, name, rss_url)
VALUES (
    'UC...',
    '@channelhandle',
    'Channel Name',
    'https://www.youtube.com/feeds/videos.xml?channel_id=UC...'
);
```

To find a channel ID from a handle:
```bash
yt-dlp --dump-json --playlist-items 1 --flat-playlist \
    "https://www.youtube.com/@handle/videos" \
    | python -c "import json,sys; d=json.loads(sys.stdin.readline()); print(d['playlist_channel_id'])"
```

## GitHub Actions Setup

Add these secrets to your repo (Settings > Secrets > Actions):

| Secret | Value |
|--------|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Your Supabase service role key |

The workflow runs daily at 3:00 AM UTC and can be triggered manually from the Actions tab.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | — | Supabase project URL (required) |
| `SUPABASE_SERVICE_KEY` | — | Supabase service role key (required) |
| `MAX_VIDEOS_PER_RUN` | `20` | Transcript fetch cap per run |
| `TRANSCRIPT_DELAY_SECONDS` | `2.0` | Rate limit between YouTube requests |

## Tech Stack

| Component | Technology | Cost |
|-----------|------------|------|
| Video discovery | YouTube RSS feeds | Free |
| Shorts filtering | RSS link URL pattern | Free |
| Transcripts | `youtube-transcript-api` | Free |
| Database | Supabase (Postgres) | Free tier |
| Knowledge extraction | Ollama + DeepSeek (local) | Free |
| Knowledge base | Markdown wiki (Karpathy pattern) | Free |
| Scheduling | GitHub Actions | Free tier |

**Total cost: $0/month**
