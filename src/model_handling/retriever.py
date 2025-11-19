# src/model_handling/retriever.py
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ..config.config import EMBEDDING_MODEL_NAME
from ..utils.logging_utils import setup_logger

logger = setup_logger("retriever")

# Load once at import time
_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts):
    """Batch embed list of strings."""
    return _model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def build_group_query(group_columns):
    """
    Create a strong query representation for a group.
    Uses column names + definitions.
    """
    parts = []
    for col in group_columns:
        name = col["Column Name"]
        defn = col["Definition"]
        parts.append(f"{name}: {defn}")
    return " | ".join(parts)


def retrieve_top_chunks(chunks, group, chunk_embeddings, top_k=4):
    """
    Returns the top_k most relevant chunks for a group.
    """
    query = build_group_query(group)
    query_emb = embed_texts([query])[0]  # (dim,)

    # Compute similarity with all chunks
    sims = cosine_similarity([query_emb], chunk_embeddings)[0]
    top_indices = np.argsort(sims)[::-1][:top_k]

    selected = []
    for idx in top_indices:
        chunk = chunks[idx].copy()
        chunk["_score"] = float(sims[idx])
        chunk["_chunk_id"] = idx
        selected.append(chunk)

    return selected