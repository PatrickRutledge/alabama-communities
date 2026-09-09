#!/usr/bin/env python3
"""Build a sub-state region from an already-built state.

    python scripts/build_region.py --region BHM

A region is a named set of counties inside one state. The state build has already done
every expensive thing -- CMS enrollment, spend, utilization, licensure, geocoding -- so a
region is a filter plus two recalculations:

  1. The bed gap is re-benchmarked against the REGION's own rate rather than the state's.
     For a market study that is the meaningful comparison: a metro county competes with
     the rest of its metro, not with the rural end of the state. The statewide-benchmarked
     figure is kept alongside as `bed_gap_state` so the two can be shown together.
  2. The map is re-projected to the region's own bounds, so seven counties fill the frame
     instead of sitting in a corner of the state outline.

Writes data/<region>_master.json, _facilities.json and _geo.json.
"""
import argparse
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import states as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

REGIONS = {
    "BHM": {
        "name": "Birmingham-Hoover",
        "long": "Birmingham-Hoover Metropolitan Statistical Area",
        "state": "AL",
        "out_prefix": "bhm/",
        # The Census MSA definition, used unmodified so the boundary needs no defending.
        "counties": ["Jefferson", "Shelby", "St. Clair", "Blount", "Bibb", "Walker", "Chilton"],
        "core": "Jefferson",
        "blurb": ("The seven counties the Census Bureau defines as the Birmingham-Hoover "
                  "Metropolitan Statistical Area."),
    },
}


def get(code):
    code = code.upper()
    if code not in REGIONS:
        raise SystemExit(f"unknown region {code}; known: {', '.join(sorted(REGIONS))}")
    return REGIONS[code]


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def project(feats):
    """Re-project a set of county rings to fill a 600-wide viewBox."""
    def rings(f):
        g = f["geometry"]
        c = g["coordinates"]
        return [r for poly in c for r in poly] if g["type"] == "MultiPolygon" else list(c)

    pts = [p for f in feats for r in rings(f) for p in r]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    W = 600.0
    H = W * (lat1 - lat0) / ((lon1 - lon0) * k)
    out = {}
    for f in feats:
        parts = []
        for r in rings(f):
            if len(r) < 3:
                continue
            xy = [((p[0] - lon0) / (lon1 - lon0) * W,
                   H - (p[1] - lat0) / (lat1 - lat0) * H) for p in r]
            parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in xy) + "Z")
        out[f["id"]] = {"n": f["properties"]["NAME"], "d": "".join(parts)}
    return {"w": round(W), "h": round(H),
            "lon0": lon0, "lon1": lon1, "lat0": lat0, "lat1": lat1, "c": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    args = ap.parse_args()
    code = args.region.upper()
    reg = get(code)
    st = S.get(reg["state"])
    pre_state = st["name"].lower() + "_"
    pre = code.lower() + "_"

    rows_all = load(pre_state + "master.json")
    facs_all = load(pre_state + "facilities.json")

    want = {S.key(c) for c in reg["counties"]}
    rows = [r for r in rows_all if S.key(r["county"]) in want]
    found = {S.key(r["county"]) for r in rows}
    missing = sorted(want - found)
    if missing:
        raise SystemExit(f"counties not found in {st['name']}: {missing}")

    fips = {r["fips"] for r in rows}
    facs = [f for f in facs_all if f.get("fips") in fips]

    # Re-benchmark the bed gap against the region's own rate.
    t = lambda k: sum((r.get(k) or 0) for r in rows)
    region_rate = t("sl_bed") / t("a75") * 1000 if t("a75") else 0
    for r in rows:
        r["bed_gap_state"] = r["bed_gap"]          # keep the statewide-benchmarked figure
        r["bed_gap"] = round(r["a75"] * region_rate / 1000 - r["sl_bed"])

    rows.sort(key=lambda r: -r["enroll"])

    with open(os.path.join(DATA, pre + "master.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    with open(os.path.join(DATA, pre + "master.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(DATA, pre + "facilities.json"), "w", encoding="utf-8") as f:
        json.dump(facs, f, separators=(",", ":"))

    with open(os.path.join(ROOT, st["raw"], "us_counties.geojson"), encoding="utf-8") as f:
        feats = [x for x in json.load(f)["features"] if x["id"] in fips]
    with open(os.path.join(DATA, pre + "geo.json"), "w", encoding="utf-8") as f:
        json.dump(project(feats), f, separators=(",", ":"))

    short = [r for r in rows if r["bed_gap"] > 0]
    short_state = [r for r in rows if r["bed_gap_state"] > 0]
    state_rate = sum((r.get("sl_bed") or 0) for r in rows_all) / \
        sum((r.get("a75") or 0) for r in rows_all) * 1000
    print(f"{reg['long']}: {len(rows)} counties of {st['name']}'s {len(rows_all)}")
    print(f"  enrollees {t('enroll'):,} ({t('ma')/t('enroll'):.1%} Medicare Advantage) | "
          f"aged 75+ {t('a75'):,} | aged 85+ {t('a85'):,}")
    print(f"  FFS spend ${t('tot_amt')/1e9:.2f}B over {t('ffs_benes'):,} benes")
    print(f"  {len(facs)} communities | {t('sl_bed'):,} {st['capacity_word']} | "
          f"{t('mc_bed'):,} memory care")
    print(f"  metro rate {region_rate:.1f} per 1,000 aged 75+ "
          f"(statewide {state_rate:.1f}) | {t('a75')/t('sl_bed'):.0f} people 75+ per bed")
    print(f"  benchmarked to the METRO: {len(short)} counties short, "
          f"{sum(r['bed_gap'] for r in short):,} beds")
    print(f"  benchmarked to the STATE: {len(short_state)} counties short, "
          f"{sum(r['bed_gap_state'] for r in short_state):,} beds")


if __name__ == "__main__":
    main()
