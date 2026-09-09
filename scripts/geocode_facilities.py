#!/usr/bin/env python3
"""Fill in any missing coordinates for a state's licensed communities.

    python scripts/geocode_facilities.py --state TX

Reads and rewrites data/<state>_facilities.json in place, touching only rows that
have no coordinates. States that publish their own coordinates (Texas) therefore
cost one small request for the handful of gaps; states that publish none (Alabama)
get the whole file geocoded.

Uses the US Census batch geocoder, which is public, free and needs no key. Addresses
that do not match a street segment fall back to the centroid of their own city's
matched siblings, then to their county's centroid. Every row carries a `prec` field
of street / city / county so the map can draw its confidence rather than implying a
precision it does not have.
"""
import argparse
import csv
import io
import json
import os
import sys
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import states as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BENCHMARK = "Public_AR_Current"
CHUNK = 900
UA = "alabama-communities facility geocoder"
key = S.key


def post_batch(rows):
    """One multipart POST of (id, street, city, state, zip); returns id -> (lon, lat)."""
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"benchmark\"\r\n\r\n"
            f"{BENCHMARK}\r\n").encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"addressFile\"; "
             f"filename=\"a.csv\"\r\nContent-Type: text/csv\r\n\r\n").encode()
    body += buf.getvalue().encode() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BATCH_URL, body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as r:
        text = r.read().decode("utf-8", "replace")
    found = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 6 and row[2] == "Match" and "," in row[5]:
            lon, lat = row[5].split(",")[:2]
            found[row[0]] = (float(lon), float(lat))
    return found


def county_centroids(cfg):
    """Rough lat/lon centre of each county in the state, for last-resort placement."""
    raw = os.path.join(ROOT, cfg["raw"], "us_counties.geojson")
    with open(raw, encoding="utf-8") as f:
        feats = [x for x in json.load(f)["features"] if x["id"].startswith(cfg["fips"])]
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
    ap.add_argument("--state", required=True)
    args = ap.parse_args()
    code = args.state.upper()
    cfg = S.get(code)
    path = os.path.join(DATA, cfg["name"].lower() + "_facilities.json")
    with open(path, encoding="utf-8") as f:
        facs = json.load(f)

    missing = [f for f in facs if f.get("lat") is None or f.get("lon") is None]
    print(f"{cfg['name']}: {len(facs)} communities, {len(missing)} without coordinates")
    if not missing:
        print("  nothing to do")
        return

    rows = [(f["id"], f["addr"], f["city"], code, str(f.get("zip") or "").split("-")[0])
            for f in missing]
    found = {}
    for i in range(0, len(rows), CHUNK):
        found.update(post_batch(rows[i:i + CHUNK]))
        print(f"  geocoded {len(found)}/{len(rows)}")

    # A city centroid built from that city's own placed communities keeps an unmatched
    # address in the right town rather than dropping it off the map entirely.
    by_city = {}
    for f in facs:
        lon = found.get(f["id"], (None, None))[0] if f["id"] in found else f.get("lon")
        lat = found.get(f["id"], (None, None))[1] if f["id"] in found else f.get("lat")
        if lat is not None and lon is not None:
            by_city.setdefault(key(f["city"]), []).append((lon, lat))
    city_mid = {c: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
                for c, v in by_city.items()}
    cnty_mid = county_centroids(cfg)

    counts = {"street": 0, "city": 0, "county": 0, "none": 0}
    for f in facs:
        if f.get("lat") is not None and f.get("lon") is not None:
            f.setdefault("prec", "street")
            counts[f["prec"]] = counts.get(f["prec"], 0) + 1
            continue
        if f["id"] in found:
            f["lon"], f["lat"] = (round(x, 5) for x in found[f["id"]])
            f["prec"] = "street"
        elif key(f["city"]) in city_mid:
            f["lon"], f["lat"] = (round(x, 5) for x in city_mid[key(f["city"])])
            f["prec"] = "city"
        elif key(f["county"]) in cnty_mid:
            f["lon"], f["lat"] = (round(x, 5) for x in cnty_mid[key(f["county"])])
            f["prec"] = "county"
        else:
            f["prec"] = "none"
        counts[f["prec"]] = counts.get(f["prec"], 0) + 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(facs, f, separators=(",", ":"))
    print(f"  precision now: {counts['street']} street, {counts['city']} city, "
          f"{counts['county']} county, {counts.get('none',0)} unplaced")
    if counts.get("none"):
        print("  unplaced rows keep null coordinates and are skipped by the map")


if __name__ == "__main__":
    main()
