# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///
"""Move manually-downloaded PDFs from tmp/ into sources/ and update manifest.

Edit the IMPORTS list at the top with tuples of:
    (src_filename, system, topic, year_or_None, society_or_None)

- `year=None` indicates a living / non-versioned entry.
- `society` is OPTIONAL — required only when multiple versions on the same topic
  share the same year (or when the topic has no year at all and multiple living
  entries). It matches against the version's society or the topic-level society
  if the version doesn't override.

For each imported PDF:
  - move tmp/<src> → sources/<system>/<topic>/<year>-<society>.pdf (or <society>.pdf for living)
  - set `source: /sources/...` on the matching version entry
  - remove `needs_attention:` on that entry

After running, the validator hook reruns automatically and
`uv run scripts/needs_attention_report.py` regenerates the open-items list.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
TMP = REPO / "tmp"
SOURCES = REPO / "sources"
MANIFEST = REPO / "manifest.yaml"

Import = tuple[str, str, str, Optional[int], Optional[str]]

# (src_filename, system, topic, year_or_None, society_or_None)
IMPORTS: list[Import] = [
    # === Re-download fixes for needs-attention entries (PDFs) ===
    ("breast-cancer-screening-final-rec.pdf",     "preventive-medicine", "breast-cancer-screening", 2024, "USPSTF"),
    ("jcem_105_3_587.pdf",                         "endocrinology", "osteoporosis", 2020, "Endocrine Society"),
    ("PIIS0002934313006050.pdf",                   "nephrology", "hyponatremia", 2013, "US expert panel"),
    ("PIIS0016508520348472.pdf",                   "hematology-oncology", "ida-gi-evaluation", 2020, "AGA"),
    ("PIIS0016508522010265.pdf",                   "endocrinology", "obesity", 2022, "AGA"),
    ("PIIS1470204522001607.pdf",                   "hematology-oncology", "cancer-associated-thrombosis", 2022, "ITAC"),
    # === ASH sickle-cell pocket guide series — primary file (the others are mv'd manually) ===
    ("Watermark ASH SCD CPKD Pocket Guide.pdf",   "hematology-oncology", "sickle-cell", 2020, "ASH"),
    # === Earlier batches (already imported — will report missing tmp source; safe to ignore) ===
    # --- EPUB batch — AHA cardiology (17) ---
    ("whelton-et-al-2017-2017-acc-aha-aapa-abc-acpm-ags-apha-ash-aspc-nma-pcna-guideline-for-the-prevention-detection.epub",
     "cardiology", "hypertension", 2017, None),
    ("jones-et-al-2025-2025-aha-acc-aanp-aapa-abc-accp-acpm-ags-ama-aspc-nma-pcna-sgim-guideline-for-the-prevention-detection.epub",
     "cardiology", "hypertension", 2025, None),
    ("grundy-et-al-2018-2018-aha-acc-aacvpr-aapa-abc-acpm-ada-ags-apha-aspc-nla-pcna-guideline-on-the-management-of-blood.epub",
     "cardiology", "dyslipidemia", 2018, None),
    ("blumenthal-et-al-2026-2026-acc-aha-aacvpr-abc-acpm-ada-ags-apha-aspc-nla-pcna-guideline-on-the-management-of.epub",
     "cardiology", "dyslipidemia", 2026, None),
    ("rao-et-al-2025-2025-acc-aha-acep-naemsp-scai-guideline-for-the-management-of-patients-with-acute-coronary-syndromes-a.epub",
     "cardiology", "acs", 2025, None),
    ("virani-et-al-2023-2023-aha-acc-accp-aspc-nla-pcna-guideline-for-the-management-of-patients-with-chronic-coronary.epub",
     "cardiology", "chronic-coronary-disease", 2023, None),
    ("heidenreich-et-al-2022-2022-aha-acc-hfsa-guideline-for-the-management-of-heart-failure-a-report-of-the-american-college.epub",
     "cardiology", "heart-failure", 2022, None),
    ("joglar-et-al-2023-2023-acc-aha-accp-hrs-guideline-for-the-diagnosis-and-management-of-atrial-fibrillation-a-report-of.epub",
     "cardiology", "atrial-fibrillation", 2023, None),
    ("gulati-et-al-2021-2021-aha-acc-ase-chest-saem-scct-scmr-guideline-for-the-evaluation-and-diagnosis-of-chest-pain-a.epub",
     "cardiology", "chest-pain", 2021, None),
    ("lawton-et-al-2021-2021-acc-aha-scai-guideline-for-coronary-artery-revascularization-a-report-of-the-american-college-of.epub",
     "cardiology", "coronary-revascularization", 2021, None),
    ("otto-et-al-2020-2020-acc-aha-guideline-for-the-management-of-patients-with-valvular-heart-disease-a-report-of-the.epub",
     "cardiology", "valvular-heart-disease", 2020, None),
    ("arnett-et-al-2019-2019-acc-aha-guideline-on-the-primary-prevention-of-cardiovascular-disease-a-report-of-the-american.epub",
     "cardiology", "primary-prevention-cvd", 2019, None),
    ("gornik-et-al-2024-2024-acc-aha-aacvpr-apma-abc-scai-svm-svn-svs-sir-vess-guideline-for-the-management-of-lower.epub",
     "cardiology", "peripheral-artery-disease", 2024, None),
    ("isselbacher-et-al-2022-2022-acc-aha-guideline-for-the-diagnosis-and-management-of-aortic-disease-a-report-of-the.epub",
     "cardiology", "thoracic-aortic-disease", 2022, None),
    ("kusumoto-et-al-2018-2018-acc-aha-hrs-guideline-on-the-evaluation-and-management-of-patients-with-bradycardia-and.epub",
     "cardiology", "bradycardia", 2018, None),
    ("al-khatib-et-al-2018-2017-aha-acc-hrs-guideline-for-management-of-patients-with-ventricular-arrhythmias-and-the.epub",
     "cardiology", "ventricular-arrhythmias", 2017, None),
    ("shen-et-al-2017-2017-acc-aha-hrs-guideline-for-the-evaluation-and-management-of-patients-with-syncope-a-report-of-the.epub",
     "cardiology", "syncope", 2017, None),
    # === EPUB batch — AHA/ASA neurology (5) ===
    ("prabhakaran-et-al-2026-2026-guideline-for-the-early-management-of-patients-with-acute-ischemic-stroke-a-guideline-from.epub",
     "neurology", "acute-ischemic-stroke", 2026, None),
    ("powers-et-al-2019-guidelines-for-the-early-management-of-patients-with-acute-ischemic-stroke-2019-update-to-the-2018.epub",
     "neurology", "acute-ischemic-stroke", 2019, None),
    ("powers-et-al-2018-2018-guidelines-for-the-early-management-of-patients-with-acute-ischemic-stroke-a-guideline-for.epub",
     "neurology", "acute-ischemic-stroke", 2018, None),
    ("kleindorfer-et-al-2021-2021-guideline-for-the-prevention-of-stroke-in-patients-with-stroke-and-transient-ischemic.epub",
     "neurology", "secondary-stroke-prevention", 2021, None),
    ("greenberg-et-al-2022-2022-guideline-for-the-management-of-patients-with-spontaneous-intracerebral-hemorrhage-a.epub",
     "neurology", "ich", 2022, None),
    # === EPUB batch — infectious diseases (AHA IE) ===
    ("baddour-et-al-2023-nondental-invasive-procedures-and-risk-of-infective-endocarditis-time-for-a-revisit-a-science.epub",
     "infectious-diseases", "infective-endocarditis", 2023, "AHA"),
    ("baddour-et-al-2015-infective-endocarditis-in-adults-diagnosis-antimicrobial-therapy-and-management-of-complications.epub",
     "infectious-diseases", "infective-endocarditis", 2015, "AHA"),
    # === EPUB batch — pulmonary ===
    ("Surviving_Sepsis_Campaign__International.epub",
     "pulmonary", "sepsis", 2021, None),
    # === EPUB batch — endocrinology (ATA) ===
    ("ross-et-al-2016-2016-american-thyroid-association-guidelines-for-diagnosis-and-management-of-hyperthyroidism-and-other.epub",
     "endocrinology", "hyperthyroidism", 2016, None),
    ("jonklaas-et-al-2014-guidelines-for-the-treatment-of-hypothyroidism-prepared-by-the-american-thyroid-association-task.epub",
     "endocrinology", "hypothyroidism", 2014, None),
    ("haugen-et-al-2015-2015-american-thyroid-association-management-guidelines-for-adult-patients-with-thyroid-nodules-and.epub",
     "endocrinology", "thyroid-nodules", 2015, None),
    # === EPUB batch — gi-hepatology ACG (10) ===
    ("ACG_Clinical_Guideline_for_the_Diagnosis_and.epub",            "gi-hepatology", "gerd", 2022, None),
    ("ACG_Clinical_Guideline__Treatment_of_Helicobacter.epub",        "gi-hepatology", "h-pylori", 2024, None),
    ("American_College_of_Gastroenterology_Guidelines_.epub",          "gi-hepatology", "acute-pancreatitis", 2024, None),
    ("ACG_Clinical_Guidelines__Prevention__Diagnosis_.epub",          "gi-hepatology", "c-difficile", 2021, "ACG"),
    ("ACG_Clinical_Guideline_Update__Ulcerative_Colitis.epub",        "gi-hepatology", "ulcerative-colitis", 2025, None),
    ("ACG_Clinical_Guideline__Ulcerative_Colitis_in.epub",            "gi-hepatology", "ulcerative-colitis", 2019, None),
    ("ACG_Clinical_Guideline__Management_of_Crohn_s.epub",            "gi-hepatology", "crohns", 2018, None),
    ("ACG_Clinical_Guideline__Upper_Gastrointestinal_and.epub",       "gi-hepatology", "upper-gi-bleeding", 2021, None),
    ("ACG_Clinical_Guideline__Management_of_Irritable.epub",          "gi-hepatology", "ibs", 2021, None),
    ("American_College_of_Gastroenterology_Guidelines.epub",           "gi-hepatology", "celiac", 2023, None),
    # === EPUB batch — gi-hepatology AASLD (3) ===
    ("AASLD_Practice_Guidance_on_prevention__diagnosis_.epub",        "gi-hepatology", "hcc", 2023, None),
    ("AASLD_Practice_Guidance_on_risk_stratification_and.epub",       "gi-hepatology", "portal-hypertension", 2024, "AASLD"),
    ("AASLD_Practice_Guidance_on_the_clinical_assessment.epub",       "gi-hepatology", "masld", 2023, None),
    # === Prior batches (already imported — will report missing tmp source) ===
    # --- ATS replacement PDFs (post-Oxford migration paths) ---
    ("ajrccm_200_7_e45.pdf",   "pulmonary", "cap", 2019, None),
    ("ajrccm_205_9_e18.pdf",   "pulmonary", "ipf", 2022, None),
    # --- Hyponatremia: JASN review (replaces inaccessible 2014 European primary) ---
    ("ASN.2016101139.pdf",     "nephrology", "hyponatremia", 2017, "JASN"),
    # --- previous batch (already imported; will report missing tmp source — safe to ignore) ---
    # --- USPSTF (preventive-medicine) ---
    ("cervical-cancer-final-rec-statement.pdf",                       "preventive-medicine", "cervical-cancer-screening", 2024, None),
    ("colorectal-cancer-screening-final-recommendation-updated.pdf",  "preventive-medicine", "colorectal-cancer-screening", 2021, None),
    ("depression-suicide-risk-adults-rs.pdf",                         "preventive-medicine", "depression-anxiety-screening", 2023, None),
    ("lung-cancer-screening-final-recommendation.pdf",                "preventive-medicine", "lung-cancer-screening", 2021, None),
    ("prostate-cancer-final-rec-statement-051418.pdf",                "preventive-medicine", "prostate-cancer-screening", 2018, None),
    ("statin-use-cvd-prevention-final-rec-statement.pdf",             "preventive-medicine", "statins-primary-prevention", 2022, "USPSTF"),
    ("tobacco-cessation-adults-final-rec-statement.pdf",              "preventive-medicine", "tobacco-cessation", 2021, None),
    # --- ESC / Oxford Academic (Eur Heart J) ---
    ("ehac237.pdf",    "pulmonary", "pulmonary-hypertension", 2022, None),
    ("ehad193.pdf",    "infectious-diseases", "infective-endocarditis", 2023, "ESC"),
    ("ehz405.pdf",     "pulmonary", "pe-vte-acute", 2019, None),
    # --- ATS CAP 2025 ---
    ("rccm.202507-1692st.pdf", "pulmonary", "cap", 2025, None),
    # --- IDSA / Clinical Infectious Diseases ---
    ("ciu296.pdf",     "infectious-diseases", "ssti", 2014, None),
    ("ciw118.pdf",     "infectious-diseases", "antimicrobial-stewardship", 2016, None),
    ("ciw376.pdf",     "infectious-diseases", "tuberculosis", 2016, None),
    ("civ933.pdf",     "infectious-diseases", "candidiasis", 2016, None),
    ("ciq257.pdf",     "infectious-diseases", "uti", 2011, None),
    ("ciad271.pdf",    "infectious-diseases", "infective-endocarditis", 2023, "Duke-ISCVID"),
    # --- ESICM ARDS (ICM = Springer journal 134) ---
    ("134_2023_Article_7050.pdf", "pulmonary", "ards", 2023, None),
    # --- Neurocritical Care Society status epilepticus (living, no year) ---
    ("s12028-012-9695-z.pdf",      "neurology", "status-epilepticus", None, "Neurocritical Care Society"),
    # --- Surviving Sepsis Campaign 2021 ---
    ("surviving_sepsis_campaign__international.21.pdf", "pulmonary", "sepsis", 2021, None),
    # --- Rheum / Neuro / ID misc ---
    ("Arthritis   Rheumatology - 2015 - Dejaco - 2015 Recommendations for the Management of Polymyalgia Rheumatica  A European.pdf",
     "rheumatology", "polymyalgia-rheumatica", 2015, None),
    ("Headache - 2021 - Ailani - The American Headache Society Consensus Statement  Update on integrating new migraine treatments.pdf",
     "neurology", "migraine", 2021, None),
    ("baddour-et-al-2023-nondental-invasive-procedures-and-risk-of-infective-endocarditis-time-for-a-revisit-a-science.pdf",
     "infectious-diseases", "infective-endocarditis", 2023, "AHA"),
    ("jama_gandhi_2024_sc_240017_1738864635.61227.pdf",
     "infectious-diseases", "hiv", 2024, None),
    ("krumholz-et-al-2015-evidence-based-guideline-management-of-an-unprovoked-first-seizure-in-adults.pdf",
     "neurology", "epilepsy", None, "AAN/AES"),
    ("PIIS0091674920314044.pdf",   "pulmonary", "asthma", 2020, None),
    ("rae-grant-et-al-2018-practice-guideline-recommendations-summary-disease-modifying-therapies-for-adults-with-multiple.pdf",
     "neurology", "multiple-sclerosis", 2018, None),
]

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


def slug(s: str) -> str:
    return (
        s.lower()
        .replace("/", "-")
        .replace(" ", "-")
        .replace(".", "")
        .replace("&", "and")
    )


def filename_for(year, society, ext="pdf"):
    if year is None and society:
        return f"{slug(society)}.{ext}"
    if society and year:
        return f"{year}-{slug(society)}.{ext}"
    if year:
        return f"{year}.{ext}"
    return f"guideline.{ext}"


def find_version(manifest, system, topic, year, society):
    sys_block = manifest.get("systems", {}).get(system)
    if not sys_block:
        return None, None
    topic_block = sys_block.get("topics", {}).get(topic)
    if not topic_block:
        return None, None
    topic_society = topic_block.get("society")
    matches = []
    for v in topic_block.get("versions", []):
        if v.get("year") != year:
            continue
        if society is not None:
            v_society = v.get("society") or topic_society
            if v_society != society:
                continue
        matches.append(v)
    if len(matches) == 1:
        return matches[0], topic_society
    if len(matches) > 1:
        return "ambiguous", topic_society
    return None, topic_society


def main():
    with MANIFEST.open() as f:
        manifest = yaml.load(f)

    moved = 0
    errors: list[str] = []

    for src_name, system, topic, year, society_hint in IMPORTS:
        src = TMP / src_name
        if not src.exists():
            errors.append(f"missing tmp source: {src_name}")
            continue

        version, topic_society = find_version(manifest, system, topic, year, society_hint)
        if version is None:
            errors.append(f"manifest entry not found: {system}/{topic}/{year}/{society_hint}")
            continue
        if version == "ambiguous":
            errors.append(f"ambiguous match: {system}/{topic}/{year} — add society")
            continue

        society = version.get("society") or topic_society
        ext = src.suffix.lstrip(".").lower() or "pdf"
        fname = filename_for(year, society, ext)
        dest = SOURCES / system / topic / fname
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        rel = dest.relative_to(REPO)
        ext = dest.suffix.lstrip(".").lower() or "unknown"
        if not isinstance(version.get("source"), dict):
            version["source"] = {}
        version["source"].setdefault(ext, {})["local"] = f"/{rel}"
        if "needs_attention" in version:
            del version["needs_attention"]
        moved += 1
        print(f"  {src_name}  →  {rel}")

    with MANIFEST.open("w") as f:
        yaml.dump(manifest, f)

    print(f"\nmoved {moved} file(s)")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
