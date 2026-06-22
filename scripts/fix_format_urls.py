# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Two cleanups on manifest source URLs:

1. Atypon DOI base URLs (`/doi/<DOI>` on ascopubs/ahajournals/ashpublications/
   neurology/diabetesjournals/etc.) → explicitly set:
       source.html.url = .../doi/full/<DOI>
       source.pdf.url  = .../doi/pdf/<DOI>
   when those format keys exist but have no `url`. Also overwrite a `url` that
   is just the DOI base with the explicit `/full/` variant for `source.html`.

2. Fix double-prefixed PMC URLs of the form
   `https://pmc.ncbi.nlm.nih.gov/articles/https://pmc.ncbi.nlm.nih.gov/articles/PMC.../`
"""

from __future__ import annotations

import re
from pathlib import Path
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "manifest.yaml"

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096

ATYPON_HOSTS = (
    "ahajournals.org",
    "ascopubs.org",
    "ashpublications.org",
    "neurology.org",
    "diabetesjournals.org",
    "acpjournals.org",
)

# Matches https://host/doi/<DOI> (not /doi/full/, /doi/pdf/, /doi/epub/, /doi/reader/, /doi/abs/)
DOI_BASE_RE = re.compile(
    r"^(?P<scheme_host>https?://[^/]+)/doi/(?!full/|pdf/|epub/|reader/|abs/|epdf/)(?P<doi>.+)$"
)


def is_atypon(url: str) -> bool:
    return any(h in url for h in ATYPON_HOSTS)


def to_full(url: str) -> str | None:
    m = DOI_BASE_RE.match(url)
    if not m or not is_atypon(url):
        return None
    return f"{m['scheme_host']}/doi/full/{m['doi']}"


def to_pdf_url(url: str) -> str | None:
    m = DOI_BASE_RE.match(url)
    if not m or not is_atypon(url):
        return None
    return f"{m['scheme_host']}/doi/pdf/{m['doi']}"


PMC_DOUBLE = re.compile(
    r"https?://pmc\.ncbi\.nlm\.nih\.gov/articles/(https?://[^/]+/articles/)?(PMC\d+)/?/?"
)


def fix_pmc(url: str) -> str:
    m = PMC_DOUBLE.match(url)
    if not m:
        return url
    return f"https://pmc.ncbi.nlm.nih.gov/articles/{m.group(2)}/"


def iter_versions(manifest):
    for s, sb in manifest.get("systems", {}).items():
        for t, tb in sb.get("topics", {}).items():
            for v in tb.get("versions", []):
                yield s, t, v


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)

    n_full = 0
    n_pdf = 0
    n_pmc_fixed = 0

    for _, _, v in iter_versions(manifest):
        src = v.get("source") or {}
        if not isinstance(src, dict):
            continue

        # 1a. Promote html.url from DOI base → /doi/full/<DOI>
        html_entry = src.get("html")
        if isinstance(html_entry, dict) and html_entry.get("url"):
            full = to_full(html_entry["url"])
            if full and html_entry["url"] != full:
                html_entry["url"] = full
                n_full += 1

        # 1b. Add pdf.url from DOI base when format entry has no url
        pdf_entry = src.get("pdf")
        if isinstance(pdf_entry, dict) and not pdf_entry.get("url"):
            # Try to derive from the top-level url field
            top = v.get("url")
            if top:
                pdf_url = to_pdf_url(top)
                if pdf_url:
                    pdf_entry["url"] = pdf_url
                    n_pdf += 1

        # 2. Fix PMC double-prefix
        pmc_entry = src.get("pmc")
        if isinstance(pmc_entry, dict) and pmc_entry.get("url"):
            fixed = fix_pmc(pmc_entry["url"])
            if fixed != pmc_entry["url"]:
                pmc_entry["url"] = fixed
                n_pmc_fixed += 1

    with MANIFEST.open("w") as f:
        yaml.dump(manifest, f)

    print(f"html.url promoted to /doi/full/ : {n_full}")
    print(f"pdf.url filled from DOI base    : {n_pdf}")
    print(f"PMC URLs un-double-prefixed     : {n_pmc_fixed}")


if __name__ == "__main__":
    main()
