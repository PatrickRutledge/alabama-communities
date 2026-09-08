#!/usr/bin/env python3
"""Geocode every licensed assisted living and memory care facility to a point.

Reads   data/raw/al_assisted_living.xls + al_memory_care.xls  (scripts/fetch_data.py)
        or a hand-supplied ADPH CSV export via --csv PATH
Writes  data/al_facilities.json   one object per facility, with lat/lon

Uses the US Census batch geocoder, which is public, free and needs no key.
Addresses that do not match a street segment fall back to the centroid of their
city's matched siblings, then to the county centroid, and are flagged with a
`precision` field so the map can show how confident each point is.
"""
import argparse
import csv
import io
import json
import math
import os
import re
import urllib.request
import uuid

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "al_facilities.json")

BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BENCHMARK = "Public_AR_Current"
CHUNK = 900  # the service accepts 10,000 but smaller chunks fail less often

key = lambda c: re.sub(r"[^a-z]", "", str(c).lower())


def read_adph(csv_path=None):
    """Facility rows from either a supplied CSV export or the two scraped Excel files."""
    if csv_path:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    else:
        parts = [pd.read_excel(os.path.join(RAW, f))
                 for f in ("al_assisted_living.xls", "al_memory_care.xls")]
        df = pd.concat(parts, ignore_index=True)
    df.columns = [str(c).strip() for c in df.columns]
    df["Licensed Beds"] = pd.to_numeric(df["Licensed Beds"], errors="coerce").fillna(0).astype(int)
    return df


def post_batch(rows):
    """One multipart POST of (id, street, city, state, zip) rows; returns id -> (lon, lat)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows:
        w.writerow(r)
    payload = buf.getvalue().encode()

    boundary = uuid.uuid4().hex
    body = b""
    for name, value in [("benchmark", BENCHMARK)]:
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                 f"{value}\r\n").encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"addressFile\"; "
             f"filename=\"a.csv\"\r\nContent-Type: text/csv\r\n\r\n").encode()
    body += payload + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(BATCH_URL, body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "alabama-communities facility geocoder",
    })
    with urllib.request.urlopen(req, timeout=600) as r:
        text = r.read().decode("utf-8", "replace")

    found = {}
    for row in csv.reader(io.StringIO(text)):
        # id, input, match indicator, match type, matched address, "lon,lat", tiger id, side
        if len(row) >= 6 and row[2] == "Match" and "," in row[5]:
            lon, lat = row[5].split(",")[:2]
            found[row[0]] = (float(lon), float(lat), row[3])
    return found


def county_centroids():
    """Rough lat/lon centre of each Alabama county, for last-resort placement."""
    with open(os.path.join(RAW, "us_counties.geojson"), encoding="utf-8") as f:
        feats = [x for x in json.load(f)["features"] if x["id"].startswith("01")]
    out = {}
    for f in feats:
        g = f["geometry"]
        c = g["coordinates"]
        rings = [r for poly in c for r in poly] if g["type"] == "MultiPolygon" else list(c)
        pts = [p for r in rings for p in r]
        out[key(f["properties"]["NAME"])] = (
            sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="ADPH CSV export to use instead of the scraped Excel files")
    args = ap.parse_args()

    df = read_adph(args.csv)
    print(f"{len(df)} facilities, {df['Licensed Beds'].sum():,} licensed beds")

    rows = [(r["Fac ID"], r["Address Line 1"], r["City"], r["State"], str(r["ZIP"]).split(".")[0])
            for _, r in df.iterrows()]
    found = {}
    for i in range(0, len(rows), CHUNK):
        chunk = rows[i:i + CHUNK]
        found.update(post_batch(chunk))
        print(f"  geocoded {len(found)}/{len(rows)}")

    # Fallbacks. A city centroid built from that city's own matched facilities keeps an
    # unmatched address in the right town rather than dropping it off the map entirely.
    by_city = {}
    for _, r in df.iterrows():
        if r["Fac ID"] in found:
            lon, lat, _ = found[r["Fac ID"]]
            by_city.setdefault(key(r["City"]), []).append((lon, lat))
    city_mid = {c: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
                for c, v in by_city.items()}
    cnty_mid = county_centroids()

    fips_by_county = {}
    master = os.path.join(ROOT, "data", "alabama_master.json")
    if os.path.exists(master):
        with open(master, encoding="utf-8") as f:
            fips_by_county = {key(r["county"]): r["fips"] for r in json.load(f)}

    out, counts = [], {"street": 0, "city": 0, "county": 0, "none": 0}
    for _, r in df.iterrows():
        fid = r["Fac ID"]
        ck, ctyk = key(r["City"]), key(r["County"])
        if fid in found:
            lon, lat, how = found[fid]
            prec = "street"
        elif ck in city_mid:
            lon, lat = city_mid[ck]
            prec = "city"
        elif ctyk in cnty_mid:
            lon, lat = cnty_mid[ctyk]
            prec = "county"
        else:
            counts["none"] += 1
            continue
        counts[prec] += 1
        specialty = "(Specialty Care)" in str(r["Facility Type"])
        out.append({
            "id": fid,
            "name": str(r["Facility Name"]).strip(),
            "type": "MC" if specialty else "AL",
            "cls": str(r.get("Class 1") or "").strip(),
            "beds": int(r["Licensed Beds"]),
            "addr": str(r["Address Line 1"]).strip(),
            "city": str(r["City"]).strip(),
            "zip": str(r["ZIP"]).split(".")[0],
            "county": str(r["County"]).strip(),
            "fips": fips_by_county.get(ctyk),
            "admin": str(r["Administrator Name"]).strip(),
            "phone": str(r["Phone"]).strip(),
            "owner": str(r.get("Licensee Type") or "").strip(),
            "status": str(r.get("License Status") or "").strip(),
            "lon": round(lon, 5), "lat": round(lat, 5),
            "prec": prec,
        })

    out.sort(key=lambda x: -x["beds"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))

    al = [x for x in out if x["type"] == "AL"]
    mc = [x for x in out if x["type"] == "MC"]
    print(f"wrote {len(out)} facilities to data/al_facilities.json")
    print(f"  assisted living {len(al)} ({sum(x['beds'] for x in al):,} beds) | "
          f"memory care {len(mc)} ({sum(x['beds'] for x in mc):,} beds)")
    print(f"  precision: {counts['street']} street, {counts['city']} city, "
          f"{counts['county']} county, {counts['none']} unplaced")
    if not fips_by_county:
        print("  note: run build_master.py first to attach county FIPS")


if __name__ == "__main__":
    main()
