# YouTube Video Recommendation System - Implementation Plan

## Overview
A personalized system that monitors YouTube channels, analyzes video content using local AI models, and sends relevant recommendations via Telegram.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     YouTube Recommendation System                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Channel    │───▶│  Transcript  │───▶│  Embedding   │      │
│  │   Monitor    │    │   Fetcher    │    │  Generator   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────┐       │
│  │                    SQLite + ChromaDB                 │       │
│  │            (Metadata + Vector Embeddings)            │       │
│  └─────────────────────────────────────────────────────┘       │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │    User      │───▶│  Relevance   │───▶│  Telegram    │      │
│  │   Profile    │    │   Scorer     │    │   Notifier   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Size/Notes |
|-----------|------------|------------|
| Language | Python 3.11+ | - |
| Transcripts | MCP Docker (YouTube Transcripts) | - |
| Embeddings | bge-large-en-v1.5 (sentence-transformers) | ~1.3GB |
| Analysis | qwen2.5:32b (Ollama) | ~19GB |
| Vector Store | ChromaDB | Local, file-based |
| Metadata DB | SQLite | Local |
| Notifications | Telegram Bot API | Free |
| Scheduler | Windows Task Scheduler | Daily |

---

## Project Structure

```
youtube_video_recommedations/
├── config/
│   ├── channels.yaml          # List of YouTube channels to monitor
│   ├── user_profile.yaml      # User interests and preferences
│   └── settings.yaml          # API keys, Telegram config, etc.
├── src/
│   ├── __init__.py
│   ├── channel_monitor.py     # Fetch new videos from channels
│   ├── transcript_fetcher.py  # Get transcripts via MCP/API
│   ├── embedding_generator.py # Generate embeddings using local model
│   ├── relevance_scorer.py    # Score videos against user profile
│   ├── notifier.py            # Send Telegram notifications
│   └── database.py            # SQLite + ChromaDB operations
├── data/
│   ├── youtube.db             # SQLite database
│   └── chroma/                # ChromaDB vector store
├── scripts/
│   ├── setup.py               # Initial setup script
│   ├── add_channel.py         # Add new channel to monitor
│   └── daily_job.py           # Main entry point for scheduler
├── requirements.txt
├── .env.example
└── README.md
```

---

## Implementation Steps

### Step 1: Channel Video Discovery & Transcript Fetching ⬅️ CURRENT
**Goal**: Given a channel name, fetch videos from last 20 days and get transcripts

- [ ] Set up project structure
- [ ] Implement channel search (name → channel ID)
- [ ] Fetch recent videos (last 20 days)
- [ ] Integrate transcript fetching (MCP Docker or fallback)
- [ ] Store raw data in SQLite

**Deliverable**: CLI command that takes channel name and outputs video titles + transcripts

---

### Step 2: Embedding Generation & Storage
**Goal**: Generate embeddings for transcripts and store in vector DB

- [ ] Set up sentence-transformers with bge-large-en-v1.5
- [ ] Implement transcript chunking (for long videos)
- [ ] Generate and store embeddings in ChromaDB
- [ ] Link embeddings to video metadata in SQLite

**Deliverable**: Transcripts converted to searchable embeddings

---

### Step 3: User Profile & Interest Matching
**Goal**: Define user interests and match against video embeddings

- [ ] Create user profile schema (topics, keywords, weights)
- [ ] Generate embeddings for user interests
- [ ] Implement similarity scoring (cosine similarity)
- [ ] Rank videos by relevance

**Deliverable**: Ranked list of videos based on user interests

---

### Step 4: Telegram Notifications
**Goal**: Send daily digest of relevant videos via Telegram

- [ ] Create Telegram bot
- [ ] Implement message formatting (title, score, summary, link)
- [ ] Send top N recommendations daily

**Deliverable**: Telegram messages with video recommendations

---

### Step 5: Summarization with Ollama (Optional Enhancement)
**Goal**: Use qwen2.5:32b to generate concise summaries

- [ ] Set up Ollama with qwen2.5:32b
- [ ] Implement transcript summarization
- [ ] Include summaries in notifications

**Deliverable**: AI-generated summaries in recommendations

---

### Step 6: Scheduling & Automation
**Goal**: Run the system automatically every day

- [ ] Create main orchestration script
- [ ] Set up Windows Task Scheduler
- [ ] Add logging and error handling
- [ ] Email fallback for Telegram failures

**Deliverable**: Fully automated daily recommendation system

---

## Configuration Files

### channels.yaml (example)
```yaml
channels:
  - name: "Two Minute Papers"
    channel_id: "UCbfYPyITQ-7l4upoX8nvctg"
  - name: "Yannic Kilcher"
    channel_id: "UCZHmQk67mSJgfCCTn7xBfew"
  - name: "AI Explained"
    channel_id: "UCNJ1Ymd5yFuUPtn21xtRbbw"
```

### user_profile.yaml (example)
```yaml
interests:
  high_priority:
    - "large language models"
    - "transformer architecture"
    - "AI agents"
    - "RAG systems"
  medium_priority:
    - "computer vision"
    - "reinforcement learning"
    - "diffusion models"
  exclude:
    - "crypto"
    - "NFT"

min_relevance_score: 0.7
max_videos_per_day: 5
```

### settings.yaml (example)
```yaml
youtube:
  api_key: "${YOUTUBE_API_KEY}"

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"

ollama:
  base_url: "http://localhost:11434"
  model: "qwen2.5:32b"

storage:
  db_path: "./data/youtube.db"
  chroma_path: "./data/chroma"
```

---

## Next Steps

Proceeding with **Step 1**: Channel Video Discovery & Transcript Fetching
