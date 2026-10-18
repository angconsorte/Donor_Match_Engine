# Step 6: bulk files have no street address, so pull it from the FEC API (Schedule A)
# for candidate identities only.
import os, time, duckdb, requests

API = "https://api.open.fec.gov/v1/schedules/schedule_a/"
KEY = os.environ["FEC_API_KEY"]
con = duckdb.connect("fec.duckdb")
rows = con.execute("""SELECT DISTINCT f.fec_id, f.last || ', ' || f.first, f.zip5
                      FROM candidates c JOIN fec_identities f USING (fec_id)""").fetchall()

out = []
for fec_id, name, zip5 in rows:
    r = requests.get(API, params={"contributor_name": name, "contributor_zip": zip5,
                                  "per_page": 20, "api_key": KEY}, timeout=30)
    for g in r.json().get("results", []):
        out.append((fec_id, g.get("contributor_street_1"), g.get("contribution_receipt_date")))
    time.sleep(0.5)                                    # stay under the API rate limit

con.execute("CREATE OR REPLACE TABLE fec_streets (fec_id VARCHAR, street VARCHAR, gift_date DATE)")
con.executemany("INSERT INTO fec_streets VALUES (?, ?, ?)", out)
