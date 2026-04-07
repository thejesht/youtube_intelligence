"""Fetch transcripts using youtube-transcript-api (no API key needed)."""

import time
import random
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable


@dataclass
class TranscriptResult:
    video_id: str
    text: str
    language: str
    word_count: int


def fetch_transcript(video_id: str, delay: float = 2.0) -> TranscriptResult | None:
    """
    Fetch transcript for a single video.
    Returns None if transcript is unavailable.
    """
    if delay > 0:
        time.sleep(delay + random.uniform(0, 1))

    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)

        # Prefer manual English, then auto-generated English, then anything
        selected = None
        for t in transcript_list:
            if not t.is_generated and t.language_code.startswith("en"):
                selected = t
                break
        if not selected:
            for t in transcript_list:
                if t.is_generated and t.language_code.startswith("en"):
                    selected = t
                    break
        if not selected and transcript_list:
            selected = transcript_list[0]

        if selected:
            fetched = selected.fetch()
            text = " ".join(snippet.text for snippet in fetched)
            return TranscriptResult(
                video_id=video_id,
                text=text,
                language=selected.language_code,
                word_count=len(text.split()),
            )

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        print(f"  Transcript unavailable for {video_id}: {e}")
    except Exception as e:
        print(f"  Error fetching transcript for {video_id}: {e}")

    return None
