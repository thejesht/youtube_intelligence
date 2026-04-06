"""
Test semantic search on embedded transcripts
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.embedding_generator import EmbeddingGenerator
from src.database import Database

console = Console()


def main():
    # Initialize
    console.print("[cyan]Loading embedding model...[/cyan]")
    embedder = EmbeddingGenerator(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Database()

    # Test queries
    queries = [
        "How do AI agents work?",
        "Claude Code tutorial",
        "marketing automation with AI",
        "transformer architecture and attention",
        "RAG retrieval augmented generation"
    ]

    console.print("\n[bold]Semantic Search Test[/bold]\n")

    for query in queries:
        console.print(f"[cyan]Query:[/cyan] {query}")

        # Generate query embedding
        query_embedding = embedder.generate_embedding(query)

        # Search
        results = db.search_transcripts(query_embedding, n_results=3)

        if results:
            for i, r in enumerate(results, 1):
                similarity = r.get('similarity', 0) * 100
                text_preview = r['text'][:150] + "..." if len(r['text']) > 150 else r['text']
                video_id = r['metadata'].get('video_id', 'unknown')

                console.print(f"  {i}. [green]{similarity:.1f}%[/green] ({video_id})")
                console.print(f"     [dim]{text_preview}[/dim]")
        else:
            console.print("  [yellow]No results found[/yellow]")

        console.print()

    # Show stats
    stats = db.get_collection_stats()
    console.print(f"[dim]Database: {stats['transcript_chunks']} chunks, {stats['user_interests']} interests[/dim]")


if __name__ == '__main__':
    main()
