"""
Transcript Fetcher - Get transcripts from YouTube videos
Updated for youtube-transcript-api v1.2.x
"""

import subprocess
import json
import time
import random
from typing import Optional
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)


@dataclass
class Transcript:
    """Represents a video transcript"""
    video_id: str
    text: str
    language: str
    is_generated: bool  # True if auto-generated, False if manual


class TranscriptFetcher:
    """Fetch transcripts from YouTube videos"""

    def __init__(self, use_mcp: bool = False, mcp_tool_name: str = "youtube_transcripts", delay_seconds: float = 2.0, cookies_path: str = None):
        """
        Initialize the transcript fetcher.

        Args:
            use_mcp: Whether to try MCP Docker tool first
            mcp_tool_name: Name of the MCP tool for transcripts
            delay_seconds: Delay between requests to avoid rate limiting (default: 2.0)
            cookies_path: Path to cookies.txt file for bypassing rate limits
        """
        self.use_mcp = use_mcp
        self.mcp_tool_name = mcp_tool_name
        self.delay_seconds = delay_seconds
        self.cookies_path = cookies_path
        self._request_count = 0

        # Initialize API with cookies if provided
        if cookies_path:
            import requests
            from http.cookiejar import MozillaCookieJar

            session = requests.Session()
            try:
                cookie_jar = MozillaCookieJar(cookies_path)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                session.cookies = cookie_jar
                print(f"Loaded {len(cookie_jar)} cookies from {cookies_path}")
            except Exception as e:
                print(f"Warning: Could not load cookies: {e}")

            self.api = YouTubeTranscriptApi(http_client=session)
        else:
            self.api = YouTubeTranscriptApi()

    def get_transcript(
        self,
        video_id: str,
        languages: list[str] = ['en', 'en-US', 'en-GB']
    ) -> Optional[Transcript]:
        """
        Get transcript for a video.

        Tries MCP Docker first if enabled, falls back to youtube-transcript-api.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages in order

        Returns:
            Transcript object or None if unavailable
        """
        # Add delay between requests to avoid rate limiting
        if self._request_count > 0 and self.delay_seconds > 0:
            # Add small random jitter (0-1 second) to look more natural
            jitter = random.uniform(0, 1)
            time.sleep(self.delay_seconds + jitter)
        self._request_count += 1

        # Try MCP Docker if enabled
        if self.use_mcp:
            transcript = self._fetch_via_mcp(video_id)
            if transcript:
                return transcript

        # Fallback to youtube-transcript-api
        return self._fetch_via_api(video_id, languages)

    def _fetch_via_mcp(self, video_id: str) -> Optional[Transcript]:
        """
        Fetch transcript using MCP Docker tool.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript object or None if failed
        """
        try:
            # TODO: Adjust this command based on actual MCP tool invocation
            cmd = [
                'docker', 'exec', 'mcp-gateway',
                'mcp', 'call', self.mcp_tool_name,
                '--video-id', video_id
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return Transcript(
                    video_id=video_id,
                    text=data.get('text', ''),
                    language=data.get('language', 'en'),
                    is_generated=data.get('is_generated', True)
                )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            print(f"MCP transcript fetch failed: {e}")

        return None

    def _fetch_via_api(
        self,
        video_id: str,
        languages: list[str]
    ) -> Optional[Transcript]:
        """
        Fetch transcript using youtube-transcript-api v1.2.x.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages

        Returns:
            Transcript object or None if unavailable
        """
        try:
            # Try to list available transcripts first
            transcript_list = self.api.list(video_id)

            # Find the best transcript
            selected_transcript = None
            is_generated = True

            # First, try to find a manual transcript in preferred languages
            for transcript in transcript_list:
                if not transcript.is_generated:
                    if transcript.language_code in languages or any(
                        transcript.language_code.startswith(lang.split('-')[0])
                        for lang in languages
                    ):
                        selected_transcript = transcript
                        is_generated = False
                        break

            # Fall back to auto-generated in preferred languages
            if not selected_transcript:
                for transcript in transcript_list:
                    if transcript.is_generated:
                        if transcript.language_code in languages or any(
                            transcript.language_code.startswith(lang.split('-')[0])
                            for lang in languages
                        ):
                            selected_transcript = transcript
                            is_generated = True
                            break

            # Last resort: take any available transcript
            if not selected_transcript and transcript_list:
                selected_transcript = transcript_list[0]
                is_generated = selected_transcript.is_generated

            if selected_transcript:
                # Fetch the actual transcript content
                fetched = selected_transcript.fetch()
                full_text = ' '.join([snippet.text for snippet in fetched])

                return Transcript(
                    video_id=video_id,
                    text=full_text,
                    language=selected_transcript.language_code,
                    is_generated=is_generated
                )

        except NoTranscriptFound:
            # Try yt-dlp as fallback
            return self._fetch_via_ytdlp(video_id)
        except TranscriptsDisabled:
            print(f"Transcripts disabled for video: {video_id}, trying yt-dlp...")
            return self._fetch_via_ytdlp(video_id)
        except VideoUnavailable:
            print(f"Video unavailable: {video_id}")
            return None
        except Exception as e:
            # For any other error (including IP blocks), try yt-dlp
            print(f"youtube-transcript-api failed for {video_id}, trying yt-dlp...")
            return self._fetch_via_ytdlp(video_id)

    def _direct_fetch(self, video_id: str) -> Optional[Transcript]:
        """
        Direct fetch without listing transcripts first.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript object or None
        """
        try:
            fetched = self.api.fetch(video_id)
            full_text = ' '.join([snippet.text for snippet in fetched])

            return Transcript(
                video_id=video_id,
                text=full_text,
                language='en',  # Assume English for direct fetch
                is_generated=True
            )
        except Exception as e:
            # Try yt-dlp as fallback
            return self._fetch_via_ytdlp(video_id)

    def _fetch_via_ytdlp(self, video_id: str) -> Optional[Transcript]:
        """
        Fetch transcript using yt-dlp (more robust against IP bans).

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript object or None
        """
        import tempfile
        import os
        import re

        url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use yt-dlp to download subtitles
                cmd = [
                    'yt-dlp',
                    '--skip-download',
                    '--write-auto-sub',
                    '--write-sub',
                    '--sub-lang', 'en',
                    '--sub-format', 'vtt',
                    '--output', os.path.join(tmpdir, '%(id)s'),
                    url
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                # Find the subtitle file
                sub_files = [f for f in os.listdir(tmpdir) if f.endswith('.vtt')]

                if not sub_files:
                    return None

                # Read and parse VTT file
                sub_path = os.path.join(tmpdir, sub_files[0])
                with open(sub_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse VTT to plain text
                text = self._parse_vtt(content)

                if text:
                    return Transcript(
                        video_id=video_id,
                        text=text,
                        language='en',
                        is_generated=True
                    )

        except subprocess.TimeoutExpired:
            print(f"yt-dlp timeout for {video_id}")
        except Exception as e:
            print(f"yt-dlp failed for {video_id}: {e}")

        return None

    def _parse_vtt(self, vtt_content: str) -> str:
        """
        Parse VTT subtitle content to plain text.

        Args:
            vtt_content: Raw VTT file content

        Returns:
            Plain text transcript
        """
        import re

        lines = vtt_content.split('\n')
        text_lines = []
        seen = set()

        for line in lines:
            # Skip VTT headers, timestamps, and empty lines
            line = line.strip()
            if not line:
                continue
            if line.startswith('WEBVTT'):
                continue
            if line.startswith('Kind:') or line.startswith('Language:'):
                continue
            if '-->' in line:
                continue
            if re.match(r'^\d+$', line):
                continue

            # Remove HTML tags
            line = re.sub(r'<[^>]+>', '', line)

            # Skip duplicates (common in auto-generated subs)
            if line not in seen:
                seen.add(line)
                text_lines.append(line)

        return ' '.join(text_lines)

    def get_transcripts_batch(
        self,
        video_ids: list[str],
        languages: list[str] = ['en', 'en-US', 'en-GB']
    ) -> dict[str, Optional[Transcript]]:
        """
        Get transcripts for multiple videos.

        Args:
            video_ids: List of YouTube video IDs
            languages: Preferred languages

        Returns:
            Dictionary mapping video_id to Transcript (or None)
        """
        results = {}
        for video_id in video_ids:
            results[video_id] = self.get_transcript(video_id, languages)
        return results
