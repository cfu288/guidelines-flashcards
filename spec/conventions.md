# Local OKF Conventions

This project's `references/guidelines/` bundle follows OKF v0.1 (see
`knowledge-catalog/okf/SPEC.md`) with the project-specific conventions below.

## Concept types

| `type:` value        | Used for                                                            |
| -------------------- | ------------------------------------------------------------------- |
| `Clinical Guideline` | A single named society guideline (e.g., GINA 2026).                 |
| `Study Guide`        | Cross-cutting curated lists (e.g., highest-yield named guidelines). |

## Custom frontmatter keys

| Key             | Type    | Purpose                                                                   |
| --------------- | ------- | ------------------------------------------------------------------------- |
| `society`       | string  | Issuing body (e.g., `GINA`, `KDIGO`, `AHA/ACC`).                          |
| `year`          | integer | Year of this version. Omit for living / non-versioned docs.               |
| `supersedes`    | path    | Prior version this replaces (bundle-relative).                            |
| `source`        | map     | Format-keyed map of `{<format>: {url?, local?}}` — see schema note below. |
| `card_eligible` | bool    | Whether the card generator should consume this concept.                   |

`source` shape:

```yaml
source:
  pdf:
    url: https://...           # publisher's direct URL for the PDF
    local: /sources/.../foo.pdf
  epub:
    url: https://...
    local: /sources/.../foo.epub
  html:
    url: https://...           # publisher's HTML full-text URL
```

Format keys are open-ended (`pdf`, `epub`, `html`, `xml`, `docx`, …). Each entry has an optional `url` (publisher source for that format) and an optional `local` (path under `sources/` once downloaded). Format-preference logic lives in the parsing/download scripts, not in the manifest — text formats (epub, html, xml) are preferred over rendered formats (pdf) because they extract without LlamaParse.

"Current" is derived: the version with the highest `year` per topic. A version with no `year` is treated as living / non-versioned.

## High-yield topics

Add `high_yield: true` at the **topic** level (peer of `title:` / `society:` / `versions:`) to mark a topic as one a resident should know cold. This is the **single source of truth** for two downstream outputs:

1. **Card tag**: `build_apkg.py` reads the manifest at build time and emits a `high-yield` tag on every card from a flagged topic. No card regeneration needed when the flag changes — re-running `build_apkg.py` is enough.
1. **Study-guide entries**: `build_references.py` auto-derives the bullet list inside `references/guidelines/study-guides/highest-yield-named-guidelines.md` from the same flags. **Do not declare an `entries:` list under `study_guides.highest-yield-named-guidelines` in the manifest** — it would be ignored and would drift.

The two outputs are guaranteed aligned by construction.

## Source-parse format preference

`scripts/parse_sources.py` is the unified parser. For each (topic-dir, basename) group under `sources/`, it picks the highest-preference format on disk and parses **only that one**:

```
epub > html > pdf
```

Each generated `.md` carries an HTML-comment provenance marker at the top:

```html
<!-- parsed-from: 2025-aha-acc.epub sha256:abc123... -->
```

The marker drives idempotency. On re-runs: same format + same hash → skip; better format now available → re-parse from the better one; unmarked legacy `.md` with no upgrade available → leave alone (don't waste LlamaParse credits). Dropping a new EPUB into a folder that previously only had a PDF automatically triggers a re-parse on next run.

## Enrichment state file

`scripts/enrich_references.py` writes `build/.enrich-state.json` at batch-submit time, recording every batch ID plus its `custom_id → {concept_path, source_hash}` mapping. On any invocation, before submitting new work, it ingests any prior-batch results that weren't already processed (auto-recovery from crash, Ctrl-C, or cancellation-that-didn't-cancel-in-time). The state file is gitignored (`build/` is gitignored); deleting it loses recovery state for any genuinely in-flight batch, but already-enriched concepts are protected separately by their `_source_hash` frontmatter marker.

## Directory layout

One subdirectory per body system; one `.md` file per guideline; each
subdirectory has an `index.md`.
