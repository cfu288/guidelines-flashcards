# Sources

Raw clinical-practice-guideline documents (PDFs, EPUBs, HTML) live here, organized as `sources/<system>/<topic>/<year>-<society>.<ext>`.

**These files are gitignored** — they are copyrighted publications of their respective societies (ACC/AHA, ESC, IDSA, KDIGO, GINA, GOLD, etc.) and are not redistributed via this repo. Only this README is committed.

## Reproducing the tree locally

Every expected file is declared in [`/manifest.yaml`](../manifest.yaml) under `source.<format>.local`. Once you have a `LLAMA_PARSE` key in `.env`:

| Task                                                                                  | Command                                                                                                                                                           |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auto-download anything fetchable by plain HTTP (PMC mirrors, USPSTF, CDC, KDIGO PDFs) | `uv run scripts/download_format_aware.py`                                                                                                                         |
| Headless browser fallback for publisher-direct PDFs (AHA, Oxford, Wiley)              | `uv run scripts/puppeteer_wrap.py prepare && node scripts/puppeteer_download.js && uv run scripts/puppeteer_wrap.py apply`                                        |
| Manual downloads (paywalled / login-walled)                                           | Open the visible-browser launchpad: `node scripts/open_browser.js`, click through entries, files land in `tmp/`, then `uv run scripts/import_manual_downloads.py` |
| What's still missing                                                                  | `uv run scripts/needs_attention_report.py` → see `spec/manifest-needs-attention.md`                                                                               |
| Parse PDFs to markdown sidecars (LlamaParse)                                          | `uv run scripts/parse_sources.py $(uv run scripts/list_pdfs_to_parse.py)`                                                                                         |

## Layout

```
sources/
├── <system>/                e.g., cardiology, pulmonary, nephrology, ...
│   └── <topic>/             e.g., hypertension, asthma, ckd, ...
│       ├── <year>-<society>.pdf      # downloaded source PDF
│       ├── <year>-<society>.epub     # downloaded source EPUB (if available)
│       ├── <year>-<society>.html     # publisher HTML or PMC mirror
│       └── <year>-<society>.md       # LlamaParse output (or local text extract)
```

Filenames follow `<year>-<society-slug>.<ext>` (e.g., `2025-aha-acc.pdf`). For living docs without a year, the slug is just `<society>.<ext>`.
