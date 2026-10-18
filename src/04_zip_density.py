# Step 4: expected same-name people inside the prospect's ZIP.
# A ZIP match on a rare name in a small ZIP is strong evidence; a common name in a dense ZIP is not.
import duckdb

con = duckdb.connect("fec.duckdb")
con.execute("""
CREATE OR REPLACE TABLE zip_density AS
SELECT a.person_id, a.zip5, z.population,
       r.est_bearers * z.population / 335e6 AS expected_same_name,
       CASE WHEN expected_same_name < 0.01 THEN 1
            WHEN expected_same_name < 0.1  THEN 2
            WHEN expected_same_name < 0.5  THEN 3
            WHEN expected_same_name < 2    THEN 4
            ELSE 5 END                      AS zip_density_score
FROM prospect_addresses a
JOIN name_rarity r USING (person_id)
JOIN read_csv_auto('ref/uszips.csv') z ON lpad(z.zip::VARCHAR, 5, '0') = a.zip5
""")
