"""
Database - SQLite for metadata + ChromaDB for vector storage
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings


@dataclass
class VideoMetadata:
    """Video metadata stored in SQLite"""
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    published_at: datetime
    description: str
    thumbnail_url: str
    transcript_path: Optional[str] = None
    processed: bool = False
    relevance_score: Optional[float] = None


class Database:
    """Combined SQLite + ChromaDB database"""

    def __init__(self, db_path: str = "data/youtube.db", chroma_path: str = "data/chroma"):
        """
        Initialize the database.

        Args:
            db_path: Path to SQLite database file
            chroma_path: Path to ChromaDB storage directory
        """
        self.db_path = Path(db_path)
        self.chroma_path = Path(chroma_path)

        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite
        self._init_sqlite()

        # Initialize ChromaDB
        self._init_chromadb()

    def _init_sqlite(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Videos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                channel_title TEXT,
                published_at TIMESTAMP,
                description TEXT,
                thumbnail_url TEXT,
                transcript_path TEXT,
                processed BOOLEAN DEFAULT FALSE,
                relevance_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Channels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                subscriber_count INTEGER,
                video_count INTEGER,
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # User interests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                embedding_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def _init_chromadb(self):
        """Initialize ChromaDB vector store"""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Collection for video transcript chunks
        self.transcript_collection = self.chroma_client.get_or_create_collection(
            name="transcript_chunks",
            metadata={"description": "Video transcript embeddings"}
        )

        # Collection for user interests
        self.interests_collection = self.chroma_client.get_or_create_collection(
            name="user_interests",
            metadata={"description": "User interest embeddings"}
        )

    # --- Video Operations ---

    def save_video(self, video: VideoMetadata):
        """Save or update video metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO videos
            (video_id, title, channel_id, channel_title, published_at,
             description, thumbnail_url, transcript_path, processed, relevance_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            video.video_id,
            video.title,
            video.channel_id,
            video.channel_title,
            video.published_at.isoformat() if video.published_at else None,
            video.description,
            video.thumbnail_url,
            video.transcript_path,
            video.processed,
            video.relevance_score
        ))

        conn.commit()
        conn.close()

    def get_video(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM videos WHERE video_id = ?', (video_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return VideoMetadata(
            video_id=row[0],
            title=row[1],
            channel_id=row[2],
            channel_title=row[3],
            published_at=datetime.fromisoformat(row[4]) if row[4] else None,
            description=row[5],
            thumbnail_url=row[6],
            transcript_path=row[7],
            processed=bool(row[8]),
            relevance_score=row[9]
        )

    def get_unprocessed_videos(self) -> list[VideoMetadata]:
        """Get all videos that haven't been processed for embeddings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM videos WHERE processed = FALSE')
        rows = cursor.fetchall()
        conn.close()

        return [
            VideoMetadata(
                video_id=row[0],
                title=row[1],
                channel_id=row[2],
                channel_title=row[3],
                published_at=datetime.fromisoformat(row[4]) if row[4] else None,
                description=row[5],
                thumbnail_url=row[6],
                transcript_path=row[7],
                processed=bool(row[8]),
                relevance_score=row[9]
            )
            for row in rows
        ]

    def mark_video_processed(self, video_id: str):
        """Mark a video as processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE videos SET processed = TRUE, updated_at = CURRENT_TIMESTAMP WHERE video_id = ?',
            (video_id,)
        )
        conn.commit()
        conn.close()

    def update_relevance_score(self, video_id: str, score: float):
        """Update the relevance score for a video"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE videos SET relevance_score = ?, updated_at = CURRENT_TIMESTAMP WHERE video_id = ?',
            (score, video_id)
        )
        conn.commit()
        conn.close()

    # --- Embedding Operations ---

    def save_transcript_embeddings(
        self,
        video_id: str,
        chunks: list[dict],
        embeddings: list[list[float]]
    ):
        """
        Save transcript chunk embeddings to ChromaDB.

        Args:
            video_id: ID of the video
            chunks: List of chunk dictionaries with text and metadata
            embeddings: List of embeddings corresponding to chunks
        """
        if not chunks or not embeddings:
            return

        ids = [f"{video_id}_chunk_{i}" for i in range(len(chunks))]
        documents = [chunk['text'] for chunk in chunks]
        metadatas = [
            {
                'video_id': video_id,
                'chunk_index': chunk.get('chunk_index', i),
                'start_char': chunk.get('start_char', 0),
                'end_char': chunk.get('end_char', len(chunk['text']))
            }
            for i, chunk in enumerate(chunks)
        ]

        self.transcript_collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search_transcripts(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        video_ids: list[str] = None
    ) -> list[dict]:
        """
        Search transcript embeddings by similarity.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            video_ids: Optional filter by specific video IDs

        Returns:
            List of matching chunks with scores
        """
        where_filter = None
        if video_ids:
            where_filter = {"video_id": {"$in": video_ids}}

        results = self.transcript_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        matches = []
        if results['ids'] and results['ids'][0]:
            for i, id in enumerate(results['ids'][0]):
                matches.append({
                    'id': id,
                    'text': results['documents'][0][i] if results['documents'] else None,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None,
                    'similarity': 1 - results['distances'][0][i] if results['distances'] else None
                })

        return matches

    # --- User Interest Operations ---

    def save_user_interest(self, topic: str, priority: str, embedding: list[float]):
        """Save a user interest with its embedding"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Save to SQLite
        cursor.execute(
            'INSERT INTO user_interests (topic, priority) VALUES (?, ?)',
            (topic, priority)
        )
        interest_id = cursor.lastrowid
        embedding_id = f"interest_{interest_id}"

        cursor.execute(
            'UPDATE user_interests SET embedding_id = ? WHERE id = ?',
            (embedding_id, interest_id)
        )
        conn.commit()
        conn.close()

        # Save embedding to ChromaDB
        self.interests_collection.upsert(
            ids=[embedding_id],
            documents=[topic],
            embeddings=[embedding],
            metadatas=[{"topic": topic, "priority": priority}]
        )

    def get_user_interests(self) -> list[dict]:
        """Get all user interests with their embeddings"""
        results = self.interests_collection.get(
            include=["documents", "metadatas", "embeddings"]
        )

        interests = []
        if results['ids']:
            for i, id in enumerate(results['ids']):
                embedding = None
                if results.get('embeddings') is not None and len(results['embeddings']) > i:
                    embedding = results['embeddings'][i]

                interests.append({
                    'id': id,
                    'topic': results['documents'][i] if results.get('documents') else None,
                    'metadata': results['metadatas'][i] if results.get('metadatas') else {},
                    'embedding': embedding
                })

        return interests

    def get_collection_stats(self) -> dict:
        """Get statistics about the collections"""
        return {
            'transcript_chunks': self.transcript_collection.count(),
            'user_interests': self.interests_collection.count()
        }
