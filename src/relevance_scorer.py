"""
Relevance Scorer - Score videos against user interests
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass

from src.embedding_generator import EmbeddingGenerator
from src.database import Database


@dataclass
class UserProfile:
    """User profile with interests"""
    interests: list[dict]  # List of {topic, priority, embedding}


@dataclass
class VideoScore:
    """Scored video result"""
    video_id: str
    title: str
    channel: str
    published_at: str
    relevance_score: float
    top_matching_interests: list[tuple[str, float]]  # (interest, score) pairs
    url: str


class RelevanceScorer:
    """Score videos based on relevance to user interests"""

    def __init__(
        self,
        embedder: EmbeddingGenerator,
        db: Database,
        priority_weights: dict = None
    ):
        """
        Initialize the relevance scorer.

        Args:
            embedder: Embedding generator instance
            db: Database instance
            priority_weights: Weight multipliers for different priority levels
        """
        self.embedder = embedder
        self.db = db
        self.priority_weights = priority_weights or {
            'high': 1.5,
            'medium': 1.0,
            'low': 0.5
        }
        self._user_interests = None

    def add_interest(self, topic: str, priority: str = 'medium'):
        """
        Add a user interest.

        Args:
            topic: Interest topic/description
            priority: Priority level (high, medium, low)
        """
        embedding = self.embedder.generate_embedding(topic)
        self.db.save_user_interest(topic, priority, embedding)
        self._user_interests = None  # Clear cache

    def get_user_interests(self) -> list[dict]:
        """Get all user interests with embeddings"""
        if self._user_interests is None:
            self._user_interests = self.db.get_user_interests()
        return self._user_interests

    def score_video(self, video_id: str) -> Optional[VideoScore]:
        """
        Score a single video against user interests.

        Args:
            video_id: ID of the video to score

        Returns:
            VideoScore object or None if video not found
        """
        # Get video metadata
        video = self.db.get_video(video_id)
        if not video:
            return None

        # Get user interests
        interests = self.get_user_interests()
        if not interests:
            return VideoScore(
                video_id=video.video_id,
                title=video.title,
                channel=video.channel_title,
                published_at=video.published_at.isoformat() if video.published_at else '',
                relevance_score=0.0,
                top_matching_interests=[],
                url=f"https://www.youtube.com/watch?v={video.video_id}"
            )

        # Calculate relevance score
        interest_scores = []

        for interest in interests:
            embedding = interest.get('embedding')
            if embedding is None:
                continue

            # Search transcript chunks with this interest embedding
            results = self.db.search_transcripts(
                query_embedding=embedding,
                n_results=5,
                video_ids=[video_id]
            )

            if results:
                # Use max similarity as the score for this interest
                max_similarity = max(r.get('similarity', 0) for r in results)
                priority = interest.get('metadata', {}).get('priority', 'medium')
                weight = self.priority_weights.get(priority, 1.0)
                weighted_score = max_similarity * weight

                interest_scores.append({
                    'topic': interest.get('topic', ''),
                    'priority': priority,
                    'score': max_similarity,
                    'weighted_score': weighted_score
                })

        # Calculate overall relevance score
        if interest_scores:
            # Weighted average of top interest matches
            sorted_scores = sorted(interest_scores, key=lambda x: x['weighted_score'], reverse=True)
            top_scores = sorted_scores[:3]  # Top 3 matching interests

            overall_score = np.mean([s['weighted_score'] for s in top_scores])
            top_interests = [(s['topic'], s['score']) for s in top_scores]
        else:
            overall_score = 0.0
            top_interests = []

        # Update database
        self.db.update_relevance_score(video_id, overall_score)

        return VideoScore(
            video_id=video.video_id,
            title=video.title,
            channel=video.channel_title,
            published_at=video.published_at.isoformat() if video.published_at else '',
            relevance_score=overall_score,
            top_matching_interests=top_interests,
            url=f"https://www.youtube.com/watch?v={video.video_id}"
        )

    def score_all_videos(self) -> list[VideoScore]:
        """
        Score all processed videos against user interests.

        Returns:
            List of VideoScore objects sorted by relevance
        """
        import sqlite3
        from datetime import datetime

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT video_id FROM videos WHERE processed = TRUE')
        video_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        scores = []
        for video_id in video_ids:
            score = self.score_video(video_id)
            if score:
                scores.append(score)

        # Sort by relevance
        scores.sort(key=lambda x: x.relevance_score, reverse=True)
        return scores

    def get_recommendations(
        self,
        min_score: float = 0.1,
        max_results: int = 5
    ) -> list[VideoScore]:
        """
        Get video recommendations based on user interests.

        Args:
            min_score: Minimum relevance score (0-1)
            max_results: Maximum number of recommendations

        Returns:
            List of recommended videos
        """
        all_scores = self.score_all_videos()

        recommendations = [
            s for s in all_scores
            if s.relevance_score >= min_score
        ][:max_results]

        return recommendations
