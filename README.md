# Donor Match Engine

**Matching a university's prospect database to federal political donations to find who gives, how much, and how confident we are that it's the same person.**

This is client work I did for my company, a fundraising analytics firm, for a large university client. The final result added **~5,000 FEC-matched records to a ~35,000-record prospect portfolio**, and I presented the method and results to the client's advancement team.

> **Confidentiality note:** Everything in this repo is representative, not real. The code mirrors the production logic, and the sample data is synthetic: fake names, addresses, employers, states and amounts, generated to match the real distributions. No client or donor information is included.

---

## The problem
Political giving is a public signal of capacity and engagement. The client already had FEC matches, but they were:
- **Regional:** one state only
- **Name-only:** first + last + city, with no ZIP or address check
- **Undocumented:** with possible double-counting of conduit gifts (ActBlue/WinRed)

I rebuilt it as a **national** match with a **0–100 confidence score** that reflects how strong the evidence actually is.

## The pipeline
```
FEC bulk files (2022–2026)  →  clean + dedupe  →  donor identities (6.5M)
                                                          │
552K prospects × 4 address blocks  →  candidate pairs  →  score 0–100  →  portfolio (45+)
                                                          │
                                       FEC API street addresses (rescoring)
```

## The scoring algorithm (the fun part)
Each candidate pair is scored on how unlikely it is to be a coincidence:

| Signal | Points | Idea |
|---|---|---|
| Name match | up to 29.4 | First, middle, last, suffix; nicknames accepted (Mike = Michael) |
| Name rarity | up to 23.5 | Census surnames × SSA first names → how many people in the US share this name |
| ZIP match | 35.3 / 31.8 | Prospect ZIP vs most recent / earlier FEC ZIP |
| City / state | up to 11.8 | Backup location check |
| Spouse bonus | +8 | Spouse is also an FEC donor at the same ZIP |
| Competing identities | −2 to −3 | Other plausible FEC donors for the same person |
| Street address | −30 to +18 | Fuzzy-matched against all four prospect addresses |

**Levels:** Very High 75+ · High 60–74 · Medium 45–59 · Low <45. Only 45+ enters the portfolio.

### How it evolved
1. **Reverse-engineered the old match.** Documented its rules and found the gaps (one state, name-only, no conduit filtering).
2. **v1, national baseline.** DuckDB pipeline over 150M+ FEC rows with name, rarity, ZIP density, spouse and collision logic. I caught two counting bugs that had overstated giving by ~46%.
3. **v2, street-address rescoring.** The bulk files have no street, so I pulled addresses from the FEC API and fuzzy-matched them, handling abbreviations, typos, one-digit house numbers and PO boxes. A verified same-address match is floored at 85; a conflicting address can subtract up to 30.
4. **v3, edge cases from review.** Maiden names as a soft middle-name conflict, a stray "M" middle initial ignored, and hard conflicts (name, suffix, state, age) capped at Low unless a ZIP agrees.

Every match carries a plain-English **explanation chain**, so a fundraiser can see why it scored the way it did:
> name 20 (middle on one side) + rarity 3/5 9.4 + ZIP 35.3 + city/state 11.8 + spouse 8 − collision 3 = baseline 81.5; street same address +18 → **99.5 (Very High)**

## Results
| | |
|---|---|
| Prospects scanned | 552,000 |
| National FEC donor identities | 6.5M |
| Candidate pairs scored | ~170,000 |
| Records added to the portfolio | **~5,000** (3,402 new + 1,601 previous) |
| New matches rated Very High | 93% |

## Stack
Python · DuckDB · pandas · FEC API · Google Colab · Google Cloud Storage

**AI-assisted:** I used **Claude Code** and AI agents to scaffold and iterate on the pipeline stage by stage, then validated every step myself with row counts, regression checks against the old matches, and a stratified manual review against FEC.gov.

## Repo
| Path | What's inside |
|---|---|
| `src/` | Pipeline steps `01`–`08` and `scoring.py` (run `python src/scoring.py` for a worked example) |
| `sample_data/` | 500-row **synthetic** snapshot of the final match table + data dictionary |
| `docs/` | Project presentation (PDF) and scoring methodology |
| `tools/` | Generator for the synthetic sample |

**Run it:** `pip install -r requirements.txt`, then `python src/scoring.py` (worked example) or `python tools/make_synthetic_sample.py` (rebuilds the sample). Steps `01`–`08` show the production pipeline; they need the FEC bulk files and a private prospect table, so they don't run as-is.

*Everything here is representative of work done for my company. All data is synthetic, and client and donor information is withheld.*
