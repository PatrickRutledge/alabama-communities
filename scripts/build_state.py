#!/usr/bin/env python3
"""Merge one state's CMS and licensure data into one row per county.

    python scripts/build_state.py --state TX

Writes, for state XX:
    data/<prefix>master.json      one object per county, used by the site
    data/<prefix>master.csv       the same rows, for spreadsheets
    data/<prefix>geo.json         county SVG paths plus projection bounds
    data/<prefix>facilities.json  one object per licence, with coordinates

The CMS half is identical for every state -- enrollment, spend and utilization come
from national files filtered by FIPS. Only the supply half is state-specific, and it
lives in scripts/states.py. See that module for why memory care is added to total
capacity in Alabama and subtracted from it in Texas.
"""
import argparse
import csv
import json
import math
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import states as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")
GROWTH_YEARS = 5

BUCKETS = ["IP", "OP", "ASC", "SNF", "IRF", "LTCH", "HH", "HOSPC", "EM",
           "PRCDRS", "TESTS", "IMGNG", "DME", "OP_DLYS", "FQHC_RHC", "AMBLNC", "TRTMNTS"]
HOME = ["hh", "em", "dme", "tests", "imgng", "fqhc_rhc", "trtmnts"]
ACUTE = ["ip", "op", "asc", "prcdrs", "amblnc", "op_dlys"]
INST = ["snf", "irf", "ltch"]

GV_FIELDS = {
    "avg_age": "BENE_AVG_AGE", "feml_pct": "BENE_FEML_PCT",
    "wht_pct": "BENE_RACE_WHT_PCT", "blk_pct": "BENE_RACE_BLACK_PCT",
    "hsp_pct": "BENE_RACE_HSPNC_PCT",
    "pc": "TOT_MDCR_PYMT_PC", "pc_std": "TOT_MDCR_STDZD_PYMT_PC",
    "tot_amt": "TOT_MDCR_PYMT_AMT",
    "ip_pct": "BENES_IP_PCT", "ip_stays": "IP_CVRD_STAYS_PER_1000_BENES",
    "ip_days": "IP_CVRD_DAYS_PER_1000_BENES", "ip_per_user": "IP_MDCR_PYMT_PER_USER",
    "readmit": "ACUTE_HOSP_READMSN_PCT",
    "er": "ER_VISITS_PER_1000_BENES", "er_pct": "BENES_ER_VISITS_PCT",
    "op_pct": "BENES_OP_PCT", "op_visits": "OP_VISITS_PER_1000_BENES",
    "snf_pct": "BENES_SNF_PCT", "snf_stays": "SNF_CVRD_STAYS_PER_1000_BENES",
    "snf_days": "SNF_CVRD_DAYS_PER_1000_BENES", "snf_per_user": "SNF_MDCR_PYMT_PER_USER",
    "irf_pct": "BENES_IRF_PCT", "irf_stays": "IRF_CVRD_STAYS_PER_1000_BENES",
    "ltch_pct": "BENES_LTCH_PCT", "ltch_stays": "LTCH_CVRD_STAYS_PER_1000_BENES",
    "hh_pct": "BENES_HH_PCT", "hh_eps": "HH_EPISODES_PER_1000_BENES",
    "hh_visits": "HH_VISITS_PER_1000_BENES", "hh_per_user": "HH_MDCR_PYMT_PER_USER",
    "hospc_pct": "BENES_HOSPC_PCT", "hospc_stays": "HOSPC_CVRD_STAYS_PER_1000_BENES",
    "hospc_days": "HOSPC_CVRD_DAYS_PER_1000_BENES",
    "em_pct": "BENES_EM_PCT", "em_events": "EM_EVNTS_PER_1000_BENES",
    "dme_pct": "BENES_DME_PCT", "dme_events": "DME_EVNTS_PER_1000_BENES",
    "tests_pct": "BENES_TESTS_PCT", "imgng_pct": "BENES_IMGNG_PCT",
    "fqhc_pct": "BENES_FQHC_RHC_PCT", "fqhc_visits": "FQHC_RHC_VISITS_PER_1000_BENES",
    "amblnc_pct": "BENES_AMBLNC_PCT", "amblnc_events": "AMBLNC_EVNTS_PER_1000_BENES",
}

AGE_75_PLUS = ["AGE_75_TO_79_BENES", "AGE_80_TO_84_BENES", "AGE_85_TO_89_BENES",
               "AGE_90_TO_94_BENES", "AGE_GT_94_BENES"]
AGE_85_PLUS = ["AGE_85_TO_89_BENES", "AGE_90_TO_94_BENES", "AGE_GT_94_BENES"]

key = S.key


def num(v):
    """CMS suppresses small cells as '*'; anything unparseable becomes missing."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def iv(v):
    """int(), but a suppressed or missing CMS cell stays missing instead of crashing."""
    return None if v is None else int(v)


def load(raw, name):
    with open(os.path.join(raw, name), encoding="utf-8") as f:
        return json.load(f)


def build_geometry(cfg, raw):
    """Project this state's county rings into a fixed-width SVG viewBox."""
    with open(os.path.join(raw, "us_counties.geojson"), encoding="utf-8") as f:
        feats = [x for x in json.load(f)["features"] if x["id"].startswith(cfg["fips"])]

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
            "lon0": lon0, "lon1": lon1, "lat0": lat0, "lat1": lat1, "c": out}, len(feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    args = ap.parse_args()
    code = args.state.upper()
    cfg = S.get(code)
    raw = os.path.join(ROOT, cfg["raw"])
    pre = cfg["name"].lower() + "_"
    additive = cfg["mc_mode"] == "additive"

    gv_file = "al_geovar.json" if code == "AL" else f"{code.lower()}_geovar.json"
    en_file = "al_enrollment.json" if code == "AL" else f"{code.lower()}_enrollment.json"
    nh_file = "al_nursing_homes.json" if code == "AL" else f"{code.lower()}_nursing_homes.json"

    geovar = {r["BENE_GEO_CD"]: r for r in load(raw, gv_file)}
    enrollment = load(raw, en_file)
    latest = max(r["YEAR"] for r in enrollment)
    base_year = str(int(latest) - GROWTH_YEARS)
    enroll = {r["BENE_FIPS_CD"].strip(): r for r in enrollment if r["YEAR"] == latest}
    prior = {r["BENE_FIPS_CD"].strip(): r for r in enrollment if r["YEAR"] == base_year}

    sup = cfg["load_supply"](raw)
    fixes = cfg.get("county_fixes", {})
    if fixes:
        bad = sup["county"].map(key).isin(fixes)
        if bad.any():
            sup.loc[bad, "county"] = sup.loc[bad, "county"].map(lambda c: fixes[key(c)])
            print(f"  applied {int(bad.sum())} county-name correction(s) from states.py")
    sup["ckey"] = sup["county"].map(key)

    nh = {}
    for r in load(raw, nh_file):
        d = nh.setdefault(key(r.get("countyparish") or ""), {"fac": 0, "bed": 0.0, "res": 0.0})
        d["fac"] += 1
        d["bed"] += num(r.get("number_of_certified_beds")) or 0
        d["res"] += num(r.get("average_number_of_residents_per_day")) or 0

    # Supply aggregated per county, under this state's own rule for memory care.
    agg = {}
    for ck, g in sup.groupby("ckey"):
        # A state may license an adjacent category on entirely separate terms -- Kentucky's
        # personal care homes are an OIG licence counted in beds, where assisted living is a
        # DAIL certification counted in units. Those are tracked beside the headline supply,
        # never inside it, because adding them would add two different quantities together.
        other = g[g["kind"] == "PCH"]
        g = g[g["kind"] != "PCH"]
        if additive:
            mc_bed = int(g.loc[g["kind"] == "MC", "beds"].sum())
            alf_bed = int(g.loc[g["kind"] != "MC", "beds"].sum())
            mc_fac = int((g["kind"] == "MC").sum())
            alf_fac = int((g["kind"] != "MC").sum())
            sl_bed = alf_bed + mc_bed
        else:
            sl_bed = int(g["beds"].sum())
            mc_bed = int(g["mc_beds"].sum())
            alf_bed = sl_bed - mc_bed          # capacity outside the memory-care certificate
            alf_fac = int(len(g))
            mc_fac = int((g["mc_beds"] > 0).sum())
        agg[ck] = dict(sl_bed=sl_bed, mc_bed=mc_bed, alf_bed=alf_bed,
                       alf_fac=alf_fac, mc_fac=mc_fac, sl_fac=int(len(g)),
                       pch_bed=int(other["beds"].sum()), pch_fac=int(len(other)))

    rows = []
    for fips, g in geovar.items():
        e = enroll.get(fips)
        if not e or g["BENE_GEO_DESC"].endswith("-UNKNOWN"):
            continue
        county = g["BENE_GEO_DESC"][3:]
        ck = key(county)
        total = num(e["TOT_BENES"])
        a75 = sum(num(e[c]) or 0 for c in AGE_75_PLUS)
        p = prior.get(fips)
        a = agg.get(ck, dict(sl_bed=0, mc_bed=0, alf_bed=0, alf_fac=0, mc_fac=0, sl_fac=0,
                             pch_bed=0, pch_fac=0))

        d = {"county": county, "fips": fips,
             "enroll": iv(total), "ma": iv(num(e["MA_AND_OTH_BENES"])),
             "om": iv(num(e["ORGNL_MDCR_BENES"])), "dual": iv(num(e["DUAL_TOT_BENES"])),
             "a75": int(a75), "a85": int(sum(num(e[c]) or 0 for c in AGE_85_PLUS)),
             "ffs_benes": iv(num(g["BENES_OM_CNT"])) or 0,
             "nh_fac": nh.get(ck, {}).get("fac", 0),
             "nh_bed": int(nh.get(ck, {}).get("bed", 0)),
             "nh_res": round(nh.get(ck, {}).get("res", 0), 1)}
        d.update(a)
        d["ma_pct"] = round(d["ma"] / total, 4) if d["ma"] is not None and total else None
        d["dual_pct"] = round(d["dual"] / total, 4) if d["dual"] is not None and total else None

        if p:
            p_tot = num(p["TOT_BENES"])
            p_a75 = sum(num(p[c]) or 0 for c in AGE_75_PLUS)
            d["enroll_p"] = int(p_tot)
            d["a75_p"] = int(p_a75)
            d["g5_enroll"] = round(total / p_tot - 1, 4) if p_tot else None
            d["g5_a75"] = round(a75 / p_a75 - 1, 4) if p_a75 else None
        else:
            d["enroll_p"] = d["a75_p"] = d["g5_enroll"] = d["g5_a75"] = None

        for dest, src in GV_FIELDS.items():
            d[dest] = num(g[src])
        for b in BUCKETS:
            d["pc_" + b.lower()] = num(g[b + "_MDCR_PYMT_PC"])
        d["home_pc"] = round(sum(d["pc_" + b] or 0 for b in HOME), 2)
        d["acute_pc"] = round(sum(d["pc_" + b] or 0 for b in ACUTE), 2)
        d["inst_pc"] = round(sum(d["pc_" + b] or 0 for b in INST), 2)
        d["eol_pc"] = d["pc_hospc"]

        d["sl_per1k"] = round(d["sl_bed"] / a75 * 1000, 2) if a75 else 0.0
        d["nh_per1k"] = round(d["nh_res"] / a75 * 1000, 2) if a75 else 0.0
        d["per_bed"] = round(a75 / d["sl_bed"], 1) if d["sl_bed"] else None
        d["mc_share"] = round(d["mc_bed"] / d["sl_bed"], 4) if d["sl_bed"] else None
        d["nh_occ"] = round(d["nh_res"] / d["nh_bed"], 4) if d["nh_bed"] else None
        rows.append(d)

    rows.sort(key=lambda r: -r["enroll"])

    t = lambda k2: sum((r[k2] or 0) for r in rows)
    state_rate = t("sl_bed") / t("a75") * 1000
    for r in rows:
        r["bed_gap"] = round(r["a75"] * state_rate / 1000 - r["sl_bed"])

    known = {key(r["county"]) for r in rows}
    for label, src in [("licensed", set(agg)), ("nursing home", set(nh))]:
        missing = [c for c in src if c and c not in known]
        if missing:
            raise SystemExit(
                f"unjoined {label} counties: {missing}\n"
                "  A source spelled a county in a way the FIPS join does not recognise.\n"
                f"  Verify the real county, then add it to county_fixes for {code} in states.py.")

    # ---- facilities, one row per licence ----
    fips_by_ck = {key(r["county"]): r["fips"] for r in rows}
    facs = []
    for _, r in sup.iterrows():
        lat, lon = r.get("lat"), r.get("lon")
        facs.append({
            "id": str(r["fac_id"]), "name": r["name"], "kind": r["kind"],
            # The map category is the loader's `kind` as-is, so a state can declare
            # categories the others do not have (Missouri's residential care, Kentucky's
            # personal care homes). Only an additive state's memory care is special:
            # elsewhere memory care is a subset column, not a category of its own.
            "type": r["kind"] if (additive or r["kind"] != "MC") else "AL",
            "cls": r["cls"], "beds": int(r["beds"]), "mc_beds": int(r["mc_beds"]),
            "addr": r["addr"], "city": r["city"], "zip": r["zip"],
            "county": r["county"], "fips": fips_by_ck.get(r["ckey"]),
            "admin": r["admin"], "phone": r["phone"],
            "owner": r.get("owner", ""), "status": r.get("status", ""),
            "mgmt": r.get("mgmt", ""),
            "lat": None if pd.isna(lat) else round(float(lat), 5),
            "lon": None if pd.isna(lon) else round(float(lon), 5),
            "prec": "street" if not pd.isna(lat) else None,
        })

    with open(os.path.join(OUT, pre + "master.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    with open(os.path.join(OUT, pre + "master.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    geo, nfeat = build_geometry(cfg, raw)
    with open(os.path.join(OUT, pre + "geo.json"), "w", encoding="utf-8") as f:
        json.dump(geo, f, separators=(",", ":"))
    # Carry forward coordinates already resolved for this facility id, so rebuilding
    # never discards geocoding work or re-requests it.
    fac_path = os.path.join(OUT, pre + "facilities.json")
    if os.path.exists(fac_path):
        with open(fac_path, encoding="utf-8") as f:
            prev = {x["id"]: x for x in json.load(f)}
        kept = 0
        for x in facs:
            old_row = prev.get(x["id"])
            if old_row and x["lat"] is None and old_row.get("lat") is not None:
                x["lat"], x["lon"] = old_row["lat"], old_row["lon"]
                x["prec"] = old_row.get("prec")
                kept += 1
        if kept:
            print(f"  kept {kept} previously resolved coordinate(s)")
    with open(fac_path, "w", encoding="utf-8") as f:
        json.dump(facs, f, separators=(",", ":"))

    lbl = cfg["labels"]
    print(f"{cfg['name']}: {len(rows)} counties ({nfeat} mapped), {len(rows[0])} fields each")
    print(f"  enrollment {latest} (growth vs {base_year}) | enrollees {t('enroll'):,} "
          f"({t('ma')/t('enroll'):.1%} Medicare Advantage)")
    print(f"  aged 75+ {t('a75'):,} | aged 85+ {t('a85'):,}")
    print(f"  FFS spend ${t('tot_amt')/1e9:.2f}B over {t('ffs_benes'):,} benes "
          f"= ${t('tot_amt')/t('ffs_benes'):,.0f} each")
    n_main = int((sup["kind"] != "PCH").sum())
    print(f"  {n_main:,} certifications | {lbl['total']} {t('sl_bed'):,} | "
          f"{lbl['mc']} {t('mc_bed'):,} ({cfg['mc_mode']})")
    if t("pch_fac"):
        print(f"  {t('pch_fac'):,} personal care homes | {t('pch_bed'):,} beds "
              f"(separate licence, tracked alongside)")
    print(f"  nursing homes {t('nh_fac'):,} | {t('nh_res'):,.0f} residents")
    print(f"  {t('a75')/t('sl_bed'):.0f} people aged 75+ per bed ({state_rate:.1f} per 1,000)")
    print(f"  {sum(1 for r in rows if r['sl_bed'] == 0)} counties with no licensed capacity")
    short = [r for r in rows if r["bed_gap"] > 0]
    print(f"  {len(short)} counties below the state rate, "
          f"{sum(r['bed_gap'] for r in short):,} beds short in total")


if __name__ == "__main__":
    main()
