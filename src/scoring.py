"""
FEC match scoring: reference implementation.

Scores one prospect-to-FEC-identity candidate pair on a 0-100 scale.

    Score = baseline (name + rarity + ZIP + city/state + bonus - penalty)
            + street points, capped at 100

Levels: Very High >= 75 | High 60-74 | Medium 45-59 | Low < 45
Portfolio inclusion: score >= 45 (previous matches are kept by rule, outside this script).

Constants marked "approx." are small calibration details simplified for this public version.

Usage:  python scoring.py      (runs a worked example)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# 1. Point values (October scale)
# ---------------------------------------------------------------------------

NAME_POINTS = {
    "full_middle_match": 29.4,     # first, middle, last (and suffix) all agree
    "middle_initial_match": 25.9,  # approx.: initial on one side matches the full middle on the other
    "no_middle": 21.2,             # neither side has a middle name
    "middle_one_side": 20.0,       # middle present on only one side (or soft maiden-name conflict)
}
NICKNAME_HAIRCUT = 2.35            # Mike = Michael accepted, minus 2.35 

RARITY_POINTS = {1: 0.0, 2: 4.7, 3: 9.4, 4: 16.5, 5: 23.5}  # approx. for 1 and 2

ZIP_POINTS = {"most_recent": 35.3, "earlier": 31.8, "none": 0.0}
CITY_STATE_POINTS = {"city_state": 11.8, "state_only": 4.7, "none": 0.0}  # approx.: state only = 4.7

SPOUSE_BONUS = 8.0
COLLISION_PENALTY = {0: 0.0, 1: 2.0}   # 1 competing identity / shared donor = -2
COLLISION_PENALTY_MAX = 3.0            # 2+ = -3

STREET_POINTS = {
    "same_exact": 18.0,
    "same_variant": 15.0,
    "near": 10.0,
    "same_street": 4.0,
    "po_same": 10.0,
    "po_different": -5.0,
    "not_comparable": 0.0,
}
DIFF_ADDRESS_BASE = -9.0               # different address, rare name, old gift
DIFF_ADDRESS_COMMON_NAME_MAX = -12.0   # approx.: extra penalty for common names (rarity 1)
DIFF_ADDRESS_RECENT_GIFT_MAX = -9.0    # approx.: extra penalty for gifts in the last 2 years
DIFF_ADDRESS_FLOOR = -30.0

OFFICE_MULTIPLIER = 0.6        # positive street points at an office address
NAME_ONLY_MULTIPLIER = 0.5     # positive street points when the FEC row was found by name only
NEGATIVE_DAMPING = {"old_gift": 0.5, "office": 0.6, "unverified": 0.5}  # approx.: damping factors
OLD_GIFT_YEARS = 4             # approx.: a gift older than this counts as "old"
VERIFIED_SAME_ADDRESS_FLOOR = 85.0

HARD_CONFLICT_CAP = 44.0       # hard conflicts cap at Low unless a ZIP agrees

LEVELS = [(75, "Very High"), (60, "High"), (45, "Medium"), (0, "Low")]

NICKNAMES = {  # extend with the production nickname table
    "MIKE": "MICHAEL", "BILL": "WILLIAM", "WILL": "WILLIAM", "BOB": "ROBERT", "ROB": "ROBERT",
    "JIM": "JAMES", "JIMMY": "JAMES", "TOM": "THOMAS", "DAVE": "DAVID", "STEVE": "STEVEN",
    "JOE": "JOSEPH", "DAN": "DANIEL", "CHRIS": "CHRISTOPHER", "LIZ": "ELIZABETH",
    "BETH": "ELIZABETH", "KATE": "KATHERINE", "KATHY": "KATHERINE", "SUE": "SUSAN",
    "TONY": "ANTHONY", "RICK": "RICHARD", "DICK": "RICHARD", "BEN": "BENJAMIN",
}

# ---------------------------------------------------------------------------
# 2. Inputs
# ---------------------------------------------------------------------------

@dataclass
class Person:
    first: str
    last: str
    middle: str = ""
    suffix: str = ""


@dataclass
class Candidate:
    prospect: Person
    fec: Person
    name_rarity: int                   # 1 (very common) .. 5 (very rare)
    zip_match: str                     # "most_recent" | "earlier" | "none"
    geo_match: str                     # "city_state" | "state_only" | "none"
    spouse_gives_same_zip: bool = False
    competing_identities: int = 0      # other FEC identities / constituents competing for this pair
    prospect_streets: list[str] = field(default_factory=list)  # Contact, Home, Seasonal, Business
    fec_street: str = ""
    fec_is_office: bool = False
    fec_found_by_name_only: bool = False
    fec_verified: bool = True
    last_gift: date | None = None
    hard_conflicts: list[str] = field(default_factory=list)  # e.g. ["state", "age"]

# ---------------------------------------------------------------------------
# 3. Name scoring
# ---------------------------------------------------------------------------

def _clean(s: str) -> str:
    return re.sub(r"[^A-Z ]", "", (s or "").upper()).strip()


def normalize_fec_middle(middle: str) -> str:
    """Rule: strip an FEC middle initial of 'M'; keep every other initial."""
    m = _clean(middle)
    return "" if m == "M" else m


def name_points(prospect: Person, fec: Person) -> tuple[float, list[str], list[str]]:
    """Return (points, explanation notes, hard conflicts)."""
    notes, conflicts = [], []
    uf, ff = _clean(prospect.first), _clean(fec.first)
    um, fm = _clean(prospect.middle), normalize_fec_middle(fec.middle)
    us, fs = _clean(prospect.suffix), _clean(fec.suffix)

    haircut = 0.0
    if uf != ff:
        if NICKNAMES.get(uf, uf) == NICKNAMES.get(ff, ff):
            haircut = NICKNAME_HAIRCUT
            notes.append(f"nickname {ff}/{uf} (-{NICKNAME_HAIRCUT})")
        else:
            conflicts.append("first name")
            return 0.0, notes + ["first name conflict"], conflicts

    if us and fs and us != fs:
        conflicts.append("suffix")
        notes.append(f"suffix conflict {us}/{fs}")

    if not um and not fm:
        pts, case = NAME_POINTS["no_middle"], "no middle"
    elif not um or not fm:
        pts, case = NAME_POINTS["middle_one_side"], "middle on one side"
    elif um == fm:
        pts, case = NAME_POINTS["full_middle_match"], "middle agrees"
    elif um[0] == fm[0] and (len(um) == 1 or len(fm) == 1):
        pts, case = NAME_POINTS["middle_initial_match"], "middle initial agrees"
    elif len(um) > 1 and len(fm) == 1:
        # Prospect full middle vs a different FEC initial: possible maiden name, soft conflict
        pts, case = NAME_POINTS["middle_one_side"], "soft middle conflict (possible maiden name)"
    else:
        conflicts.append("middle")
        pts, case = 0.0, "middle conflict"

    notes.insert(0, case)
    return max(pts - haircut, 0.0), notes, conflicts

# ---------------------------------------------------------------------------
# 4. Street normalization and street points
# ---------------------------------------------------------------------------

_ABBR = {
    "STREET": "ST", "AVENUE": "AVE", "AV": "AVE", "ROAD": "RD", "DRIVE": "DR", "LANE": "LN",
    "BOULEVARD": "BLVD", "COURT": "CT", "CIRCLE": "CIR", "PLACE": "PL", "TERRACE": "TER",
    "PARKWAY": "PKWY", "HIGHWAY": "HWY", "COUNTY ROAD": "CR", "TRAIL": "TRL", "COVE": "CV",
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
    "APARTMENT": "APT", "SUITE": "STE", "UNIT": "UNIT", "#": "UNIT",
}
_SUFFIXES = {"ST", "AVE", "RD", "DR", "LN", "BLVD", "CT", "CIR", "PL", "TER", "PKWY", "TRL", "CV", "WAY"}
_DIRS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}


def parse_street(raw: str) -> dict | None:
    s = (raw or "").upper().replace(".", "").replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None
    po = re.match(r"^(?:P ?O ?BOX|POB|POST OFFICE BOX|BOX)\s*(\w+)", s)
    if po:
        return {"po_box": po.group(1)}
    for long, short in _ABBR.items():
        s = re.sub(rf"\b{re.escape(long)}\b", short, s)
    s = re.sub(r"\b(APT|STE|UNIT)\s*\w+$", "", s).strip()   # drop unit
    m = re.match(r"^(\d+[A-Z]?)\s+(.*)$", s)
    if not m:
        return None
    house, rest = m.group(1), m.group(2).split()
    core = [t for t in rest if t not in _SUFFIXES and t not in _DIRS]
    extras = [t for t in rest if t in _SUFFIXES or t in _DIRS]
    return {"house": house, "street": " ".join(core), "extras": extras}


def _one_digit_off(a: str, b: str) -> bool:
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def compare_streets(prospect_raw: str, fec_raw: str) -> str:
    prospect, fec = parse_street(prospect_raw), parse_street(fec_raw)
    if not prospect or not fec:
        return "not_comparable"
    if "po_box" in prospect or "po_box" in fec:
        if "po_box" in prospect and "po_box" in fec:
            return "po_same" if prospect["po_box"] == fec["po_box"] else "po_different"
        return "different"
    same_name = prospect["street"] == fec["street"]
    similar_name = SequenceMatcher(None, prospect["street"], fec["street"]).ratio() >= 0.85
    if prospect["house"] == fec["house"]:
        if same_name and prospect["extras"] == fec["extras"]:
            return "same_exact"
        if same_name:
            return "near"          # suffix / direction conflict
        if similar_name:
            return "same_variant"  # spelling variant
    elif (same_name or similar_name) and _one_digit_off(prospect["house"], fec["house"]):
        return "near"
    elif same_name:
        return "same_street"
    return "different"


_RANK = ["same_exact", "same_variant", "near", "po_same", "same_street",
         "not_comparable", "po_different", "different"]


def street_points(c: Candidate, today: date) -> tuple[float, str]:
    if not c.fec_street or not c.prospect_streets:
        return 0.0, "not_comparable"
    best = min((compare_streets(u, c.fec_street) for u in c.prospect_streets), key=_RANK.index)

    if best == "different":
        common = (5 - c.name_rarity) / 4                       # 1.0 for rarity 1, 0 for rarity 5
        years = (today - c.last_gift).days / 365.25 if c.last_gift else 99
        recent = max(0.0, 1 - years / OLD_GIFT_YEARS)         # 1.0 for a gift today
        pts = DIFF_ADDRESS_BASE + common * DIFF_ADDRESS_COMMON_NAME_MAX + recent * DIFF_ADDRESS_RECENT_GIFT_MAX
        if years > OLD_GIFT_YEARS:
            pts *= NEGATIVE_DAMPING["old_gift"]
        if c.fec_is_office:
            pts *= NEGATIVE_DAMPING["office"]
        if not c.fec_verified:
            pts *= NEGATIVE_DAMPING["unverified"]
        return max(pts, DIFF_ADDRESS_FLOOR), best

    pts = STREET_POINTS[best]
    if pts > 0:
        if c.fec_is_office:
            pts *= OFFICE_MULTIPLIER
        if c.fec_found_by_name_only:
            pts *= NAME_ONLY_MULTIPLIER
    return pts, best

# ---------------------------------------------------------------------------
# 5. Total score
# ---------------------------------------------------------------------------

def level(score: float) -> str:
    return next(name for cut, name in LEVELS if score >= cut)


def score_candidate(c: Candidate, today: date | None = None) -> dict:
    today = today or date.today()
    name_pts, name_notes, name_conflicts = name_points(c.prospect, c.fec)
    rarity = RARITY_POINTS[c.name_rarity]
    zip_pts = ZIP_POINTS[c.zip_match]
    geo_pts = CITY_STATE_POINTS[c.geo_match]
    bonus = SPOUSE_BONUS if c.spouse_gives_same_zip else 0.0
    penalty = (COLLISION_PENALTY.get(c.competing_identities, COLLISION_PENALTY_MAX)
               if c.competing_identities else 0.0)

    baseline = name_pts + rarity + zip_pts + geo_pts + bonus - penalty
    st_pts, st_result = street_points(c, today)
    score = min(baseline + st_pts, 100.0)

    if st_result in ("same_exact", "same_variant") and c.fec_verified:
        score = max(score, VERIFIED_SAME_ADDRESS_FLOOR)

    conflicts = name_conflicts + c.hard_conflicts
    if conflicts and c.zip_match == "none":
        score = min(score, HARD_CONFLICT_CAP)

    score = round(max(score, 0.0), 1)
    explanation = (
        f"name {name_pts:.1f} ({'; '.join(name_notes)}) + rarity {c.name_rarity}/5 {rarity:.1f}"
        f" + ZIP {zip_pts:.1f} + city/state {geo_pts:.1f}"
        + (f" + spouse {bonus:.0f}" if bonus else "")
        + (f" - collision {penalty:.0f}" if penalty else "")
        + f" = baseline {baseline:.1f}; street {st_result} {st_pts:+.1f} -> {score}"
        + (f" | hard conflicts: {', '.join(conflicts)}" if conflicts else "")
    )
    return {
        "score": score,
        "level": level(score),
        "in_portfolio": score >= 45,
        "baseline": round(baseline, 1),
        "street_result": st_result,
        "street_points": round(st_pts, 1),
        "explanation": explanation,
    }

# ---------------------------------------------------------------------------
# 6. Worked example (expected: baseline 81.5 -> 99.5, Very High)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    example = Candidate(
        prospect=Person(first="John", middle="Allen", last="Smith"),
        fec=Person(first="JOHN", middle="", last="SMITH"),
        name_rarity=3,
        zip_match="most_recent",
        geo_match="city_state",
        spouse_gives_same_zip=True,
        competing_identities=2,
        prospect_streets=["4120 Maple Grove Road"],
        fec_street="4120 MAPLE GROVE ROAD",
        last_gift=date(2024, 10, 1),
    )
    r = score_candidate(example, today=date(2026, 10, 8))
    print(r["explanation"])
    print(f"Score {r['score']} | {r['level']} | in portfolio: {r['in_portfolio']}")
