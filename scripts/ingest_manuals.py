"""
Ingest OEM equipment manuals into Qdrant using hybrid chunking.

Usage:
    python scripts/ingest_manuals.py --dir ./data/manuals
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.vector_store import ensure_collections
from app.services.vector_service import upsert_document
from scripts.chunking import hybrid_chunk


def extract_text(pdf_path: Path) -> str:
    try:
        import pypdf
    except ImportError:
        raise SystemExit("Run: pip install pypdf")
    reader = pypdf.PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def ingest_pdf(pdf_path: Path) -> int:
    text = extract_text(pdf_path)
    chunks = hybrid_chunk(text, max_words=400, overlap_words=60)

    for chunk in chunks:
        upsert_document(
            collection=settings.QDRANT_COLLECTION_MANUALS,
            text=chunk["text"],
            metadata={
                "source": pdf_path.name,
                "section": chunk["section"],
                "chunk_index": chunk["chunk_index"],
                "document_type": "oem_manual",
            },
        )
    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="Ingest OEM manuals into Qdrant")
    parser.add_argument("--dir", required=True, help="Folder containing manual PDFs")
    args = parser.parse_args()

    ensure_collections()
    pdfs = list(Path(args.dir).glob("*.pdf"))
    if not pdfs:
        print("No PDFs found.")
        return

    total = 0
    for pdf in pdfs:
        print(f"  {pdf.name} ...", end=" ", flush=True)
        n = ingest_pdf(pdf)
        print(f"{n} chunks")
        total += n
    print(f"\nDone — {total} chunks across {len(pdfs)} manuals.")


if __name__ == "__main__":
    main()
