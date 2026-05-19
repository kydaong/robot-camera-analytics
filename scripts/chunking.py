"""
Hybrid chunking for technical documents (standards, manuals, incident reports).

Strategy:
  1. Structural split  — break on detected headings and paragraph boundaries first
  2. Size enforcement  — any structural chunk exceeding max_tokens is split further
  3. Sentence-aware    — splits happen at sentence endings, not mid-sentence
  4. Overlap           — each chunk carries a tail of the previous chunk for context
"""
from __future__ import annotations

import re


# ── Heading detection ─────────────────────────────────────────────────────────

_HEADING_RE = re.compile(
    r"^("
    r"\d+(\.\d+)*\s+[A-Z]"          # 1.2.3 Title
    r"|[A-Z][A-Z\s]{4,}$"            # ALL CAPS HEADING
    r"|Clause\s+\d"                  # Clause 4
    r"|Section\s+\d"                 # Section 3
    r"|Annex\s+[A-Z\d]"             # Annex A
    r"|Chapter\s+\d"                 # Chapter 2
    r")",
    re.MULTILINE,
)


def _is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line.strip())) and len(line.strip()) < 120


def _split_sentences(text: str) -> list[str]:
    """Rough sentence splitter that keeps abbreviations intact."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\d\(])", text)
    return [p.strip() for p in parts if p.strip()]


# ── Core chunker ──────────────────────────────────────────────────────────────

def hybrid_chunk(
    text: str,
    max_words: int = 400,
    overlap_words: int = 60,
) -> list[dict[str, str]]:
    """
    Returns a list of dicts:
      { "text": str, "section": str (nearest heading), "chunk_index": int }
    """
    lines = text.splitlines()

    # Pass 1: group lines into structural blocks by heading
    blocks: list[dict] = []
    current_heading = "Introduction"
    current_lines: list[str] = []

    for line in lines:
        if _is_heading(line):
            if current_lines:
                blocks.append({
                    "section": current_heading,
                    "text": " ".join(current_lines).strip(),
                })
                current_lines = []
            current_heading = line.strip()
        else:
            stripped = line.strip()
            if stripped:
                current_lines.append(stripped)
            elif current_lines:
                # Blank line = paragraph boundary — flush as its own mini-block
                blocks.append({
                    "section": current_heading,
                    "text": " ".join(current_lines).strip(),
                })
                current_lines = []

    if current_lines:
        blocks.append({"section": current_heading, "text": " ".join(current_lines).strip()})

    # Pass 2: enforce max_words by splitting large blocks at sentence boundaries
    sized_blocks: list[dict] = []
    for block in blocks:
        words = block["text"].split()
        if len(words) <= max_words:
            sized_blocks.append(block)
            continue

        sentences = _split_sentences(block["text"])
        bucket: list[str] = []
        bucket_words = 0
        for sent in sentences:
            sent_words = len(sent.split())
            if bucket_words + sent_words > max_words and bucket:
                sized_blocks.append({"section": block["section"], "text": " ".join(bucket)})
                bucket = []
                bucket_words = 0
            bucket.append(sent)
            bucket_words += sent_words
        if bucket:
            sized_blocks.append({"section": block["section"], "text": " ".join(bucket)})

    # Pass 3: add overlap — prepend tail of previous chunk
    
    chunks: list[dict[str, str]] = []
    prev_tail = ""
    for i, block in enumerate(sized_blocks):
        body = (prev_tail + " " + block["text"]).strip() if prev_tail else block["text"]
        chunks.append({
            "text": body,
            "section": block["section"],
            "chunk_index": i,
        })
        # Tail = last overlap_words words of this block (not the prepended overlap)
        tail_words = block["text"].split()[-overlap_words:]
        prev_tail = " ".join(tail_words) if len(tail_words) == overlap_words else ""

    return [c for c in chunks if len(c["text"].split()) > 10]  # drop near-empty chunks


    
