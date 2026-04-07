# youtube_intelligence

Automated YouTube learning pipeline with a compounding LLM wiki (inspired by Karpathy's LLM Wiki pattern).

## How it works

**Automated (GitHub Actions daily):**
1. **RSS check** — discovers new long-form videos, skips Shorts (no API key)
2. **Transcript fetch** — pulls transcripts via `youtube-transcript-api` (no API key)
3. Stores everything in Supabase (`yt_channels`, `yt_videos`, `yt_transcripts`)

**Manual (Claude Code session):**
4. **Wiki update** — reads raw transcripts, extracts concepts/people/knowledge via Ollama, builds interlinked markdown wiki

## Structure
- `pipeline/` — automated ingestion
  - `run.py` — orchestrator (2 stages: rss, transcripts)
  - `rss_checker.py` — YouTube RSS feed parsing, filters out Shorts
  - `transcript.py` — transcript fetching
  - `storage.py` — Supabase operations (singleton client)
  - `config.py` — configuration
  - `wiki_update.py` — transcript → wiki knowledge extraction
- `wiki/` — LLM-maintained knowledge base (Karpathy pattern)
  - `index.md` — catalog of all pages
  - `log.md` — chronological ingest log
  - `concepts/` — concept pages, cross-referenced across videos
  - `people/` — entity pages for recurring experts/guests
  - `sources/` — per-video knowledge pages
  - `themes/` — cross-cutting synthesis

## Running
```bash
# Automated pipeline (GitHub Actions runs this daily)
python -m pipeline.run

# Wiki update (run locally in Claude Code session)
python -m pipeline.wiki_update
```

## Adding channels
Insert into Supabase `yt_channels` table with channel_id, handle, name, and rss_url.
