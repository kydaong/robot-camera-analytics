"""
Vector embedding and semantic search via Qdrant.
"""
from typing import Any
from uuid import uuid4

import anthropic
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

from app.config import settings
from app.core.vector_store import get_qdrant_client

_anthropic = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def embed_text(text: str) -> list[float]:
    """Generate an embedding using Claude-compatible approach via voyage or similar.
    Placeholder: replace with your chosen embedding model call.
    """
    # TODO: swap for actual embedding model (e.g. voyage-3, text-embedding-3-small)
    raise NotImplementedError("Configure your embedding provider in vector_service.py")


def upsert_document(
    collection: str,
    text: str,
    metadata: dict[str, Any],
    doc_id: str | None = None,
) -> str:
    client = get_qdrant_client()
    vector = embed_text(text)
    point_id = doc_id or str(uuid4())
    client.upsert(
        collection_name=collection,
        points=[PointStruct(id=point_id, vector=vector, payload={"text": text, **metadata})],
    )
    return point_id


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
