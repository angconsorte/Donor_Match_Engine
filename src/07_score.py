# Step 7: score every candidate pair with scoring.py and keep each prospect's best match.
import duckdb
import pandas as pd
from scoring import Candidate, Person, score_candidate

con = duckdb.connect("fec.duckdb")
pairs = con.execute("SELECT * FROM candidate_features").df()   # one row per pair, built from steps 3-6

def to_candidate(r):
    return Candidate(
        prospect=Person(r.first, r.last, r.middle, r.suffix),
        fec=Person(r.fec_first, r.fec_last, r.fec_middle, r.fec_suffix),
        name_rarity=r.rarity, zip_match=r.zip_match, geo_match=r.geo_match,
        spouse_gives_same_zip=r.spouse_same_zip, competing_identities=r.competing_ids,
        prospect_streets=list(r.prospect_streets), fec_street=r.fec_street or "",
        fec_is_office=r.fec_is_office, last_gift=r.last_gift)

results = pd.DataFrame([score_candidate(to_candidate(r)) for r in pairs.itertuples()])
scored = pd.concat([pairs, results], axis=1)
best = scored.sort_values("score", ascending=False).drop_duplicates("person_id")
con.execute("CREATE OR REPLACE TABLE best_matches AS SELECT * FROM best")
print(best.level.value_counts())
