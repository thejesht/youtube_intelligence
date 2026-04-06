"""
Channel Monitor - Fetch videos from YouTube channels
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


@dataclass
class Video:
    """Represents a YouTube video"""
    video_id: str
    title: str
    description: str
    published_at: datetime
    channel_id: str
    channel_title: str
    thumbnail_url: str

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


@dataclass
class Channel:
    """Represents a YouTube channel"""
    channel_id: str
    title: str
    description: str
    subscriber_count: Optional[int]
    video_count: Optional[int]


class ChannelMonitor:
    """Monitor YouTube channels for new videos"""

    def __init__(self, api_key: str):
        """
        Initialize the channel monitor.

        Args:
            api_key: YouTube Data API v3 key
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def search_channel(self, query: str) -> list[Channel]:
        """
        Search for YouTube channels by name.

        Args:
            query: Channel name to search for

        Returns:
            List of matching channels
        """
        try:
            request = self.youtube.search().list(
                part='snippet',
                q=query,
                type='channel',
                maxResults=5
            )
            response = request.execute()

            channels = []
            for item in response.get('items', []):
                channel = Channel(
                    channel_id=item['id']['channelId'],
                    title=item['snippet']['title'],
                    description=item['snippet']['description'],
                    subscriber_count=None,
                    video_count=None
                )
                channels.append(channel)

            return channels

        except HttpError as e:
            print(f"Error searching for channel: {e}")
            return []

    def get_channel_by_id(self, channel_id: str) -> Optional[Channel]:
        """
        Get channel details by ID.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Channel object or None if not found
        """
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            )
            response = request.execute()

            if not response.get('items'):
                return None

            item = response['items'][0]
            stats = item.get('statistics', {})

            return Channel(
                channel_id=channel_id,
                title=item['snippet']['title'],
                description=item['snippet']['description'],
                subscriber_count=int(stats.get('subscriberCount', 0)) if stats.get('subscriberCount') else None,
                video_count=int(stats.get('videoCount', 0)) if stats.get('videoCount') else None
            )

        except HttpError as e:
            print(f"Error getting channel: {e}")
            return None

    def get_recent_videos(
        self,
        channel_id: str,
        days: int = 20,
        max_results: int = 50
    ) -> list[Video]:
        """
        Get videos published in the last N days from a channel.

        Args:
            channel_id: YouTube channel ID
            days: Number of days to look back (default: 20)
            max_results: Maximum number of videos to return (default: 50)

        Returns:
            List of Video objects
        """
        # Calculate the date threshold
        published_after = datetime.utcnow() - timedelta(days=days)
        published_after_str = published_after.isoformat() + 'Z'

        try:
            # Search for videos from this channel
            request = self.youtube.search().list(
                part='snippet',
                channelId=channel_id,
                publishedAfter=published_after_str,
                type='video',
                order='date',
                maxResults=max_results
            )
            response = request.execute()

            videos = []
            for item in response.get('items', []):
                snippet = item['snippet']

                # Parse the published date
                published_at = datetime.fromisoformat(
                    snippet['publishedAt'].replace('Z', '+00:00')
                )

                video = Video(
                    video_id=item['id']['videoId'],
                    title=snippet['title'],
                    description=snippet['description'],
                    published_at=published_at,
                    channel_id=snippet['channelId'],
                    channel_title=snippet['channelTitle'],
                    thumbnail_url=snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['default']['url']
                )
                videos.append(video)

            return videos

        except HttpError as e:
            print(f"Error getting videos: {e}")
            return []

    def get_channel_by_handle(self, handle: str) -> Optional[Channel]:
        """
        Get channel by YouTube handle (e.g., @TwoMinutePapers).

        Args:
            handle: YouTube handle (with or without @)

        Returns:
            Channel object or None if not found
        """
        # Remove @ if present
        handle = handle.lstrip('@')

        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                forHandle=handle
            )
            response = request.execute()

            if not response.get('items'):
                return None

            item = response['items'][0]
            stats = item.get('statistics', {})

            return Channel(
                channel_id=item['id'],
                title=item['snippet']['title'],
                description=item['snippet']['description'],
                subscriber_count=int(stats.get('subscriberCount', 0)) if stats.get('subscriberCount') else None,
                video_count=int(stats.get('videoCount', 0)) if stats.get('videoCount') else None
            )

        except HttpError as e:
            # Handle might not exist or API doesn't support it
            print(f"Error getting channel by handle: {e}")
            return None


def get_channel_id_from_url(url: str) -> Optional[str]:
    """
    Extract channel ID from various YouTube URL formats.

    Supports:
    - https://www.youtube.com/channel/UC...
    - https://www.youtube.com/@handle
    - https://www.youtube.com/c/ChannelName

    Args:
        url: YouTube channel URL

    Returns:
        Channel ID or handle string
    """
    import re

    patterns = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'youtube\.com/@([a-zA-Z0-9_-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_-]+)',
        r'youtube\.com/user/([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None
