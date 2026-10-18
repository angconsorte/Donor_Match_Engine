# Step 2: collapse transactions into donor identities (one person = one name at one ZIP).
import duckdb
from normalize import split_fec_name

con = duckdb.connect("fec.duckdb")
con.create_function("split_name", split_fec_name, ["VARCHAR"],
                    "STRUCT(first VARCHAR, middle VARCHAR, last VARCHAR, suffix VARCHAR)")
con.execute("""
CREATE OR REPLACE TABLE fec_identities AS
SELECT md5(n.first || n.last || zip5)  AS fec_id,
       n.first, max(n.middle) AS middle, n.last, max(n.suffix) AS suffix,
       zip5, any_value(city) AS city, any_value(state) AS state,
       count(*) AS n_gifts, sum(transaction_amt::DOUBLE) AS total_given,
       max(gift_date) AS last_gift
FROM (SELECT *, split_name(name) AS n FROM fec_tx)
GROUP BY n.first, n.last, zip5
""")
print(con.execute("SELECT count(*) FROM fec_identities").fetchone())
