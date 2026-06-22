# References

AI-extracted structured knowledge — OKF-conformant concept files derived from the source guidelines in [`/sources/`](../sources/).

**These files are gitignored** — they're *derivative works* of copyrighted clinical guidelines (verbatim quotes + structured extractions of recommendations, thresholds, and decision logic). Same reasoning as `sources/`: only this README is committed.

## Reproducing the bundle locally

Inputs required:

- A populated `sources/` tree (see [`sources/README.md`](../sources/README.md) for how to fetch)
- The extraction methodology in [`spec/guideline-extraction.md`](../spec/guideline-extraction.md)
- The local OKF conventions in [`spec/conventions.md`](../spec/conventions.md)

Then run the extraction pipeline against the parsed `.md` sidecars in `sources/`. Each version entry in the manifest becomes one OKF concept file here at `references/guidelines/<system>/<topic>/<year-or-society>.md`, carrying:

- YAML frontmatter (`type: Clinical Guideline`, society, year, source paths, url)
- Definitions and classifications drawn from the source
- A `Key recommendations` section where each item has a paraphrased claim plus a verbatim `Exact quote` block citing the parsed source
- Algorithm walk-throughs (if/then form), dosing tables, risk scores
- Citation anchors back into the source markdown

## Layout

```
references/
└── guidelines/                       # OKF v0.1 bundle root
    ├── index.md                      # bundle root index (auto-generated)
    ├── <system>/                     # e.g. cardiology, pulmonary, nephrology, ...
    │   ├── index.md                  # system section index (auto-generated)
    │   └── <topic>/                  # e.g. hypertension, asthma, ckd, ...
    │       ├── index.md              # topic-level OKF concept
    │       └── <year>-<society>.md   # per-version OKF concept (one per manifest version)
    └── study-guides/                 # cross-cutting curated lists
        └── highest-yield-named-guidelines.md
```

`index.md` files and the study-guides bundle are also auto-derived from `manifest.yaml`.
