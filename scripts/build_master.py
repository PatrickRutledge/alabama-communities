#!/usr/bin/env python3
"""Merge the raw sources into one row per Alabama county.

Reads   data/raw/*   (see scripts/fetch_data.py)
Writes  data/alabama_master.json      one object per county, used by the site
        data/alabama_master.csv       same thing, for spreadsheets
        data/al_geo.json              projected SVG paths for the county map

Joining note: the three sources spell counties three different ways
("DeKalb" / "Dekalb" / "De Kalb"), so everything joins on 5-digit FIPS where
available and on a letters-only county key otherwise.
"""
import csv
import json
import math
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data")

# Per-capita spend buckets published in the Geographic Variation PUF.
BUCKETS = ["IP", "OP", "ASC", "SNF", "IRF", "LTCH", "HH", "HOSPC", "EM",
           "PRCDRS", "TESTS", "IMGNG", "DME", "OP_DLYS", "FQHC_RHC", "AMBLNC", "TRTMNTS"]

# How those buckets roll up on the site. "Institutional PAC" is post-acute only:
# Medicare pays no custodial long-term care, so no bundle here represents a nursing home stay.
HOME = ["hh", "em", "dme", "tests", "imgng", "fqhc_rhc", "trtmnts"]
ACUTE = ["ip", "op", "asc", "prcdrs", "amblnc", "op_dlys"]
INST = ["snf", "irf", "ltch"]

AGE_75_PLUS = ["AGE_75_TO_79_BENES", "AGE_80_TO_84_BENES", "AGE_85_TO_89_BENES",
               "AGE_90_TO_94_BENES", "AGE_GT_94_BENES"]
AGE_85_PLUS = ["AGE_85_TO_89_BENES", "AGE_90_TO_94_BENES", "AGE_GT_94_BENES"]

key = lambda c: re.sub(r"[^a-z]", "", str(c).lower())


def num(v):
    """CMS suppresses small cells as '*'; treat anything unparseable as missing."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(name):
    with open(os.path.join(RAW, name), encoding="utf-8") as f:
        return json.load(f)


def licensed_beds(filename):
    """Facility count and licensed beds per county from an ADPH Excel export."""
    df = pd.read_excel(os.path.join(RAW, filename), header=0)
    df.columns = [str(c).strip() for c in df.columns]
    df["K"] = df["County"].map(key)
    df["Licensed Beds"] = pd.to_numeric(df["Licensed Beds"], errors="coerce").fillna(0)
    g = df.groupby("K").agg(fac=("Facility Name", "count"), bed=("Licensed Beds", "sum"))
    return g.to_dict("index")


def build_geometry():
    """Project Alabama county rings to a fixed SVG viewBox and emit path strings.

    Equirectangular with a cos(lat) correction -- at Alabama's span the distortion
    is invisible and it keeps the payload to a couple of dozen KB with no projection
    library. The upstream GeoJSON is already generalized, so no simplification here.
    """
    with open(os.path.join(RAW, "us_counties.geojson"), encoding="utf-8") as f:
        feats = [x for x in json.load(f)["features"] if x["id"].startswith("01")]

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

    geo = {"w": round(W), "h": round(H), "c": out}
    with open(os.path.join(OUT, "al_geo.json"), "w", encoding="utf-8") as f:
        json.dump(geo, f, separators=(",", ":"))
    return geo


def main():
    geovar = {r["BENE_GEO_CD"]: r for r in load("al_geovar.json")}
    enrollment = load("al_enrollment.json")
    latest = max(r["YEAR"] for r in enrollment)
    enroll = {r["BENE_FIPS_CD"].strip(): r for r in enrollment if r["YEAR"] == latest}

    alf = licensed_beds("al_assisted_living.xls")
    mc = licensed_beds("al_memory_care.xls")

    nh = {}
    for r in load("al_nursing_homes.json"):
        d = nh.setdefault(key(r.get("countyparish") or ""), {"fac": 0, "bed": 0.0, "res": 0.0})
        d["fac"] += 1
        d["bed"] += num(r.get("number_of_certified_beds")) or 0
        d["res"] += num(r.get("average_number_of_residents_per_day")) or 0

    rows = []
    for fips, g in geovar.items():
        e = enroll.get(fips)
        if not e or g["BENE_GEO_DESC"] == "AL-UNKNOWN":
            continue
        county = g["BENE_GEO_DESC"][3:]
        k = key(county)
        total = num(e["TOT_BENES"])

        d = {
            "county": county, "fips": fips,
            "enroll": int(total),
            "ma": int(num(e["MA_AND_OTH_BENES"])),
            "om": int(num(e["ORGNL_MDCR_BENES"])),
            "dual": int(num(e["DUAL_TOT_BENES"])),
            "a75": int(sum(num(e[c]) or 0 for c in AGE_75_PLUS)),
            "a85": int(sum(num(e[c]) or 0 for c in AGE_85_PLUS)),
            # FFS beneficiaries with full Part A+B -- the denominator for every
            # per-capita dollar below. Not the same as total enrollees.
            "ffs_benes": int(num(g["BENES_OM_CNT"])),
            "avg_age": num(g["BENE_AVG_AGE"]),
            "pc": num(g["TOT_MDCR_PYMT_PC"]),
            "pc_std": num(g["TOT_MDCR_STDZD_PYMT_PC"]),
            "tot_amt": num(g["TOT_MDCR_PYMT_AMT"]),
            "ip_stays": num(g["IP_CVRD_STAYS_PER_1000_BENES"]),
            "readmit": num(g["ACUTE_HOSP_READMSN_PCT"]),
            "er": num(g["ER_VISITS_PER_1000_BENES"]),
            "snf_pct": num(g["BENES_SNF_PCT"]),
            "snf_stays": num(g["SNF_CVRD_STAYS_PER_1000_BENES"]),
            "snf_days": num(g["SNF_CVRD_DAYS_PER_1000_BENES"]),
            "snf_per_user": num(g["SNF_MDCR_PYMT_PER_USER"]),
            "hh_pct": num(g["BENES_HH_PCT"]),
            "hh_eps": num(g["HH_EPISODES_PER_1000_BENES"]),
            "hospc_pct": num(g["BENES_HOSPC_PCT"]),
            "hospc_days": num(g["HOSPC_CVRD_DAYS_PER_1000_BENES"]),
            "alf_fac": alf.get(k, {}).get("fac", 0),
            "alf_bed": int(alf.get(k, {}).get("bed", 0)),
            "mc_fac": mc.get(k, {}).get("fac", 0),
            "mc_bed": int(mc.get(k, {}).get("bed", 0)),
            "nh_fac": nh.get(k, {}).get("fac", 0),
            "nh_bed": int(nh.get(k, {}).get("bed", 0)),
            "nh_res": round(nh.get(k, {}).get("res", 0), 1),
        }
        for b in BUCKETS:
            d["pc_" + b.lower()] = num(g[b + "_MDCR_PYMT_PC"])
        d["home_pc"] = round(sum(d["pc_" + k2] or 0 for k2 in HOME), 2)
        d["acute_pc"] = round(sum(d["pc_" + k2] or 0 for k2 in ACUTE), 2)
        d["inst_pc"] = round(sum(d["pc_" + k2] or 0 for k2 in INST), 2)
        d["eol_pc"] = d["pc_hospc"]
        rows.append(d)

    rows.sort(key=lambda r: -r["enroll"])

    # Any supply county that didn't join means a new spelling upstream -- fail loudly.
    known = {key(r["county"]) for r in rows}
    for label, src in [("assisted living", alf), ("memory care", mc), ("nursing home", nh)]:
        missing = [c for c in src if c not in known]
        if missing:
            raise SystemExit(f"unjoined {label} counties: {missing}")

    with open(os.path.join(OUT, "alabama_master.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    with open(os.path.join(OUT, "alabama_master.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    build_geometry()

    t = lambda k2: sum(r[k2] for r in rows)
    beds = t("alf_bed") + t("mc_bed")
    print(f"{len(rows)} counties | enrollment year {latest}")
    print(f"  enrollees {t('enroll'):,} ({t('ma')/t('enroll'):.1%} Medicare Advantage)")
    print(f"  aged 75+ {t('a75'):,} | aged 85+ {t('a85'):,}")
    print(f"  FFS spend ${t('tot_amt')/1e9:.2f}B over {t('ffs_benes'):,} benes "
          f"= ${t('tot_amt')/t('ffs_benes'):,.0f} each")
    print(f"  assisted living {t('alf_bed'):,} beds | memory care {t('mc_bed'):,} beds "
          f"| nursing home {t('nh_res'):,.0f} residents")
    print(f"  {t('a75')/beds:.0f} people aged 75+ per licensed AL/memory-care bed")
    print(f"  {sum(1 for r in rows if r['alf_bed'] + r['mc_bed'] == 0)} counties "
          f"with no licensed assisted living or memory care")


if __name__ == "__main__":
    main()
