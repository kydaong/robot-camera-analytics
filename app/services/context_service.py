"""
RAG context retrieval — bundles relevant chunks from Qdrant for the agent prompt.
"""
from app.config import settings
from app.services.vector_service import semantic_search


def get_standards_context(query: str, limit: int = 5) -> list[dict]:
    return semantic_search(settings.QDRANT_COLLECTION_STANDARDS, query, limit=limit)


def get_incidents_context(query: str, limit: int = 5) -> list[dict]:
    return semantic_search(settings.QDRANT_COLLECTION_INCIDENTS, query, limit=limit)


def get_manuals_context(query: str, limit: int = 3) -> list[dict]:
    return semantic_search(settings.QDRANT_COLLECTION_MANUALS, query, limit=limit)


def get_inspection_tasks_context(query: str, limit: int = 5) -> list[dict]:
    return semantic_search(settings.QDRANT_COLLECTION_INSPECTION_TASKS, query, limit=limit)


def build_context_block(query: str) -> str:
    """Return a formatted context string to inject into the system prompt."""
    standards = get_standards_context(query)
    incidents = get_incidents_context(query)
    manuals = get_manuals_context(query)
    inspection_tasks = get_inspection_tasks_context(query)

    parts: list[str] = []
    if standards:
        parts.append("## Relevant Singapore Standards\n" + "\n---\n".join(
            s.get("text", "") for s in standards
        ))
    if incidents:
        parts.append("## Similar Past Incidents\n" + "\n---\n".join(
            i.get("text", "") for i in incidents
        ))
    if manuals:
        parts.append("## OEM Manual Excerpts\n" + "\n---\n".join(
            m.get("text", "") for m in manuals
        ))
    if inspection_tasks:
        parts.append("## Recent Inspection Tasks\n" + "\n---\n".join(
            t.get("text", "") for t in inspection_tasks
        ))
    return "\n\n".join(parts)
