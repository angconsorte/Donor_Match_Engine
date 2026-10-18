# Build a fully synthetic snapshot of the final match table.
# People, addresses, employers and amounts are fake (Faker). Each new match is scored with
# src/scoring.py, and rows are kept until the sample matches the real tier and status mix.
import random, sys
from datetime import date, timedelta
import pandas as pd
from faker import Faker

sys.path.append("src")
from scoring import Candidate, Person, score_candidate

SEED, TODAY = 7, date(2026, 10, 9)
fake, rng = Faker("en_US"), random.Random(SEED)
Faker.seed(SEED)

# Real mix: ~68% new / ~32% previous; new matches ~93% Very High, ~5% High, ~2% Medium.
QUOTA = {"Very High": 317, "High": 15, "Medium": 8}
N_PREVIOUS = 160

NICK = {"Michael": "MIKE", "William": "BILL", "Robert": "BOB", "James": "JIM",
        "Thomas": "TOM", "David": "DAVE", "Elizabeth": "LIZ", "Susan": "SUE"}
JOBS = (["Retired"] * 22 + ["Not Employed"] * 18 + ["Attorney"] * 5 + ["Physician"] * 2 +
        ["Homemaker", "CEO", "President", "Owner", "Professor", "Consultant", "Real Estate",
         "Partner", "Self-Employed", "Engineer", "Banker", "Investor"])
RECIPIENT = ["Candidate committee", "Party committee", "PAC", "Joint fundraising committee"]

def pick(weights):
    return rng.choices(list(weights), list(weights.values()))[0]

def state():
    return pick({"OH": 55, "PA": 15, "": 30}) or fake.state_abbr(include_territories=False)

def gift_date():
    return min(TODAY, date(2021, 1, 2) + timedelta(days=int(rng.betavariate(3.2, 1.4) * 2050)))

def giving_bin(x):
    for cut, label in [(1e3, "<$1K"), (3e3, "$1K-$3K"), (1e4, "$3K-$10K"),
                       (5e4, "$10K-$50K"), (5e5, "$50K-$500K")]:
        if x < cut:
            return label
    return "$500K+"

def fec_street_for(result, street):
    house, _, rest = street.partition(" ")
    if result == "same_exact":
        return street.upper().replace("STREET", "ST").replace("ROAD", "RD").replace("AVENUE", "AVE")
    if result == "same_variant":
        i = rng.randrange(1, max(2, len(rest) - 4))
        return f"{house} {rest[:i] + rest[i + 1:]}".upper()          # one dropped letter
    if result == "near":
        return f"{house[:-1]}{(int(house[-1]) + 1) % 10} {rest}".upper()
    if result == "same_street":
        return f"{rng.randint(100, 9999)} {rest}".upper()
    if result == "po_same":
        return street.upper()
    if result == "different":
        return fake.street_address().upper()
    return ""                                                         # not comparable

GEO_LABEL = {"same_exact": "Street match (same address)", "same_variant": "Street match (spelling variant)",
             "near": "Near street match", "same_street": "Same street, different house #",
             "po_same": "PO box match", "po_different": "PO box differs", "different": "Street differs",
             "not_comparable": ""}
ZIP_LABEL = {"most_recent": "ZIP match (most recent FEC ZIP)", "earlier": "ZIP match (earlier FEC ZIP)"}

def new_match():
    first, last = fake.first_name(), fake.last_name()
    middle = fake.first_name() if rng.random() < 0.7 else ""
    fec_first = NICK.get(first, first.upper()) if rng.random() < 0.3 else first.upper()
    fec_middle = pick({middle[:1]: 40, "": 50, middle: 5, "Q": 5}) if middle else pick({"": 85, "R": 15})
    street_result = pick({"same_exact": 78, "same_variant": 2, "near": 2, "po_same": 3,
                          "same_street": 1, "different": 9, "not_comparable": 5})
    street = f"PO Box {rng.randint(10, 9999)}" if street_result == "po_same" else fake.street_address()
    zip_match = pick({"most_recent": 85, "earlier": 4, "none": 11})
    geo = "city_state" if zip_match != "none" or rng.random() < 0.7 else "state_only"
    spouse = pick({"Yes": 17, "No": 51, "n/a (no spouse on file)": 32})
    c = Candidate(
        prospect=Person(first, last, middle), fec=Person(fec_first, last.upper(), fec_middle),
        name_rarity=pick({5: 36, 4: 26, 3: 26, 2: 10, 1: 2}), zip_match=zip_match, geo_match=geo,
        spouse_gives_same_zip=spouse == "Yes", competing_identities=pick({0: 84, 1: 12, 2: 4}),
        prospect_streets=[street], fec_street=fec_street_for(street_result, street),
        fec_is_office=rng.random() < 0.05, last_gift=gift_date())
    return c, spouse, score_candidate(c, today=TODAY)

rows, i = [], 0
while sum(QUOTA.values()):
    c, spouse, r = new_match()
    if QUOTA.get(r["level"], 0) == 0:
        continue
    QUOTA[r["level"]] -= 1
    st = state()
    amount = round(min(rng.lognormvariate(6.62, 1.9), 1e6), 2)
    geo_parts = [GEO_LABEL[r["street_result"]], ZIP_LABEL.get(c.zip_match) or
                 ("City + State match" if c.geo_match == "city_state" else "State match")]
    i += 1
    rows.append(dict(
        record_id=f"SYN-{i:05d}", match_status="New match", confidence_level=r["level"],
        confidence_score=r["score"],
        prospect_name=" ".join(filter(None, [c.prospect.first, c.prospect.middle, c.prospect.last])),
        fec_donor_name=" ".join(filter(None, [c.fec.first, c.fec.middle, c.fec.last])).title(),
        state=st, geographic_match=" + ".join(filter(None, geo_parts)),
        name_rarity=c.name_rarity, competing_fec_identities=c.competing_identities,
        spouse_also_fec_donor=spouse, fec_occupation=rng.choice(JOBS), fec_employer=fake.company(),
        fec_giving_bin=giving_bin(amount), fec_total_2022_2026=amount,
        fec_gift_count=max(1, round(rng.lognormvariate(1.1, 1.6))), fec_last_gift=c.last_gift,
        largest_gift_recipient=rng.choice(RECIPIENT),
        prospect_street=c.prospect_streets[0], fec_street=c.fec_street or None,
        address_match_result=r["street_result"], match_explanation=r["explanation"]))

for _ in range(N_PREVIOUS):            # previous matches: kept by rule, carry lifetime totals
    i += 1
    first, last = fake.first_name(), fake.last_name()
    lifetime = round(max(3000, rng.lognormvariate(9.11, 1.3)), 2)
    rows.append(dict(record_id=f"SYN-{i:05d}", match_status="Previous match",
                     confidence_level="Previous match", prospect_name=f"{first} {last}",
                     fec_donor_name=f"{first} {last}", state=pick({"OH": 90, "PA": 10}),
                     previous_fec_bin=giving_bin(lifetime), previous_lifetime_total=lifetime))

df = pd.DataFrame(rows).sample(frac=1, random_state=SEED)
df = df.sort_values(["match_status", "confidence_score"], ascending=[True, False])
df.to_csv("sample_data/fec_matches_sample.csv", index=False)
print(df.groupby(["match_status", "confidence_level"]).size())
