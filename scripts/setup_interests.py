"""
Step 3: Set up user interests and get recommendations

Usage:
    python scripts/setup_interests.py --add "AI agents and automation"
    python scripts/setup_interests.py --list
    python scripts/setup_interests.py --recommend
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.embedding_generator import EmbeddingGenerator
from src.database import Database
from src.relevance_scorer import RelevanceScorer

console = Console()


def main():
    parser = argparse.ArgumentParser(description='Manage user interests and get recommendations')
    parser.add_argument('--add', '-a', help='Add a new interest topic')
    parser.add_argument('--priority', '-p', default='medium', choices=['high', 'medium', 'low'],
                        help='Priority for the interest (default: medium)')
    parser.add_argument('--list', '-l', action='store_true', help='List all interests')
    parser.add_argument('--recommend', '-r', action='store_true', help='Get video recommendations')
    parser.add_argument('--min-score', type=float, default=0.1, help='Minimum relevance score (0-1)')
    parser.add_argument('--max-results', type=int, default=5, help='Maximum recommendations')
    parser.add_argument('--setup-default', action='store_true', help='Set up default AI-focused interests')

    args = parser.parse_args()

    # Initialize
    console.print("[dim]Loading components...[/dim]")
    embedder = EmbeddingGenerator(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Database()
    scorer = RelevanceScorer(embedder, db)

    if args.setup_default:
        # Set up default AI-focused interests
        default_interests = [
            ("Large language models and LLM applications", "high"),
            ("AI agents and autonomous systems", "high"),
            ("RAG retrieval augmented generation", "high"),
            ("Claude and Anthropic AI tools", "high"),
            ("Machine learning tutorials and best practices", "medium"),
            ("AI coding assistants and developer tools", "medium"),
            ("Transformer architecture and attention mechanisms", "medium"),
            ("AI startups and entrepreneurship", "low"),
        ]

        console.print("\n[cyan]Setting up default AI-focused interests...[/cyan]\n")

        for topic, priority in default_interests:
            console.print(f"  Adding: {topic} ({priority})")
            scorer.add_interest(topic, priority)

        console.print(f"\n[green]Added {len(default_interests)} interests![/green]")

    elif args.add:
        # Add new interest
        console.print(f"\n[cyan]Adding interest:[/cyan] {args.add} ({args.priority})")
        scorer.add_interest(args.add, args.priority)
        console.print("[green]Interest added![/green]")

    elif args.list:
        # List all interests
        interests = scorer.get_user_interests()

        if not interests:
            console.print("\n[yellow]No interests defined yet.[/yellow]")
            console.print("Run with --setup-default to add AI-focused interests, or --add to add custom ones.")
            return

        table = Table(title="User Interests")
        table.add_column("Topic", style="white")
        table.add_column("Priority", style="cyan")

        for interest in interests:
            topic = interest.get('topic', 'Unknown')
            priority = interest.get('metadata', {}).get('priority', 'medium')
            table.add_row(topic, priority)

        console.print("\n")
        console.print(table)

    elif args.recommend:
        # Get recommendations
        interests = scorer.get_user_interests()

        if not interests:
            console.print("\n[yellow]No interests defined. Run with --setup-default first.[/yellow]")
            return

        console.print(f"\n[cyan]Getting recommendations based on {len(interests)} interests...[/cyan]\n")

        recommendations = scorer.get_recommendations(
            min_score=args.min_score,
            max_results=args.max_results
        )

        if not recommendations:
            console.print("[yellow]No videos meet the minimum relevance score.[/yellow]")
            return

        console.print(f"[green]Found {len(recommendations)} relevant videos:[/green]\n")

        for i, rec in enumerate(recommendations, 1):
            score_pct = rec.relevance_score * 100

            # Format matching interests
            interests_str = ", ".join([f"{t} ({s*100:.0f}%)" for t, s in rec.top_matching_interests[:2]])

            console.print(Panel(
                f"[bold]{rec.title}[/bold]\n"
                f"[dim]Channel: {rec.channel}[/dim]\n"
                f"[dim]Published: {rec.published_at[:10] if rec.published_at else 'Unknown'}[/dim]\n\n"
                f"[cyan]Relevance Score: {score_pct:.1f}%[/cyan]\n"
                f"[dim]Matching: {interests_str}[/dim]\n\n"
                f"[link={rec.url}]{rec.url}[/link]",
                title=f"#{i} Recommendation"
            ))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
