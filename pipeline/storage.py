"""Supabase storage for the YouTube learning pipeline."""

from supabase import create_client
from pipeline.config import SUPABASE_URL, SUPABASE_KEY

_client = None


def get_client():
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def get_channels() -> list[dict]:
    return get_client().table("yt_channels").select("*").execute().data


def get_known_video_ids(channel_id: str) -> set[str]:
    result = (
        get_client().table("yt_videos")
        .select("video_id")
        .eq("channel_id", channel_id)
        .execute()
    )
    return {row["video_id"] for row in result.data}


def insert_video(video_id: str, channel_id: str, title: str, published_at: str, video_url: str):
    get_client().table("yt_videos").upsert({
        "video_id": video_id,
        "channel_id": channel_id,
        "title": title,
        "published_at": published_at,
        "video_url": video_url,
    }).execute()


def get_videos_pending_transcript() -> list[dict]:
    return (
        get_client().table("yt_videos")
        .select("video_id, title")
        .eq("transcript_fetched", False)
        .execute()
    ).data


def save_transcript(video_id: str, text: str, language: str, word_count: int):
    client = get_client()
    client.table("yt_transcripts").upsert({
        "video_id": video_id,
        "transcript": text,
        "language": language,
        "word_count": word_count,
    }).execute()
    client.table("yt_videos").update({"transcript_fetched": True}).eq("video_id", video_id).execute()


def get_videos_pending_wiki() -> list[dict]:
    """Videos with transcripts that haven't been wiki-processed."""
    return (
        get_client().table("yt_videos")
        .select("video_id, title, video_url, published_at, channel_id")
        .eq("transcript_fetched", True)
        .eq("wiki_processed", False)
        .execute()
    ).data


def get_transcript_text(video_id: str) -> str | None:
    result = (
        get_client().table("yt_transcripts")
        .select("transcript")
        .eq("video_id", video_id)
        .single()
        .execute()
    )
    return result.data["transcript"] if result.data else None


def get_channel_name(channel_id: str) -> str:
    result = (
        get_client().table("yt_channels")
        .select("name")
        .eq("channel_id", channel_id)
        .single()
        .execute()
    )
    return result.data["name"] if result.data else "Unknown"


def mark_wiki_processed(video_id: str):
    get_client().table("yt_videos").update({"wiki_processed": True}).eq("video_id", video_id).execute()
