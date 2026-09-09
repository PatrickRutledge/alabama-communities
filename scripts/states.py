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



# -------------------------------------------------------------------------- Kentucky

# 902 KAR 20:480 defines three assisted living certifications, and the abbreviations are
# not what they look like -- ALC-BH is "basic health", not behavioural health:
KY_TYPES = {
    "ALC":    "Social model assisted living community",
    "ALC-BH": "Assisted living with basic health and health-related services",
    "ALC-DC": "Assisted living with a secured dementia care unit",
}


def _ky_personal_care_homes(raw):
    """Parse the Personal Care Home directory PDF.

    A separate OIG licence from the DAIL assisted-living certification, and counted in
    BEDS where assisted living is counted in UNITS -- so these are carried as their own
    category and never added into the assisted-living totals.

    The BEDS and LICENSE EXPIRATION columns abut, so the extracted text stream merges
    them into one token ("2006/30/2027" = 20 beds expiring 06/30/2027). Words are read by
    x-position instead, and the merged token is split on its trailing 10-character date.
    """
    import pdfplumber
    COLS = [(0, 47, "lic"), (47, 220, "name"), (220, 333, "addr"), (333, 384, "city"),
            (384, 405, "zip"), (405, 449, "county"), (449, 563, "owner"),
            (563, 610, "adm1"), (610, 659, "adm2"), (659, 713, "phone"), (713, 999, "beds")]
    out = []
    with pdfplumber.open(os.path.join(raw, "ky_personal_care_homes.pdf")) as pdf:
        for page in pdf.pages:
            lines = {}
            for w in page.extract_words(use_text_flow=False, keep_blank_chars=False):
                lines.setdefault(round(w["top"] / 3), []).append(w)
            for k in sorted(lines):
                ws = sorted(lines[k], key=lambda w: w["x0"])
                if not re.match(r"^\d{6}$", ws[0]["text"]):
                    continue
                rec = {name: " ".join(w["text"] for w in ws if lo <= w["x0"] < hi)
                       for lo, hi, name in COLS}
                # The beds column runs into LICENSE EXPIRATION with no separator, and its x
                # drifts a few points row to row, so take everything past the phone number
                # and strip whichever expiration form is stuck to it: a date
                # ("2006/30/2027" = 20 beds) or the words "Pending Renewal"
                # ("57Pending Renewal" = 57 beds).
                rec["beds"] = "".join(w["text"] for w in ws if w["x0"] >= 706)
                v = re.sub(r"\d{2}/\d{2}/\d{4}$", "", rec["beds"].strip())
                v = re.sub(r"(?i)pending\s*renewal$", "", v).strip()
                m = re.match(r"^(\d+)$", v)
                if not m:
                    raise SystemExit(f"could not read bed count from {rec['beds']!r} "
                                     f"for {rec['name']!r}")
                rec["beds"] = int(m.group(1))
                out.append(rec)
    return out


def load_kentucky(raw):
    """DAIL assisted-living certifications (units) plus OIG personal care homes (beds)."""
    df = pd.read_excel(os.path.join(raw, "ky_alc_directory.xlsx"))
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    alc = pd.DataFrame({
        "fac_id": df["LICENSE #"].astype("Int64").astype(str),
        "name": df["NAME"].astype(str).str.strip(),
        # ALC-DC is a secured dementia care unit: memory care, certified separately from
        # the community's other beds, so it adds rather than overlapping.
        "kind": df["TYPE"].map(lambda t: "MC" if str(t).strip() == "ALC-DC" else "AL"),
        "cls": df["TYPE"].map(lambda t: KY_TYPES.get(str(t).strip(), str(t).strip())),
        "beds": pd.to_numeric(df["UNITS"], errors="coerce").fillna(0).astype(int),
        "mc_beds": 0,
        "addr": df["ADDRESS"].astype(str).str.strip(),
        "city": df["CITY"].astype(str).str.strip(),
        "zip": df["ZIP"].astype(str).str.split(".").str[0],
        "county": df["COUNTY"].astype(str).str.strip().str.title(),
        "admin": (df["ADM FIRST"].fillna("").astype(str).str.strip() + " "
                  + df["ADM LAST"].fillna("").astype(str).str.strip()).str.strip(),
        "phone": df["TELEPHONE"].fillna("").astype(str).str.strip(),
        "owner": "",
        "status": df["LICENSE EXPIRATION"].fillna("").astype(str).str.strip(),
        "lat": None, "lon": None,
    })
    pch = _ky_personal_care_homes(raw)
    pch = pd.DataFrame({
        "fac_id": [r["lic"] for r in pch],
        "name": [r["name"].title() for r in pch],
        "kind": "PCH",
        "cls": "Personal care home (separate OIG licence, counted in beds)",
        "beds": [r["beds"] for r in pch],
        "mc_beds": 0,
        "addr": [r["addr"].title() for r in pch],
        "city": [r["city"].title() for r in pch],
        "zip": [r["zip"] for r in pch],
        "county": [r["county"].title() for r in pch],
        "admin": [f"{r['adm1']} {r['adm2']}".strip().title() for r in pch],
        "phone": [r["phone"] for r in pch],
        "owner": [r["owner"] for r in pch],
        "status": "", "lat": None, "lon": None,
    })
    return pd.concat([alc, pch], ignore_index=True)


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
    "KY": {
        "name": "Kentucky",
        "fips": "21",
        "counties": 120,
        "county_word": "County",
        "raw": "data/raw-ky",
        "out_prefix": "ky/",
        "load_supply": load_kentucky,
        "mc_mode": "additive",
        # Kentucky certifies assisted living in UNITS -- an apartment, which may hold more
        # than one person -- where Alabama and Texas license BEDS. The two are not the same
        # quantity and per-1,000 rates are not comparable across that line.
        "capacity_word": "units",
        "labels": {
            "total": "Assisted living units",
            "mc": "Dementia care units",
            "mc_share": "Dementia care share of units",
            "per1k": "Assisted living units / 1k 75+",
            "licence": "secured dementia care unit certification (ALC-DC)",
        },
        # Three categories on the map: the two DAIL assisted-living certifications plus
        # the OIG personal care home licence, which is a different licence counted in a
        # different unit and is therefore shown beside them, never inside their totals.
        "types": [
            {"k": "AL", "label": "Assisted living (ALC / ALC-BH)"},
            {"k": "MC", "label": "Dementia care (ALC-DC)"},
            {"k": "PCH", "label": "Personal care home (beds)"},
        ],
        "extra_measures": [
            ["pch_bed", "Personal care home beds", "n", "seq",
             "Beds in licensed personal care homes -- a separate Kentucky licence, counted in beds where assisted living is counted in units, and never added to the unit totals"],
            ["pch_fac", "Personal care homes", "n", "seq",
             "Licensed personal care homes, a separate licence from assisted living"],
        ],
        "geocode": True,
        "source": "Kentucky Cabinet for Health and Family Services directories",
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
