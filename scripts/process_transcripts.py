"""
Step 2: Process Transcripts - Generate embeddings and store in vector database

Usage:
    python scripts/process_transcripts.py
    python scripts/process_transcripts.py --model all-MiniLM-L6-v2  # Faster, smaller model
"""

import os
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from src.embedding_generator import EmbeddingGenerator
from src.database import Database, VideoMetadata

load_dotenv()
console = Console()


def parse_transcript_file(filepath: Path) -> dict:
    """
    Parse a transcript file and extract metadata.

    Returns:
        Dictionary with video_id, title, channel, published_at, and text
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split header and transcript
    parts = content.split('-' * 50)
    if len(parts) < 2:
        return None

    header = parts[0].strip()
    transcript = parts[1].strip()

    # Parse header
    metadata = {}
    for line in header.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip().lower().replace(' ', '_')] = value.strip()

    # Parse filename for date
    filename = filepath.stem
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})_(.+)', filename)
    if date_match:
        metadata['date_from_filename'] = date_match.group(1)

    return {
        'video_id': metadata.get('video_id', filepath.stem),
        'title': metadata.get('title', ''),
        'channel': metadata.get('channel', ''),
        'url': metadata.get('url', ''),
        'published_at': metadata.get('published', ''),
        'text': transcript,
        'filepath': str(filepath)
    }


def main():
    parser = argparse.ArgumentParser(description='Process transcripts and generate embeddings')
    parser.add_argument(
        '--transcripts-dir',
        default='data/transcripts',
        help='Directory containing transcript files'
    )
    parser.add_argument(
        '--model',
        default='BAAI/bge-large-en-v1.5',
        help='Embedding model to use (default: BAAI/bge-large-en-v1.5)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help='Chunk size in characters (default: 1000)'
    )
    parser.add_argument(
        '--overlap',
        type=int,
        default=200,
        help='Overlap between chunks (default: 200)'
    )
    parser.add_argument(
        '--db-path',
        default='data/youtube.db',
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--chroma-path',
        default='data/chroma',
        help='Path to ChromaDB storage'
    )

    args = parser.parse_args()

    transcripts_dir = Path(args.transcripts_dir)
    if not transcripts_dir.exists():
        console.print(f"[red]Error:[/red] Transcripts directory not found: {transcripts_dir}")
        sys.exit(1)

    # Find all transcript files
    transcript_files = list(transcripts_dir.glob('*.txt'))
    if not transcript_files:
        console.print(f"[yellow]No transcript files found in {transcripts_dir}[/yellow]")
        sys.exit(0)

    console.print(f"[cyan]Found {len(transcript_files)} transcript files[/cyan]\n")

    # Initialize components
    console.print("[cyan]Initializing embedding model...[/cyan]")
    embedder = EmbeddingGenerator(model_name=args.model)

    console.print("[cyan]Initializing database...[/cyan]")
    db = Database(db_path=args.db_path, chroma_path=args.chroma_path)

    # Process each transcript
    total_chunks = 0
    processed_videos = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Processing transcripts...", total=len(transcript_files))

        for filepath in transcript_files:
            progress.update(task, description=f"Processing: {filepath.name[:40]}...")

            # Parse transcript file
            data = parse_transcript_file(filepath)
            if not data or not data['text']:
                progress.advance(task)
                continue

            # Create video metadata
            try:
                published_at = datetime.fromisoformat(data['published_at'].replace('+00:00', ''))
            except (ValueError, TypeError):
                published_at = datetime.now()

            video = VideoMetadata(
                video_id=data['video_id'],
                title=data['title'],
                channel_id='',  # Not available in transcript
                channel_title=data['channel'],
                published_at=published_at,
                description='',
                thumbnail_url='',
                transcript_path=data['filepath'],
                processed=False
            )

            # Save video metadata
            db.save_video(video)

            # Process transcript into chunks and embeddings
            results = embedder.process_transcript(
                text=data['text'],
                video_id=data['video_id'],
                chunk_size=args.chunk_size,
                overlap=args.overlap
            )

            if results:
                # Save embeddings
                chunks = [
                    {
                        'text': chunk.text,
                        'chunk_index': chunk.chunk_index,
                        'start_char': chunk.start_char,
                        'end_char': chunk.end_char
                    }
                    for chunk, _ in results
                ]
                embeddings = [emb for _, emb in results]

                db.save_transcript_embeddings(
                    video_id=data['video_id'],
                    chunks=chunks,
                    embeddings=embeddings
                )

                total_chunks += len(chunks)

            # Mark as processed
            db.mark_video_processed(data['video_id'])
            processed_videos += 1

            progress.advance(task)

    # Show results
    console.print("\n")
    stats = db.get_collection_stats()

    table = Table(title="Processing Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Videos Processed", str(processed_videos))
    table.add_row("Total Chunks Created", str(total_chunks))
    table.add_row("Chunks in Database", str(stats['transcript_chunks']))
    table.add_row("Embedding Model", args.model)
    table.add_row("Chunk Size", f"{args.chunk_size} chars")
    table.add_row("Overlap", f"{args.overlap} chars")

    console.print(table)

    console.print(f"\n[green]Done![/green] Embeddings stored in:")
    console.print(f"  SQLite: {args.db_path}")
    console.print(f"  ChromaDB: {args.chroma_path}")


if __name__ == '__main__':
    main()
