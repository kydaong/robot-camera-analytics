# data/

Drop source documents here before running ingestion scripts.

| Folder | What goes here | Ingestion script |
|---|---|---|
| `standards/` | Singapore standard PDFs (SS, CP, TR series) | `scripts/ingest_standards.py` |
| `manuals/` | OEM equipment manuals (pump, valve, pipe PDFs) | `scripts/ingest_manuals.py` |

These folders are git-ignored (only `.gitkeep` is tracked).
Do NOT commit PDFs — they may be licensed documents.
