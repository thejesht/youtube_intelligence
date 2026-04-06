# video_recommendations

YouTube channel monitoring and semantic video recommendation engine. Fetches transcripts, generates embeddings, and surfaces relevant videos based on user interests.

## What this project does
- Monitors a set of YouTube channels for new videos
- Fetches and stores transcripts
- Generates embeddings (Chroma vector DB) for semantic search
- Scores videos by relevance to configured user interests

## Structure
- `src/` — core modules: channel_monitor, transcript_fetcher, embedding_generator, relevance_scorer, database
- `scripts/` — runnable entry points: setup, fetch_channel, process_transcripts, test_search
- `data/` — local DBs and embeddings (not committed to git)
- `config/` — user interest profiles

## Running
```bash
python scripts/setup.py           # first-time setup
python scripts/fetch_channel.py   # fetch new videos
python scripts/process_transcripts.py  # generate embeddings
python scripts/test_search.py     # test relevance search
```

## Key files
- `requirements.txt` — dependencies
- `.env` — YouTube API key and user config (never commit)
- `IMPLEMENTATION_PLAN.md` — roadmap for upcoming features
