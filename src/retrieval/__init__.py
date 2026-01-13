# src/retrieval/__init__.py
"""
Retrieval module for efficient chunk selection.
Supports BM25, semantic, and hybrid retrieval strategies.
"""

from .retriever import (
    BaseRetriever,
    BM25Retriever,
    SemanticRetriever,
    HybridRetriever,
    get_retriever,
    build_retrieval_query,
    combine_retrieved_chunks
)

__all__ = [
    "BaseRetriever",
    "BM25Retriever", 
    "SemanticRetriever",
    "HybridRetriever",
    "get_retriever",
    "build_retrieval_query",
    "combine_retrieved_chunks"
]
