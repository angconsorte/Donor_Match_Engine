# Step 3: how many people in the US share each prospect's name?
# Estimated bearers = US population x P(first name, SSA) x P(last name, Census).
import duckdb

con = duckdb.connect("fec.duckdb")
con.execute("""
CREATE OR REPLACE TABLE p_last AS
SELECT upper(name) AS last, TRY_CAST(prop100k AS DOUBLE) / 1e5 AS p
FROM read_csv_auto('ref/census_surnames_2010.csv');

CREATE OR REPLACE TABLE p_first AS
SELECT upper(name) AS first, sum(cnt) / sum(sum(cnt)) OVER () AS p
FROM read_csv('ref/ssa/yob*.txt', columns={'name': 'VARCHAR', 'sex': 'VARCHAR', 'cnt': 'BIGINT'})
GROUP BY 1;

CREATE OR REPLACE TABLE name_rarity AS
SELECT pr.person_id,
       335e6 * coalesce(f.p, 1e-6) * coalesce(l.p, 1e-6) AS est_bearers,
       CASE WHEN est_bearers < 1    THEN 5     -- likely the only one in the US
            WHEN est_bearers < 10   THEN 4
            WHEN est_bearers < 100  THEN 3
            WHEN est_bearers < 1000 THEN 2
            ELSE 1 END                          AS rarity
FROM prospects pr
LEFT JOIN p_first f ON f.first = pr.first
LEFT JOIN p_last  l ON l.last  = pr.last
""")
