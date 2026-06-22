---
type: Extraction Guide
title: Clinical Practice Guideline Extraction Methodology
description: Working spec for AI agents extracting Anki cloze cards from clinical practice guideline PDFs — what to keep, what to skip, and how to keep hallucinations out.
timestamp: 2026-06-20
---

# Clinical Practice Guideline Extraction Methodology

This is a working spec. The card-generation agent reads a guideline parsed to markdown (LlamaParse output of a PDF in `sources/`) and must produce atomic cloze cards that are faithful, traceable, and edition-correct. Follow the rules below; do not improvise around them.

## 1. Anatomy of a modern CPG

Modern guidelines from major societies (ACC/AHA, ESC, KDIGO, GINA, GOLD, IDSA, USPSTF, AAN) follow a roughly standard skeleton inherited from the IOM *Clinical Practice Guidelines We Can Trust* standards and the AGREE II / RIGHT reporting frameworks. Treat sections as **high-signal** (mine aggressively) or **low-signal** (skim or skip):

| Section                                         | Signal                                                      | Why                                                                                    |
| ----------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Recommendation tables / boxed statements        | HIGH                                                        | The actual claims, with grade + LOE attached.                                          |
| Algorithms / flowcharts                         | HIGH                                                        | Decision logic, thresholds, branch points.                                             |
| Definitions, classification, staging tables     | HIGH                                                        | Cutoffs and categorical thresholds.                                                    |
| Dosing / regimen tables, drug appendices        | HIGH                                                        | Numerical facts.                                                                       |
| Evidence profiles / Summary of Findings (SoF)   | MEDIUM                                                      | Useful to cross-check a recommendation's strength; rarely the source of a card itself. |
| Implementation / quality-measure sections       | MEDIUM                                                      | Sometimes contains an operational threshold.                                           |
| Background / epidemiology / pathophysiology     | LOW                                                         | Often outdated and not the document's purpose.                                         |
| Methods, panel composition, COI, voting         | SKIP                                                        | Process documentation.                                                                 |
| Executive summary                               | SKIP — unless it is the only place a recommendation appears | Usually restates; risks double-extraction.                                             |
| Public-comment responses, appendices of letters | SKIP                                                        | Not normative.                                                                         |

Rule: the recommendation table is the canonical source for a recommendation. If the executive summary and the recommendation table disagree, **the recommendation table wins**.

## 2. Recommendation grading systems

The card text must reflect the *strength* of the recommendation. Map the source's grade to plain language and preserve the grade as metadata.

### GRADE (KDIGO, IDSA, ACP, WHO, ATS, many others)

- **Strength**: Strong ("we recommend") vs Conditional/Weak ("we suggest").
- **Certainty of evidence**: High / Moderate / Low / Very Low.
- Strong recommendations carry "we recommend"; weak/conditional carry "we suggest." Translate exactly that way in card prose.

### ACC/AHA (2015 update, still current framework)

- **Class of Recommendation (COR)**: I (Strong — "is recommended/indicated/useful"), IIa (Moderate — "is reasonable"), IIb (Weak — "may be considered/reasonable"), III-No Benefit ("is not recommended/useful"), III-Harm ("potentially harmful — should not be performed").
- **Level of Evidence (LOE)**: A, B-R (randomized), B-NR (non-randomized), C-LD (limited data), C-EO (expert opinion).

### ESC

- **Class**: I / IIa / IIb / III, same intent as ACC/AHA.
- **LOE**: A (multiple RCTs / meta-analyses), B (single RCT or large non-randomized), C (expert consensus / small studies / registries).

### USPSTF

- **A**: offer / provide (high certainty, substantial net benefit).
- **B**: offer / provide (moderate-to-substantial net benefit).
- **C**: offer selectively based on individual circumstances.
- **D**: recommend against.
- **I**: insufficient evidence — *do not extract as a recommendation* except as "USPSTF concludes evidence is insufficient."

### IDSA (GRADE-based but reported as strength + quality)

- Strong / Weak × High / Moderate / Low / Very Low.

### Strength language → card phrasing

| Source phrase                                                                     | Card phrasing                                            | Do not write                                   |
| --------------------------------------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| "We recommend", "is recommended", "is indicated", COR I, USPSTF A/B, GRADE Strong | "...is recommended..." / "...should..."                  | "may be considered", "can be used"             |
| "We suggest", "is reasonable", COR IIa, GRADE Conditional                         | "...is reasonable..." / "...is suggested..."             | "is recommended", "should"                     |
| "May be considered", COR IIb                                                      | "...may be considered..."                                | "is recommended"                               |
| COR III-No Benefit, USPSTF D, GRADE Strong-against                                | "...is not recommended..."                               | "is contraindicated" (unless source says harm) |
| COR III-Harm                                                                      | "...is potentially harmful / should not be performed..." |                                                |
| USPSTF I                                                                          | Card the *insufficiency*, not a directive.               | Any directive verb.                            |

Strength escalation is the most common hallucination — never upgrade "may be considered" into "is recommended."

## 3. Prioritize for extraction

- **Numerical thresholds**: BP targets, eGFR cutoffs, HbA1c, LDL, ferritin, troponin, age thresholds for screening, time-to-treatment windows.
- **Dosing**: drug, dose, route, frequency, duration, renal/hepatic adjustment, max dose.
- **Decision criteria in algorithms**: "if X then Y" with the exact branch condition.
- **Inclusion / exclusion criteria** for a test or therapy.
- **First-line vs alternatives**; contraindications; red flags / referral triggers.
- **Definitions and classification** (e.g., KDIGO AKI stages, GOLD ABE groups, GINA steps).
- **Risk equations / scores** (PCE, CHA2DS2-VASc, HAS-BLED): name, inputs, threshold for action.
- **Monitoring intervals** (eGFR every X months, mammogram every X years).

## 4. De-prioritize / skip

- COI disclosures, funding statements, panel rosters.
- Lengthy epidemiology, pathophysiology, historical context.
- Methods (search strategy, GRADE process notes) — extract only the grading legend if needed for metadata.
- Executive-summary paraphrases that duplicate a recommendation table.
- "Future research needs" / "gaps in evidence" sections.
- Patient-facing plain-language summaries (use the clinician text for primary extraction).

## 5. Algorithm extraction

Flowcharts are high-value and high-risk — OCR often mangles them.

1. **Locate the figure's caption and any in-text walkthrough.** The narrative usually spells out branch logic the diagram only implies.
1. **Encode node-by-node**: each decision diamond becomes an `if <criterion> then <action> else <action>` card. Preserve exact thresholds.
1. **Do not merge branches.** If "yes" and "no" arrows both point to overlapping next steps, encode both edges.
1. **When the OCR for a figure is garbled**, mark the recommendation `extracted: false` with `reason: figure_ocr_unreadable` and skip rather than guess. Do not infer arrows.
1. **Cross-check with the recommendation table.** If the algorithm contradicts the table, prefer the table and flag the discrepancy in metadata.

## 6. Hallucination-reduction tactics

These are mandatory, not optional.

- **Quote-anchor every claim.** For each card, capture the verbatim source sentence(s) in `exact_quote`. The cloze paraphrase must be derivable from that quote alone, with no outside knowledge.
- **Provenance on every card.** `source_doc`, `section`, `page` (or markdown heading path), `grade`, `strength`. Cards without provenance are invalid.
- **Refuse-to-extract.** If the source does not state X, the card must not assert X. No "common knowledge" backfill. No "this is implied."
- **Recommend vs describe.** Background prose often *describes* current practice ("most clinicians initiate ACEi first") without *recommending* it. Only extract from normative statements (recommendation tables, "we recommend/suggest", numbered guidance).
- **Edition discipline.** The agent must extract only from the PDF in front of it. Do not reconcile against a remembered older edition. The filename and `year` in frontmatter are authoritative.
- **Numerical traps.**
  - Units: mg/dL vs mmol/L (glucose, creatinine, lipids); IU vs mcg (vitamin D); mEq vs mmol.
  - Boundaries: "≥140" ≠ ">140"; "age 40–75" includes both endpoints unless stated.
  - Ranges vs point estimates: "target 7–9%" is not "target 8%."
  - Population qualifiers: "in adults without diabetes" — drop the qualifier and the threshold changes.
- **Negation traps.** "Not recommended" and "recommended against" mean the same thing; "insufficient evidence to recommend" does **not** mean "recommended against."
- **Conditional traps.** "In patients with X, Y is recommended" — the condition must travel with the recommendation in the card stem.

## 7. Common failure modes (with examples)

- **Strength inflation.** Source: "ezetimibe may be considered as add-on to maximally tolerated statin (COR IIb)." Bad card: "Ezetimibe is recommended as add-on to statin." Correct: "Ezetimibe `{{c1::may be considered}}` as add-on to maximally tolerated statin therapy (ACC/AHA COR IIb)."
- **Dropped population.** Source: "In adults aged 40–75 without ASCVD, statin therapy is recommended if 10-yr risk ≥7.5%." Bad card omits the age range or the no-ASCVD qualifier.
- **Unit drift.** Source gives LDL in mmol/L; agent converts to mg/dL without saying so, introducing rounding error.
- **Edition bleed.** Old KDIGO AKI staging used different urine-output windows than the current edition. Agent must use only what the loaded PDF says.
- **Algorithm shortcut.** Agent collapses a 3-step triage algorithm into "start treatment if criteria met," losing the intermediate test.
- **Background-as-recommendation.** A sentence in the pathophys section saying "beta-blockers reduce mortality in HFrEF" is not a recommendation — find the recommendation table entry and cite that instead.
- **Composite endpoints stated as outcomes.** "Reduced MACE" ≠ "reduced mortality." Preserve the exact endpoint.

## 8. Output schema for an extracted recommendation

The card generator reads this. One YAML object per extracted recommendation; one or more cloze cards may be generated per object.

```yaml
- claim: "In adults 40–75 with LDL-C 70–189 mg/dL and 10-yr ASCVD risk >=7.5%, moderate-intensity statin therapy is recommended."
  exact_quote: "In adults 40 to 75 years of age with an LDL-C level of 70 to 189 mg/dL (1.8 to 4.9 mmol/L), a 10-year ASCVD risk of >=7.5% should prompt initiation of a moderate-intensity statin."
  source_doc: "sources/cardiology/2018-aha-acc-cholesterol-guideline.pdf"
  section: "Recommendations for Primary Prevention in Adults 40 to 75 Years"
  page: 1108
  heading_path: ["4. Primary Prevention", "4.4 Adults 40-75 Years"]
  society: "ACC/AHA"
  year: 2018
  grade_system: "ACC/AHA"
  cor: "I"
  loe: "A"
  strength_phrase: "is recommended"
  population:
    age_range: [40, 75]
    inclusion: ["LDL-C 70-189 mg/dL", "10-yr ASCVD risk >=7.5%"]
    exclusion: ["clinical ASCVD", "LDL-C >=190 mg/dL", "diabetes (separate recommendation)"]
  units_canonical: "mg/dL"
  units_source_also: ["mmol/L"]
  numeric_values:
    - {name: "LDL_low", value: 70, unit: "mg/dL", boundary: "inclusive"}
    - {name: "LDL_high", value: 189, unit: "mg/dL", boundary: "inclusive"}
    - {name: "ASCVD_risk", value: 7.5, unit: "%", boundary: ">="}
  card_eligible: true
  notes: ""
```

Required keys: `claim`, `exact_quote`, `source_doc`, `section`, `page`, `society`, `year`, `grade_system`, `strength_phrase`, `card_eligible`. If a required field cannot be filled from the source, set `card_eligible: false` and write the reason in `notes` instead of guessing.

## 9. Agent contract (one-paragraph summary)

You are extracting from a single PDF parsed to markdown. Every card you emit must be traceable to a verbatim quote in that file, must preserve the source's strength language and numerical boundaries, and must carry provenance and grade metadata. When in doubt, do not extract. The deck would rather be missing a card than wrong about one.

# Citations

1. GRADE Working Group — *Handbook for grading the quality of evidence and the strength of recommendations using the GRADE approach* — [gdt.gradepro.org/app/handbook/handbook.html](https://gdt.gradepro.org/app/handbook/handbook.html)
1. AGREE Next Steps Consortium — *AGREE II Instrument* (2010, current) — [agreetrust.org/agree-ii](https://www.agreetrust.org/agree-ii/)
1. Institute of Medicine — *Clinical Practice Guidelines We Can Trust* (National Academies, 2011) — [nationalacademies.org/our-work/standards-for-developing-trustworthy-clinical-practice-guidelines](https://www.nationalacademies.org/our-work/standards-for-developing-trustworthy-clinical-practice-guidelines)
1. ACC/AHA Joint Committee on Clinical Practice Guidelines — *Methodology Manual and Policies* — [acc.org/Guidelines/About-Guidelines-and-Clinical-Documents/Methodology](https://www.acc.org/Guidelines/About-Guidelines-and-Clinical-Documents/Methodology)
1. Halperin JL et al. — *ACC/AHA 2015 Update on the Clinical Practice Guideline Recommendation Classification System* — Circulation, doi:[10.1161/CIR.0000000000000312](https://doi.org/10.1161/CIR.0000000000000312)
1. U.S. Preventive Services Task Force — *Grade Definitions* — [uspreventiveservicestaskforce.org/uspstf/about-uspstf/methods-and-processes/grade-definitions](https://www.uspreventiveservicestaskforce.org/uspstf/about-uspstf/methods-and-processes/grade-definitions)
1. Infectious Diseases Society of America — *Clinical Practice Guidelines Development, Training, and Resources* — [idsociety.org/practice-guideline/clinical-practice-guidelines-development-training-and-resources](https://www.idsociety.org/practice-guideline/clinical-practice-guidelines-development-training-and-resources/)
1. European Society of Cardiology — *ESC Clinical Practice Guidelines* — [escardio.org/Guidelines](https://www.escardio.org/Guidelines)
1. Higgins JPT, Thomas J, et al. (eds) — *Cochrane Handbook for Systematic Reviews of Interventions* (current version) — [cochrane.org/authors/handbooks-and-manuals/handbook/current](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current)
1. Alonso-Coello P et al. — *GRADE Evidence to Decision (EtD) frameworks: a systematic and transparent approach to making well informed healthcare choices* — BMJ 2016;353:i2016 / i2089, doi:[10.1136/bmj.i2016](https://doi.org/10.1136/bmj.i2016)
1. Chen Y, Yang K, Marušić A, et al. — *A Reporting Tool for Practice Guidelines in Health Care: The RIGHT Statement* — Ann Intern Med 2017, doi:[10.7326/M16-1565](https://doi.org/10.7326/M16-1565); project site [right-statement.org](http://www.right-statement.org/)
1. Guyatt GH et al. — *GRADE: an emerging consensus on rating quality of evidence and strength of recommendations* — BMJ 2008;336:924, doi:[10.1136/bmj.39489.470347.AD](https://doi.org/10.1136/bmj.39489.470347.AD)
1. AHRQ Effective Health Care Program — *Methods Guide for Effectiveness and Comparative Effectiveness Reviews* — [effectivehealthcare.ahrq.gov/products/collections/cer-methods-guide](https://effectivehealthcare.ahrq.gov/products/collections/cer-methods-guide)
