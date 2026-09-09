#!/usr/bin/env python3
"""Combine ReferenceUSA exports into one tidy file, plus one file per state.

    python scripts/combine_referenceusa.py

Reads every export in reference-usa/ (ReferenceUSA caps a download at 250 records, so
a state arrives as many files, and re-running a search produces byte-identical
duplicates). Writes to reference-usa/combined/:

    referenceusa_all.csv        every deduplicated record
    referenceusa_<ST>.csv       one file per state
    referenceusa_review.csv     records whose industry code is not senior housing

The exports carry 396 columns, 200 of them empty executive slots. Only the ~30 that
carry information are kept.

**On the `category` column.** ReferenceUSA is a business directory, not a licensure
list. A search by industry code returns whatever is coded to that industry, which
includes home health agencies, property companies that own a building, management
firms, and a long tail of businesses that share an address or a name with a community.
Nothing here is a licensed-facility list, and no record should be treated as one
without checking it against that state's licensure file. `category` sorts records by
their primary industry code so the obvious noise can be set aside first; it does not
verify that a record in the "assisted_living" bucket is a real, currently licensed
community.
"""
import glob
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reference-usa")
OUT = os.path.join(SRC, "combined")

# Columns worth keeping, in the order they should appear.
KEEP = [
    "Company Name", "Parent Company Name", "Address", "City", "State", "ZIP Code",
    "County", "Phone Number Combined", "Website", "Company Description",
    "Primary NAICS", "Primary NAICS Description",
    "Primary SIC Code", "Primary SIC Description",
    "Location Employee Size Actual", "Location Employee Size Range",
    "Location Sales Volume Actual", "Location Sales Volume Range",
    "Location Type", "Year Established", "Years In Database",
    "Executive First Name", "Executive Last Name", "Executive Title",
    "Professional Title", "Owns Location", "Affiliated Locations",
    "Mailing Address", "Mailing City", "Mailing State", "Mailing Zip Code",
]

# Primary NAICS prefix -> bucket. Longest prefix wins.
BUCKETS = [
    ("623312", "assisted_living",   "Assisted living facilities for the elderly"),
    ("623311", "ccrc",              "Continuing care retirement community"),
    ("62311",  "nursing_care",      "Nursing care / skilled nursing facility"),
    ("62322",  "residential_other", "Residential mental health or substance abuse"),
    ("62399",  "residential_other", "Other residential care"),
    ("62321",  "residential_other", "Residential intellectual disability facility"),
    ("62161",  "home_health",       "Home health care services"),
    ("62412",  "elder_services",    "Services for the elderly and disabled"),
    ("62419",  "elder_services",    "Other individual and family services"),
]


# Industry coding is unreliable in BOTH directions. Real communities turn up coded as
# consulting firms, hotels, building material dealers and property lessors, so the
# "other" bucket cannot simply be discarded. A name signal triages it: these phrases
# name the business as senior housing regardless of how it was coded.
STRONG_NAME = re.compile(
    r"(?i)\b(assisted\s*living|assisted\s*lvng|memory\s*care|senior\s*living|"
    r"retirement|nursing\s*home|alzheimer|independent\s*living|senior\s*care|"
    r"elder\s*care|rest\s*home|personal\s*care\s*home|care\s*cent(er|re))\b")
# Weaker: common in community names, but also in apartments, hotels and subdivisions.
WEAK_NAME = re.compile(
    r"(?i)\b(manor|village|gardens?|terrace|commons|estates?|pointe|landing|"
    r"crossings?|place|arbors?|meadows?|springs?|haven|lodge|cottages?|"
    r"residence|court|crest|grove|oaks?)\b")


def name_signal(name):
    if STRONG_NAME.search(str(name)):
        return "strong"
    if WEAK_NAME.search(str(name)):
        return "weak"
    return "none"


def classify(naics):
    n = re.sub(r"\D", "", str(naics))
    for prefix, bucket, label in BUCKETS:
        if n.startswith(prefix):
            return bucket, label
    return "other", "Not a senior housing or care industry code"


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.csv"))
                   + glob.glob(os.path.join(SRC, "*.csv.crdownload")))
    files = [f for f in files if os.path.dirname(f) == SRC]
    if not files:
        raise SystemExit(f"no exports found in {SRC}")

    frames = []
    for f in files:
        d = pd.read_csv(f, dtype=str, keep_default_na=False, low_memory=False)
        d["source_file"] = os.path.basename(f)
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    raw = len(df)

    ident = ["Company Name", "Address", "City", "State", "ZIP Code"]
    df = df.drop_duplicates(ident).reset_index(drop=True)

    cols = [c for c in KEEP if c in df.columns]
    out = df[cols + ["source_file"]].copy()
    cat = df["Primary NAICS"].map(classify)
    out.insert(0, "category", [c[0] for c in cat])
    out.insert(1, "category_note", [c[1] for c in cat])
    out.insert(2, "name_signal", out["Company Name"].map(name_signal))
    out = out.sort_values(["State", "category", "Company Name"]).reset_index(drop=True)

    os.makedirs(OUT, exist_ok=True)
    out.to_csv(os.path.join(OUT, "referenceusa_all.csv"), index=False)
    for st, g in out.groupby("State"):
        g.to_csv(os.path.join(OUT, f"referenceusa_{st}.csv"), index=False)
    # Split the noise bucket by whether the name says senior housing anyway.
    other = out[out["category"] == "other"]
    miscoded = other[other["name_signal"] == "strong"]
    review = other[other["name_signal"] != "strong"]
    miscoded.to_csv(os.path.join(OUT, "referenceusa_likely_miscoded.csv"), index=False)
    review.to_csv(os.path.join(OUT, "referenceusa_review.csv"), index=False)

    print(f"{len(files)} export files, {raw:,} rows -> {len(out):,} after removing "
          f"{raw-len(out):,} duplicate record(s)")
    print(f"kept {len(cols)} of {len(df.columns)-1} columns\n")

    print("BY STATE")
    piv = pd.crosstab(out["State"], out["category"])
    order = [c for c in ["assisted_living", "ccrc", "nursing_care", "residential_other",
                         "home_health", "elder_services", "other"] if c in piv.columns]
    print(piv[order].to_string())
    print()
    print("BY CATEGORY")
    for c in order:
        n = int((out["category"] == c).sum())
        print(f"  {n:>5}  {n/len(out)*100:>5.1f}%  {c}")
    core = int(out["category"].isin(["assisted_living", "ccrc"]).sum())
    print(f"\n  {core:,} of {len(out):,} records ({core/len(out)*100:.0f}%) carry an "
          f"assisted living or CCRC industry code.")
    print(f"  {len(other):,} carry an industry code unrelated to senior housing, of which:")
    print(f"     {len(miscoded):,} are named as senior housing anyway and look MISCODED "
          f"-- referenceusa_likely_miscoded.csv")
    print(f"     {len(review):,} show no senior-housing signal in the name "
          f"-- referenceusa_review.csv")
    named = int((out["name_signal"] == "strong").sum())
    print(f"\n  {named:,} records name themselves as senior housing; {core:,} are coded "
          f"as such.")
    print("  The two disagree in both directions, so neither field alone is a filter.")

    # Fields a market study actually needs, and whether they arrived.
    print("\nFIELD COVERAGE (non-empty)")
    for c in ["Company Name", "Address", "County", "Phone Number Combined", "Website",
              "Location Employee Size Actual", "Year Established", "Executive Last Name"]:
        if c in out.columns:
            n = int((out[c].astype(str).str.strip() != "").sum())
            print(f"  {n:>5}  {n/len(out)*100:>5.1f}%  {c}")
    print("\n  No column in this export carries licensed beds, units or capacity.")
    print("  Employee count is the only size signal. It is a headcount rather than")
    print("  capacity, and it is modelled where not reported, so a value being present")
    print("  does not mean it was observed.")


if __name__ == "__main__":
    main()
