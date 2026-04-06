"""
Embedding Generator - Generate embeddings using sentence-transformers
"""

from typing import Optional
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer


@dataclass
class TextChunk:
    """A chunk of text with metadata"""
    text: str
    video_id: str
    chunk_index: int
    start_char: int
    end_char: int


class EmbeddingGenerator:
    """Generate embeddings for text using sentence-transformers"""

    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        """
        Initialize the embedding generator.

        Args:
            model_name: Name of the sentence-transformers model to use
                       Default: BAAI/bge-large-en-v1.5 (~1.3GB, excellent quality)
                       Alternatives:
                       - sentence-transformers/all-MiniLM-L6-v2 (~90MB, good quality)
                       - BAAI/bge-small-en-v1.5 (~130MB, good balance)
        """
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            List of floats representing the embedding
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for encoding

        Returns:
            List of embeddings
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True
        )
        return embeddings.tolist()

    def chunk_text(
        self,
        text: str,
        video_id: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> list[TextChunk]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: Full transcript text
            video_id: ID of the video this text comes from
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of TextChunk objects
        """
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for sep in ['. ', '? ', '! ', '\n\n', '\n']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start + chunk_size // 2:
                        end = last_sep + len(sep)
                        break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(TextChunk(
                    text=chunk_text,
                    video_id=video_id,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end
                ))
                chunk_index += 1

            # Move start position with overlap
            start = end - overlap if end < len(text) else len(text)

        return chunks

    def process_transcript(
        self,
        text: str,
        video_id: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> list[tuple[TextChunk, list[float]]]:
        """
        Process a transcript: chunk it and generate embeddings.

        Args:
            text: Full transcript text
            video_id: ID of the video
            chunk_size: Target size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of (TextChunk, embedding) tuples
        """
        # Chunk the text
        chunks = self.chunk_text(text, video_id, chunk_size, overlap)

        if not chunks:
            return []

        # Generate embeddings for all chunks
        texts = [chunk.text for chunk in chunks]
        embeddings = self.generate_embeddings_batch(texts)

        # Pair chunks with embeddings
        return list(zip(chunks, embeddings))
