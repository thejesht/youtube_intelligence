"""
Step 1: Fetch Channel Videos and Transcripts

Usage:
    python scripts/fetch_channel.py "Two Minute Papers"
    python scripts/fetch_channel.py "@TwoMinutePapers"
    python scripts/fetch_channel.py --channel-id "UCbfYPyITQ-7l4upoX8nvctg"
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.channel_monitor import ChannelMonitor, get_channel_id_from_url
from src.transcript_fetcher import TranscriptFetcher

# Load environment variables
load_dotenv()

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description='Fetch recent videos and transcripts from a YouTube channel'
    )
    parser.add_argument(
        'query',
        nargs='?',
        help='Channel name, @handle, or URL to search for'
    )
    parser.add_argument(
        '--channel-id',
        help='Direct channel ID (skips search)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=20,
        help='Number of days to look back (default: 20)'
    )
    parser.add_argument(
        '--max-videos',
        type=int,
        default=10,
        help='Maximum videos to fetch (default: 10)'
    )
    parser.add_argument(
        '--save-transcripts',
        action='store_true',
        help='Save transcripts to files'
    )
    parser.add_argument(
        '--output-dir',
        default='data/transcripts',
        help='Directory to save transcripts (default: data/transcripts)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.5,
        help='Delay between transcript requests in seconds (default: 2.5)'
    )
    parser.add_argument(
        '--cookies',
        default=None,
        help='Path to cookies.txt file for bypassing rate limits'
    )

    args = parser.parse_args()

    # Auto-detect cookies.txt in project root if not specified
    if not args.cookies:
        default_cookies = Path(__file__).parent.parent / 'cookies.txt'
        if default_cookies.exists():
            args.cookies = str(default_cookies)
            print(f"[dim]Using cookies from: {args.cookies}[/dim]")

    # Get API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        console.print(
            "[red]Error:[/red] YOUTUBE_API_KEY not found in environment.\n"
            "Please set it in a .env file or export it."
        )
        sys.exit(1)

    # Initialize components
    monitor = ChannelMonitor(api_key)
    fetcher = TranscriptFetcher(use_mcp=False, delay_seconds=args.delay, cookies_path=args.cookies)

    # Determine channel ID
    channel = None
    channel_id = args.channel_id

    if not channel_id:
        if not args.query:
            console.print("[red]Error:[/red] Please provide a channel name, handle, or --channel-id")
            sys.exit(1)

        query = args.query

        # Check if it's a URL
        if 'youtube.com' in query:
            extracted = get_channel_id_from_url(query)
            if extracted:
                if extracted.startswith('UC'):
                    channel_id = extracted
                else:
                    # It's a handle or custom URL
                    query = extracted

        # Check if it's a handle
        if not channel_id and query.startswith('@'):
            console.print(f"[cyan]Searching for handle:[/cyan] {query}")
            channel = monitor.get_channel_by_handle(query)
            if channel:
                channel_id = channel.channel_id

        # Fall back to search
        if not channel_id:
            console.print(f"[cyan]Searching for channel:[/cyan] {query}")
            channels = monitor.search_channel(query)

            if not channels:
                console.print(f"[red]No channels found for:[/red] {query}")
                sys.exit(1)

            # Show search results
            if len(channels) > 1:
                console.print("\n[yellow]Multiple channels found. Select one:[/yellow]\n")
                table = Table(show_header=True)
                table.add_column("#", style="cyan", width=4)
                table.add_column("Channel Name", style="green")
                table.add_column("Channel ID", style="dim")

                for i, ch in enumerate(channels, 1):
                    table.add_row(str(i), ch.title, ch.channel_id)

                console.print(table)

                try:
                    choice = int(input("\nEnter number (1-{}): ".format(len(channels))))
                    if 1 <= choice <= len(channels):
                        channel = channels[choice - 1]
                        channel_id = channel.channel_id
                    else:
                        console.print("[red]Invalid choice[/red]")
                        sys.exit(1)
                except ValueError:
                    console.print("[red]Invalid input[/red]")
                    sys.exit(1)
            else:
                channel = channels[0]
                channel_id = channel.channel_id

    # Get channel details if we don't have them
    if not channel:
        channel = monitor.get_channel_by_id(channel_id)
        if not channel:
            console.print(f"[red]Could not find channel with ID:[/red] {channel_id}")
            sys.exit(1)

    # Display channel info
    console.print(Panel(
        f"[bold green]{channel.title}[/bold green]\n"
        f"[dim]ID: {channel.channel_id}[/dim]\n"
        f"[dim]Videos: {channel.video_count or 'N/A'} | "
        f"Subscribers: {channel.subscriber_count or 'N/A'}[/dim]",
        title="Channel Found"
    ))

    # Fetch recent videos
    console.print(f"\n[cyan]Fetching videos from the last {args.days} days...[/cyan]")
    videos = monitor.get_recent_videos(
        channel_id,
        days=args.days,
        max_results=args.max_videos
    )

    if not videos:
        console.print(f"[yellow]No videos found in the last {args.days} days[/yellow]")
        sys.exit(0)

    console.print(f"[green]Found {len(videos)} videos[/green]")
    if args.delay > 0:
        console.print(f"[dim]Using {args.delay}s delay between requests to avoid rate limiting[/dim]\n")

    # Create output directory if saving
    if args.save_transcripts:
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    # Fetch transcripts
    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Fetching transcripts...", total=len(videos))

        for video in videos:
            progress.update(task, description=f"Fetching: {video.title[:40]}...")

            transcript = fetcher.get_transcript(video.video_id)
            results.append({
                'video': video,
                'transcript': transcript
            })

            # Save transcript if requested
            if args.save_transcripts and transcript:
                # Format: YYYY-MM-DD_VideoTitle.txt (sortable by date)
                date_prefix = video.published_at.strftime("%Y-%m-%d")
                safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in video.title)
                safe_title = safe_title[:60].strip()
                filename = f"{date_prefix}_{safe_title}.txt"
                filepath = output_path / filename

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {video.title}\n")
                    f.write(f"Video ID: {video.video_id}\n")
                    f.write(f"URL: {video.url}\n")
                    f.write(f"Published: {video.published_at}\n")
                    f.write(f"Channel: {video.channel_title}\n")
                    f.write("-" * 50 + "\n\n")
                    f.write(transcript.text)

            progress.advance(task)

    # Display results
    console.print("\n")
    table = Table(title=f"Videos from {channel.title}", show_header=True)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Published", style="dim")
    table.add_column("Transcript", style="green")
    table.add_column("Length", style="dim")

    for i, result in enumerate(results, 1):
        video = result['video']
        transcript = result['transcript']

        has_transcript = "[green]Yes[/green]" if transcript else "[red]No[/red]"
        length = f"{len(transcript.text):,} chars" if transcript else "-"
        published = video.published_at.strftime("%Y-%m-%d")

        table.add_row(
            str(i),
            video.title[:50] + ("..." if len(video.title) > 50 else ""),
            published,
            has_transcript,
            length
        )

    console.print(table)

    # Summary
    successful = sum(1 for r in results if r['transcript'])
    console.print(f"\n[cyan]Summary:[/cyan] {successful}/{len(results)} videos have transcripts")

    if args.save_transcripts:
        console.print(f"[cyan]Transcripts saved to:[/cyan] {args.output_dir}")

    # Print sample transcript
    if results and results[0]['transcript']:
        sample = results[0]
        console.print(Panel(
            f"[bold]{sample['video'].title}[/bold]\n\n"
            f"{sample['transcript'].text[:500]}...\n\n"
            f"[dim](Showing first 500 characters)[/dim]",
            title="Sample Transcript Preview"
        ))


if __name__ == '__main__':
    main()
