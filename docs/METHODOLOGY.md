# Scoring Methodology

**Score (0–100) = baseline + street points**, capped at 100. Reference code: [`src/scoring.py`](../src/scoring.py).

## Baseline
| Component | Points |
|---|---|
| Name: first, middle, last all agree | 29.4 |
| Name: middle initial agrees | 25.9 |
| Name: no middle on either side | 21.2 |
| Name: middle on one side only / possible maiden name | 20.0 |
| Nickname accepted (Mike = Michael) | −2.35 |
| Name rarity 1–5 | 0 / 4.7 / 9.4 / 16.5 / 23.5 |
| ZIP: most recent FEC ZIP / earlier FEC ZIP | 35.3 / 31.8 |
| City + state / state only | 11.8 / 4.7 |
| Spouse also gives at the same ZIP | +8 |
| Competing FEC identities (1 / 2+) | −2 / −3 |

## Street points
The FEC street is compared with every prospect address (contact, home, seasonal, business) after normalizing abbreviations, directions, units and PO-box spellings. The best result is used.

| Result | Points |
|---|---|
| Same address / spelling variant | +18 / +15 |
| Near match (one digit off, suffix or direction differs) | +10 |
| Same street, different house # | +4 |
| PO box same / different | +10 / −5 |
| Different address (worse for common names and recent gifts) | −9 to −30 |
| Not comparable | 0 |

Positive points are reduced for office addresses (×0.6) and name-only FEC rows (×0.5). A different address counts less when the gift is old, the address is an office, or the row is unverified. **A verified same address is floored at 85.**

## Guardrails
- Hard conflicts (first name, middle, suffix, state, age) cap the score at 44 unless a ZIP agrees.
- A stray FEC middle initial "M" is ignored.
- Previous matches are never overwritten, because they carry lifetime totals while new data covers 2022–2026.

## Levels
Very High ≥75 · High 60–74 · Medium 45–59 · Low <45. Portfolio inclusion: 45+.
