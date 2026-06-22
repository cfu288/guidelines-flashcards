# docs/

GitHub Pages site that renders the `manifest.yaml` listings for browsing.

**Generated** — do not edit by hand. Regenerate after manifest changes:

```bash
uv run scripts/build_docs.py
```

## Layout

- `index.md` — root: list of systems with topic/version/high-yield counts
- `<system>.md` — per system: each topic with all versions, publisher URLs, notes, and ⚠️ flags

`source.<format>.local` paths are intentionally NOT linked — those files are gitignored (copyrighted source documents). Only publisher URLs and metadata are surfaced.

## Enabling on GitHub

Repo → **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main` → Folder: `/docs`. Site appears at `https://<owner>.github.io/<repo>/` within a minute or two.

Theme is Jekyll's default `minima` (set in `_config.yml`). No custom CSS.
