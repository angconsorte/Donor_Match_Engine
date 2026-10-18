# Step 1: load FEC bulk individual contributions (2022, 2024, 2026 cycles) into DuckDB.
import duckdb

COLS = ["cmte_id", "amndt_ind", "rpt_tp", "transaction_pgi", "image_num", "transaction_tp",
        "entity_tp", "name", "city", "state", "zip_code", "employer", "occupation",
        "transaction_dt", "transaction_amt", "other_id", "tran_id", "file_num",
        "memo_cd", "memo_text", "sub_id"]

schema = "{" + ", ".join(f"'{c}': 'VARCHAR'" for c in COLS) + "}"
con = duckdb.connect("fec.duckdb")
con.execute(f"""
CREATE OR REPLACE TABLE fec_tx AS
SELECT DISTINCT ON (sub_id) *,
       strptime(transaction_dt, '%m%d%Y')::DATE AS gift_date,
       left(zip_code, 5)                        AS zip5
FROM read_csv('data/indiv*/itcont*.txt', delim='|', header=false, quote='',
              columns={schema})
WHERE entity_tp = 'IND'
  AND coalesce(memo_cd, '') <> 'X'     -- conduit memo rows would double-count gifts
""")
print(con.execute("SELECT count(*), sum(transaction_amt::DOUBLE) FROM fec_tx").fetchone())
