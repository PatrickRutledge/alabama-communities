#!/usr/bin/env python3
"""Per-state configuration.

Every state licenses senior housing on its own terms, and this project deliberately
does not flatten those definitions into a common schema -- a regional roll-up would
have to invent equivalences the states themselves do not recognise. So each state
carries its own supply loader, its own vocabulary, and its own rule for how memory
care relates to total capacity.

The two rules that differ most, and that silently corrupt any cross-state total:

  Alabama   two separate licences. An ALF bed and a SCALF (memory care) bed are
            different beds, so total capacity = ALF + SCALF. `mc_mode` = "additive".
  Texas     one ALF licence with an Alzheimer certification covering some of its
            beds. Alzheimer capacity is a SUBSET of total licensed capacity, never
            added to it. `mc_mode` = "subset".

Alabama also counts beds; Kentucky, when it lands, counts units. Do not sum across
states without deciding what the sum means.
"""
import os
import re

import pandas as pd

key = lambda c: re.sub(r"[^a-z]", "", str(c).lower())


# --------------------------------------------------------------------------- Alabama

def load_alabama(raw):
    """Two ADPH Excel exports: assisted living, and specialty care (memory care)."""
    frames = []
    for f, kind in [("al_assisted_living.xls", "AL"), ("al_memory_care.xls", "MC")]:
        df = pd.read_excel(os.path.join(raw, f))
        df.columns = [str(c).strip() for c in df.columns]
        df["kind"] = kind
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    return pd.DataFrame({
        "fac_id": df["Fac ID"].astype(str),
        "name": df["Facility Name"].astype(str).str.strip(),
        "kind": df["kind"],
        "cls": df["Class 1"].fillna("").astype(str).str.strip(),
        "beds": pd.to_numeric(df["Licensed Beds"], errors="coerce").fillna(0).astype(int),
        "mc_beds": 0,                       # memory care is its own licence row, not a subset
        "addr": df["Address Line 1"].astype(str).str.strip(),
        "city": df["City"].astype(str).str.strip(),
        "zip": df["ZIP"].astype(str).str.split(".").str[0],
        "county": df["County"].astype(str).str.strip(),
        "admin": df["Administrator Name"].fillna("").astype(str).str.strip(),
        "phone": df["Phone"].fillna("").astype(str).str.strip(),
        "owner": df["Licensee Type"].fillna("").astype(str).str.strip(),
        "status": df["License Status"].fillna("").astype(str).str.strip(),
        "lat": None, "lon": None,
    })


# ----------------------------------------------------------------------------- Texas

def load_texas(raw):
    """One HHSC directory export. Ships its own coordinates, so no geocoding needed."""
    df = pd.read_excel(os.path.join(raw, "tx_alf_directory.xlsx"), header=1)
    df.columns = [str(c).strip() for c in df.columns]
    geo = df["Geo Location"].astype(str).str.split(",", n=1, expand=True)
    cap = pd.to_numeric(df["Total Licensed Capacity"], errors="coerce").fillna(0).astype(int)
    az = pd.to_numeric(df["Alzheimer Capacity"], errors="coerce").fillna(0).astype(int)
    # One row reports more Alzheimer capacity than total licensed capacity, which cannot
    # be true of a subset. Clip rather than drop, and let the count surface in the build log.
    az = az.clip(upper=cap)
    return pd.DataFrame({
        "fac_id": df["Facility ID"].astype(str),
        "name": df["Facility Name"].astype(str).str.strip(),
        "kind": "ALF",
        "cls": df["Service  Type"].fillna("").astype(str).str.strip(),   # TYPE A / B / C
        "beds": cap,
        "mc_beds": az,                      # subset of `beds`, never added to it
        "addr": df["Physical Address"].astype(str).str.strip(),
        "city": df["Physical Address CITY"].astype(str).str.strip(),
        "zip": df["Physical Address Zipcode"].astype(str).str.split(".").str[0],
        "county": df["County"].astype(str).str.strip().str.title(),
        "admin": df["Administrator"].fillna("").astype(str).str.strip(),
        "phone": df["Facility Phone Number"].fillna("").astype(str).str.strip(),
        "owner": df["Type of Entity"].fillna("").astype(str).str.strip(),
        "status": "Active",                 # the directory lists active licences only
        "mgmt": df["Management Company_"].fillna("").astype(str).str.strip(),
        "lat": pd.to_numeric(geo[0], errors="coerce"),
        "lon": pd.to_numeric(geo[1], errors="coerce"),
    })


STATES = {
    "AL": {
        "name": "Alabama",
        "fips": "01",
        "counties": 67,
        "county_word": "County",
        "raw": "data/raw",
        "out_prefix": "",                  # Alabama publishes at the site root
        "load_supply": load_alabama,
        "mc_mode": "additive",
        "capacity_word": "beds",
        "labels": {
            "total": "AL + memory care beds",
            "mc": "Memory care beds",
            "mc_share": "Memory care share of beds",
            "per1k": "AL + memory care beds / 1k 75+",
            "licence": "Specialty Care Assisted Living Facility (SCALF)",
        },
        "geocode": True,                    # ADPH publishes no coordinates
        "source": "Alabama Department of Public Health Facilities Directory",
    },
    "TX": {
        "name": "Texas",
        "fips": "48",
        "counties": 254,
        "county_word": "County",
        "raw": "data/raw-tx",
        "out_prefix": "tx/",   # not "texas/": Windows would fold it into the Texas/ source folder
        "load_supply": load_texas,
        "mc_mode": "subset",
        "capacity_word": "licensed capacity",
        "labels": {
            "total": "Licensed capacity",
            "mc": "Alzheimer-certified capacity",
            "mc_share": "Alzheimer share of capacity",
            "per1k": "Licensed capacity / 1k 75+",
            "licence": "Alzheimer certification (a subset of the ALF licence)",
        },
        # Corrections for county names the source misspells, applied before joining.
        # MARAVILLA AT THE DOMAIN is filed under "Travis Country" (an Austin
        # neighbourhood); its ZIP 78758 and its own coordinates are both in Travis County.
        "county_fixes": {"traviscountry": "Travis"},
        "geocode": False,                   # HHSC ships coordinates
        "source": "Texas HHSC Directory of Assisted Living Facility Providers",
    },
}


def get(code):
    code = code.upper()
    if code not in STATES:
        raise SystemExit(f"unknown state {code}; known: {', '.join(sorted(STATES))}")
    return STATES[code]
