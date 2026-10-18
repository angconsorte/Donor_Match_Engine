# Name normalization shared by the pipeline.
import re

SUFFIX = {"JR", "SR", "II", "III", "IV"}
TITLES = {"MR", "MRS", "MS", "DR", "HON"}

def split_fec_name(raw):
    """FEC names look like 'LAST, FIRST MIDDLE JR'. Returns (first, middle, last, suffix)."""
    last, _, rest = (raw or "").upper().partition(",")
    toks = re.sub(r"[^A-Z ]", " ", rest).split()
    suffix = next((t for t in toks if t in SUFFIX), "")
    toks = [t for t in toks if t not in SUFFIX | TITLES]
    first = toks[0] if toks else ""
    middle = toks[1] if len(toks) > 1 else ""
    return first, middle, re.sub(r"[^A-Z]", "", last), suffix
