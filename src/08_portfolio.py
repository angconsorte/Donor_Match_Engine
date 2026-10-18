# Step 8: add matches to the portfolio. New matches enter at 45+;
# previous matches are never overwritten because they carry lifetime totals.
import duckdb

con = duckdb.connect("fec.duckdb")
con.execute("""
CREATE OR REPLACE TABLE portfolio_fec AS
SELECT person_id, 'Previous match' AS match_status, NULL AS confidence_level,
       last_gift, lifetime_total AS total_given
FROM previous_matches
UNION ALL
SELECT b.person_id, 'New match', b.level, f.last_gift, f.total_given
FROM best_matches b JOIN fec_identities f USING (fec_id)
WHERE b.score >= 45
  AND b.person_id NOT IN (SELECT person_id FROM previous_matches)
""")
con.execute("COPY portfolio_fec TO 'output/portfolio_fec_columns.csv' (HEADER)")
print(con.execute("SELECT match_status, count(*) FROM portfolio_fec GROUP BY ALL").fetchall())
