# Step 5: block on last name + compatible first name, nationally, across all four address blocks.
import duckdb

con = duckdb.connect("fec.duckdb")
con.execute("""
CREATE OR REPLACE TABLE candidates AS
SELECT DISTINCT p.person_id, f.fec_id
FROM prospects p
JOIN fec_identities f
  ON f.last = p.last
 AND (f.first = p.first
      OR f.first IN (SELECT nick FROM nicknames WHERE full_name = p.first)
      OR p.first IN (SELECT nick FROM nicknames WHERE full_name = f.first))
JOIN prospect_addresses a                       -- contact, home, seasonal, business
  ON a.person_id = p.person_id AND a.state = f.state
""")
print(con.execute("SELECT count(*), count(DISTINCT person_id) FROM candidates").fetchone())
