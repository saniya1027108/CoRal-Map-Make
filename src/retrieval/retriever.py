# src/retrieval/retriever.py
"""
Retrieval strategies for efficient chunk selection.
Supports: BM25 (keyword), Semantic (embedding), and Hybrid (weighted combination).
"""

import numpy as np
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from rank_bm25 import BM25Plus
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from ..config.config import EMBEDDING_MODEL_NAME
from ..utils.logging_utils import setup_logger

logger = setup_logger("retriever")


def build_retrieval_query(group: List[Dict[str, str]]) -> str:
    """
    Build retrieval query from a group of columns.
    Format: "What is the value of {column name}: {definition}??"
    
    Args:
        group: List of column definitions [{"Column Name": ..., "Definition": ...}, ...]
    
    Returns:
        Query string for retrieval
    """
    queries = []
    for col in group:
        col_name = col.get("Column Name", "")
        definition = col.get("Definition", "")
        query = f"What is the value of {col_name}: {definition}??"
        queries.append(query)
    
    # Combine all column queries with space separator
    return " ".join(queries)


def combine_retrieved_chunks(chunks: List[Dict[str, Any]], max_chunks: Optional[int] = None) -> Dict[str, Any]:
    """
    Combine multiple retrieved chunks into a single structured chunk.
    
    Args:
        chunks: List of chunk dictionaries
        max_chunks: Maximum number of chunks to combine (None = all)
    
    Returns:
        Combined chunk dictionary with structured content
    """
    if not chunks:
        return {"content": "", "type": "text", "page": None}
    
    # Limit number of chunks if specified
    if max_chunks:
        chunks = chunks[:max_chunks]
    
    combined_parts = []
    page_numbers = []
    
    for i, chunk in enumerate(chunks, 1):
        # Build header
        chunk_type = chunk.get("type", "text")
        page_num = chunk.get("page", "unknown")
        page_numbers.append(page_num)
        
        header = f"=== CHUNK {i} (Page {page_num}, Type: {chunk_type}) ==="
        
        # Get content based on type
        if chunk_type == "text":
            content = chunk.get("content", "")
        elif chunk_type == "table":
            content = chunk.get("table_content", chunk.get("content", ""))
        elif chunk_type == "figure":
            content = chunk.get("figure_content", chunk.get("content", ""))
        else:
            content = chunk.get("content", "")
        
        combined_parts.append(f"{header}\n{content}")
    
    # Combine all parts
    combined_content = "\n\n".join(combined_parts)
    
    # Return as a pseudo-chunk
    return {
        "content": combined_content,
        "type": "combined",
        "page": page_numbers[0] if page_numbers else None,
        "source_chunks": len(chunks),
        "pages": page_numbers
    }


class BaseRetriever(ABC):
    """Abstract base class for retrievers."""
    
    def __init__(self, chunks: List[Dict[str, Any]]):
        """
        Initialize retriever with chunks.
        
        Args:
            chunks: List of document chunks
        """
        self.chunks = chunks
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """Initialize retriever (build indices, etc.)"""
        pass
    
    @abstractmethod
    def retrieve(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top-N most relevant chunks for query.
        
        Args:
            query: Search query string
            top_n: Number of chunks to retrieve
        
        Returns:
            List of top-N chunks (ordered by relevance)
        """
        pass


class BM25Retriever(BaseRetriever):
    """BM25-based keyword retriever (fast, good for exact matches)."""
    
    def _initialize(self):
        """Build BM25 index."""
        logger.info(f"Initializing BM25 retriever with {len(self.chunks)} chunks")
        
        # Tokenize chunks (lowercase for better matching)
        self.tokenized_chunks = []
        for chunk in self.chunks:
            content = chunk.get("content", "")
            # For table/figure chunks, use their specific content if available
            if chunk.get("type") == "table" and "table_content" in chunk:
                content = chunk["table_content"]
            elif chunk.get("type") == "figure" and "figure_content" in chunk:
                content = chunk["figure_content"]
            
            tokens = content.lower().split()
            self.tokenized_chunks.append(tokens)
        
        # Build BM25 index
        self.bm25 = BM25Plus(self.tokenized_chunks)
        logger.info("BM25 index built successfully")
    
    def retrieve(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Retrieve using BM25 scoring."""
        if not query.strip():
            logger.warning("Empty query provided, returning first N chunks")
            return self.chunks[:top_n]
        
        # Tokenize query
        query_tokens = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-N indices
        top_indices = np.argsort(scores)[-top_n:][::-1]
        
        # Return top chunks with scores
        top_chunks = [self.chunks[i] for i in top_indices]
        
        logger.info(f"BM25 retrieved {len(top_chunks)} chunks (scores: {scores[top_indices]})")
        return top_chunks


class SemanticRetriever(BaseRetriever):
    """Embedding-based semantic retriever (better for meaning, slower)."""
    
    def _initialize(self):
        """Build embedding index."""
        logger.info(f"Initializing Semantic retriever with {len(self.chunks)} chunks")
        
        # Load embedding model
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        # Extract content for embedding
        chunk_texts = []
        for chunk in self.chunks:
            content = chunk.get("content", "")
            # For table/figure chunks, use their specific content if available
            if chunk.get("type") == "table" and "table_content" in chunk:
                content = chunk["table_content"]
            elif chunk.get("type") == "figure" and "figure_content" in chunk:
                content = chunk["figure_content"]
            chunk_texts.append(content)
        
        # Encode all chunks (batch encoding is faster)
        logger.info("Encoding chunks with sentence transformer...")
        self.chunk_embeddings = self.embedding_model.encode(
            chunk_texts, 
            show_progress_bar=True,
            batch_size=32
        )
        logger.info(f"Encoded {len(self.chunk_embeddings)} chunk embeddings")
    
    def retrieve(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Retrieve using cosine similarity of embeddings."""
        if not query.strip():
            logger.warning("Empty query provided, returning first N chunks")
            return self.chunks[:top_n]
        
        # Encode query
        query_embedding = self.embedding_model.encode([query])[0]
        
        # Compute cosine similarities
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1), 
            self.chunk_embeddings
        )[0]
        
        # Get top-N indices
        top_indices = np.argsort(similarities)[-top_n:][::-1]
        
        # Return top chunks
        top_chunks = [self.chunks[i] for i in top_indices]
        
        logger.info(f"Semantic retrieved {len(top_chunks)} chunks (similarities: {similarities[top_indices]})")
        return top_chunks


class HybridRetriever(BaseRetriever):
    """
    Hybrid retriever combining BM25 and semantic search.
    Uses weighted combination of scores.
    """
    
    def __init__(self, chunks: List[Dict[str, Any]], bm25_weight: float = 0.5, semantic_weight: float = 0.5):
        """
        Initialize hybrid retriever.
        
        Args:
            chunks: List of document chunks
            bm25_weight: Weight for BM25 scores (0-1)
            semantic_weight: Weight for semantic scores (0-1)
        """
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        
        # Normalize weights
        total_weight = bm25_weight + semantic_weight
        self.bm25_weight /= total_weight
        self.semantic_weight /= total_weight
        
        super().__init__(chunks)
    
    def _initialize(self):
        """Initialize both BM25 and semantic retrievers."""
        logger.info(f"Initializing Hybrid retriever (BM25: {self.bm25_weight:.2f}, Semantic: {self.semantic_weight:.2f})")
        
        # Initialize BM25
        self.bm25_retriever = BM25Retriever(self.chunks)
        
        # Initialize semantic
        self.semantic_retriever = SemanticRetriever(self.chunks)
        
        logger.info("Hybrid retriever initialized")
    
    def retrieve(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve using weighted combination of BM25 and semantic scores.
        """
        if not query.strip():
            logger.warning("Empty query provided, returning first N chunks")
            return self.chunks[:top_n]
        
        # Get BM25 scores
        query_tokens = query.lower().split()
        bm25_scores = self.bm25_retriever.bm25.get_scores(query_tokens)
        
        # Get semantic scores
        query_embedding = self.semantic_retriever.embedding_model.encode([query])[0]
        semantic_scores = cosine_similarity(
            query_embedding.reshape(1, -1),
            self.semantic_retriever.chunk_embeddings
        )[0]
        
        # Normalize scores to [0, 1]
        bm25_scores_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-8)
        semantic_scores_norm = (semantic_scores - semantic_scores.min()) / (semantic_scores.max() - semantic_scores.min() + 1e-8)
        
        # Weighted combination
        combined_scores = (
            self.bm25_weight * bm25_scores_norm + 
            self.semantic_weight * semantic_scores_norm
        )
        
        # Get top-N indices
        top_indices = np.argsort(combined_scores)[-top_n:][::-1]
        
        # Return top chunks
        top_chunks = [self.chunks[i] for i in top_indices]
        
        logger.info(f"Hybrid retrieved {len(top_chunks)} chunks (combined scores: {combined_scores[top_indices]})")
        return top_chunks


def get_retriever(
    chunks: List[Dict[str, Any]], 
    strategy: str = "bm25",
    bm25_weight: float = 0.5,
    semantic_weight: float = 0.5
) -> BaseRetriever:
    """
    Factory function to create retriever based on strategy.
    
    Args:
        chunks: List of document chunks
        strategy: "bm25", "semantic", or "hybrid"
        bm25_weight: Weight for BM25 in hybrid mode
        semantic_weight: Weight for semantic in hybrid mode
    
    Returns:
        Retriever instance
    """
    strategy = strategy.lower()
    
    if strategy == "bm25":
        return BM25Retriever(chunks)
    elif strategy == "semantic":
        return SemanticRetriever(chunks)
    elif strategy == "hybrid":
        return HybridRetriever(chunks, bm25_weight, semantic_weight)
    else:
        raise ValueError(f"Unknown retrieval strategy: {strategy}. Choose from: bm25, semantic, hybrid")
