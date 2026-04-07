"""
YouTube Learning Pipeline — automated ingestion.

GitHub Actions runs this daily:
  1. Check RSS feeds for new long-form videos
  2. Fetch transcripts and store in Supabase

Usage:
  python -m pipeline.run              # run both stages
  python -m pipeline.run --stage rss  # run one stage
"""

import argparse
from datetime import datetime

from pipeline import storage
from pipeline.rss_checker import get_new_videos
from pipeline.transcript import fetch_transcript
from pipeline.config import MAX_VIDEOS_PER_RUN, TRANSCRIPT_DELAY_SECONDS


def stage_rss():
    """Check RSS feeds and discover new long-form videos."""
    channels = storage.get_channels()
    print(f"\n[RSS] Checking {len(channels)} channels...")

    total_new = 0
    for ch in channels:
        known = storage.get_known_video_ids(ch["channel_id"])
        new_videos = get_new_videos(ch["rss_url"], ch["channel_id"], known)

        for v in new_videos:
            storage.insert_video(v.video_id, v.channel_id, v.title, v.published_at, v.video_url)
            print(f"  + {ch['name']}: {v.title}")

        total_new += len(new_videos)
        print(f"  {ch['name']}: {len(new_videos)} new / {len(known)} existing")

    print(f"[RSS] Done. {total_new} new videos discovered.\n")
    return total_new


def stage_transcripts():
    """Fetch transcripts for videos that don't have one yet."""
    pending = storage.get_videos_pending_transcript()
    batch = pending[:MAX_VIDEOS_PER_RUN]
    print(f"[TRANSCRIPTS] {len(pending)} pending, processing {len(batch)}...")

    fetched = 0
    for video in batch:
        vid_id = video["video_id"]
        print(f"  Fetching: {video['title'][:60]}...")

        result = fetch_transcript(vid_id, delay=TRANSCRIPT_DELAY_SECONDS)
        if result:
            storage.save_transcript(vid_id, result.text, result.language, result.word_count)
            print(f"    OK ({result.word_count} words)")
            fetched += 1
        else:
            storage.save_transcript(vid_id, "", "en", 0)
            print(f"    SKIPPED (no transcript available)")

    print(f"[TRANSCRIPTS] Done. {fetched}/{len(batch)} fetched.\n")
    return fetched


STAGES = {"rss": stage_rss, "transcripts": stage_transcripts}


def main():
    parser = argparse.ArgumentParser(description="YouTube Learning Pipeline")
    parser.add_argument("--stage", choices=list(STAGES.keys()), help="Run a single stage")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"YouTube Learning Pipeline - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    if args.stage:
        STAGES[args.stage]()
    else:
        stage_rss()
        stage_transcripts()

    print("Pipeline complete.")


if __name__ == "__main__":
    main()
