"""
One-time ingestion script: load Singapore engineering standards PDFs into Qdrant.

Usage:
    python scripts/ingest_standards.py --dir ./data/standards

Each PDF is chunked, embedded, and upserted into the QDRANT_COLLECTION_STANDARDS collection.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.vector_store import ensure_collections
from app.services.vector_service import upsert_document


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def ingest_pdf(pdf_path: Path, collection: str) -> int:
    try:
        import pypdf
    except ImportError:
        raise SystemExit("Install pypdf: pip install pypdf")

    reader = pypdf.PdfReader(str(pdf_path))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    chunks = chunk_text(full_text)

    for idx, chunk in enumerate(chunks):
        upsert_document(
            collection=collection,
            text=chunk,
            metadata={
                "source": pdf_path.name,
                "chunk_index": idx,
                "standard_type": "singapore_standard",
            },
        )
    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="Ingest Singapore standards into Qdrant")
    parser.add_argument("--dir", required=True, help="Directory containing PDF files")
    args = parser.parse_args()

    ensure_collections()
    pdf_dir = Path(args.dir)
    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}")
        return

    total = 0
    for pdf in pdfs:
        print(f"Ingesting {pdf.name}...")
        n = ingest_pdf(pdf, settings.QDRANT_COLLECTION_STANDARDS)
        print(f"  → {n} chunks")
        total += n

    print(f"\nDone. Total chunks ingested: {total}")


if __name__ == "__main__":
    main()
