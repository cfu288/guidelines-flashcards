# build/

Generated artifacts — the final outputs of the pipeline.

**Gitignored** — these are derivative works of copyrighted clinical guidelines (the Anki cards carry extracted recommendations + thresholds + paraphrased claims from `references/`, which itself derives from `sources/`). Same reasoning as `sources/` and `references/`: only this README is committed.

## Contents (when populated locally)

| File                 | What                                                                          | Produced by                                                  |
| -------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `cards.jsonl`        | one line per generated cloze card, with text, GUID, tags, provenance metadata | `scripts/generate_cards.py` (Anthropic batch — paid)         |
| `guidelines.apkg`    | self-contained Anki package: notetype + deck hierarchy + all notes            | `scripts/build_apkg.py` (no API calls — local genanki build) |
| `<system>.apkg`      | per-system slice of the deck                                                  | optional one-off builds                                      |
| `.enrich-state.json` | resume marker for `enrich_references.py` (auto-ignored separately)            | runtime, not an artifact                                     |

## Reproducing locally

Inputs required:

- A populated `references/guidelines/` tree (see [`references/README.md`](../references/README.md))
- Anthropic API key in `.env` for the card-generation step (or skip and rebuild from an existing `cards.jsonl`)

Pipeline:

```bash
uv run scripts/generate_cards.py    # references/**/*.md  → build/cards.jsonl   (paid)
uv run scripts/build_apkg.py        # build/cards.jsonl    → build/guidelines.apkg
```

Then `File → Import` in Anki on `build/guidelines.apkg`. Card GUIDs are stable across regenerations, so re-importing updates notes in place and preserves FSRS review history.
