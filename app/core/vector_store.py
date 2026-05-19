"""
Qdrant vector store client — shared across services.
"""
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=settings.QDRANT_API_KEY,
    )


def _vector_size() -> int:
    return settings.EMBEDDING_DIM


def ensure_collections() -> None:
    """Create Qdrant collections if they don't exist yet."""
    client = get_qdrant_client()
    collections = {
        settings.QDRANT_COLLECTION_INCIDENTS: "Historical inspection incidents",
        settings.QDRANT_COLLECTION_STANDARDS: "Singapore engineering standards",
        settings.QDRANT_COLLECTION_MANUALS: "OEM equipment manuals",
    }
    existing = {c.name for c in client.get_collections().collections}
    for name in collections:
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=_vector_size(), distance=Distance.COSINE),
            )
