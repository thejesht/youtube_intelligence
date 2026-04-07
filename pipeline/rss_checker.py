"""Check YouTube RSS feeds for new videos."""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from dataclasses import dataclass


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
YT_NS = {"yt": "http://www.youtube.com/xml/schemas/2015"}


@dataclass
class RSSVideo:
    video_id: str
    title: str
    published_at: str  # ISO format
    channel_id: str
    video_url: str


def fetch_rss_videos(rss_url: str, channel_id: str, long_form_only: bool = True) -> list[RSSVideo]:
    """Fetch latest videos from a channel's RSS feed.

    Args:
        long_form_only: If True, skip YouTube Shorts (detected via /shorts/ URL in RSS).
    """
    resp = requests.get(rss_url, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    videos = []

    for entry in root.findall("atom:entry", ATOM_NS):
        # Check the link URL to detect shorts vs long-form
        link_url = entry.find("atom:link", ATOM_NS).get("href", "")
        if long_form_only and "/shorts/" in link_url:
            continue

        vid_id = entry.find("yt:videoId", YT_NS).text
        title = entry.find("atom:title", ATOM_NS).text
        published = entry.find("atom:published", ATOM_NS).text

        videos.append(RSSVideo(
            video_id=vid_id,
            title=title,
            published_at=published,
            channel_id=channel_id,
            video_url=f"https://www.youtube.com/watch?v={vid_id}",
        ))

    return videos


def get_new_videos(rss_url: str, channel_id: str, known_video_ids: set[str]) -> list[RSSVideo]:
    """Return only videos not already in the known set."""
    all_videos = fetch_rss_videos(rss_url, channel_id)
    return [v for v in all_videos if v.video_id not in known_video_ids]
