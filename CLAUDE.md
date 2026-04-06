# youtube_intelligence

A unified YouTube intelligence toolkit — monitors channels, fetches transcripts, generates embeddings, and extracts structured insights using LLMs.

## What this project does
- Monitors YouTube channels for new videos
- Fetches and stores transcripts
- Generates embeddings (Chroma vector DB) for semantic search
- Scores videos by relevance to configured user interests
- Extracts LLM-generated insights from transcripts for any domain

## Structure
- `src/` — core modules: channel_monitor, transcript_fetcher, embedding_generator, relevance_scorer, database
- `scripts/` — runnable entry points: setup, fetch_channel, process_transcripts, test_search
- `transcript_extraction/` — LLM insight generation from transcripts; currently contains one worked example (AEO strategies for UK OTAs), evolving into a reusable pipeline
- `data/` — local DBs and embeddings (not committed to git)
- `config/` — user interest profiles

## Running
```bash
python scripts/setup.py                  # first-time setup
python scripts/fetch_channel.py          # fetch new videos
python scripts/process_transcripts.py   # generate embeddings
python scripts/test_search.py           # test relevance search
```

## Key files
- `requirements.txt` — dependencies
- `.env` — YouTube API key and user config (never commit)
- `IMPLEMENTATION_PLAN.md` — roadmap for upcoming features

## Roadmap
Connect `transcript_extraction` insight pipeline with the recommendation engine for full end-to-end: discover → fetch → embed → score → extract insights.
