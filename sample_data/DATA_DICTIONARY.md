# fec_matches_sample.csv: Data Dictionary

500 synthetic rows: 340 new matches and 160 previous matches, the same split and tier mix as the real delivery. **Every name, address, employer, state and amount is fake.** New-match scores and explanations come from [`src/scoring.py`](../src/scoring.py).

| Column | Description |
|---|---|
| record_id | Synthetic ID |
| match_status | `New match` (national, 2022–2026) or `Previous match` (earlier regional match kept for lifetime totals) |
| confidence_level / confidence_score | Very High / High / Medium and the 0–100 score (blank for previous matches) |
| prospect_name / fec_donor_name | Name in the prospect database vs as filed with the FEC (nicknames and initials included) |
| state | Prospect state |
| geographic_match | Location evidence in words (street + ZIP / city / state) |
| name_rarity | 1 (very common) – 5 (likely unique in the US) |
| competing_fec_identities | Other plausible FEC donors for this person |
| spouse_also_fec_donor | Yes / No / n/a (no spouse on file) |
| fec_occupation / fec_employer | As reported to the FEC |
| fec_giving_bin / fec_total_2022_2026 | Total given in 2022–2026, after removing conduit duplicates |
| fec_gift_count / fec_last_gift | Number of gifts and the most recent date |
| largest_gift_recipient | Committee type of the largest gift |
| prospect_street / fec_street | Best-matching prospect address vs FEC street |
| address_match_result | same_exact, same_variant, near, same_street, po_same, different, not_comparable |
| match_explanation | Point-by-point chain behind the score |
| previous_fec_bin / previous_lifetime_total | Lifetime totals carried by previous matches |
