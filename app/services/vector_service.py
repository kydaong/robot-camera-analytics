"""
Vector embedding and semantic search via Qdrant.
Uses sentence-transformers (all-MiniLM-L6-v2, 384-dim) for local embeddings.
"""
from functools import lru_cache
from typing import Any
from uuid import uuid4

from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

from app.config import settings
from app.core.vector_store import get_qdrant_client


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def upsert_document(
    collection: str,
    text: str,
    metadata: dict[str, Any],
    doc_id: str | int | None = None,
) -> str:
    client = get_qdrant_client()
    vector = embed_text(text)
    # Qdrant accepts unsigned integers or proper UUID strings only
    if isinstance(doc_id, int):
        point_id: str | int = doc_id
    elif isinstance(doc_id, str) and doc_id.isdigit():
        point_id = int(doc_id)
    else:
        point_id = doc_id or str(uuid4())
    client.upsert(
        collection_name=collection,
        points=[PointStruct(id=point_id, vector=vector, payload={"text": text, **metadata})],
    )
    return str(point_id)


def semantic_search(
    collection: str,
    query: str,
    limit: int = 5,
    filter_field: str | None = None,
    filter_value: Any = None,
) -> list[dict[str, Any]]:
    client = get_qdrant_client()
    vector = embed_text(query)
    qfilter = None
    if filter_field and filter_value is not None:
        qfilter = Filter(
            must=[FieldCondition(key=filter_field, match=MatchValue(value=filter_value))]
        )
    results = client.search(
        collection_name=collection,
        query_vector=vector,
        limit=limit,
        query_filter=qfilter,
        with_payload=True,
    )
    return [{"score": r.score, **r.payload} for r in results]
