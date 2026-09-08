#!/usr/bin/env python3
"""Fetch every upstream source the atlas is built from into data/raw/.

Sources
  1. CMS Medicare Monthly Enrollment .......... county enrollee counts, by year
  2. CMS Medicare Geographic Variation PUF .... county spend + utilization (FFS)
  3. CMS Care Compare Provider Information .... nursing home beds and residents
  4. Alabama ADPH Facilities Directory ........ licensed ALF and SCALF beds
  5. Plotly US county GeoJSON ................. county boundaries

Everything here is public data and needs no API key. Run:  python scripts/fetch_data.py
"""
import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

# CMS dataset identifiers. Both are "latest vintage" ids -- CMS keeps these stable
# across annual refreshes, so re-running this script picks up a newer year on its own.
ENROLLMENT_ID = "d7fabe1e-d19b-4333-9eff-e80e0643f2fd"
GEOVAR_ID = "6219697b-8f6c-4164-bed4-cd9317c58ebc"
NURSING_HOME_ID = "4pq5-n9py"

STATE = "AL"
GEOVAR_YEAR = "2024"  # latest year published in the Geographic Variation PUF

UA = "Mozilla/5.0 (alabama-communities data build)"


def get(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def save(name, payload):
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, name)
    mode = "wb" if isinstance(payload, bytes) else "w"
    with open(path, mode, **({} if isinstance(payload, bytes) else {"encoding": "utf-8"})) as f:
        f.write(payload)
    print(f"  -> {name} ({os.path.getsize(path)/1024:.0f} KB)")
    return path


def fetch_enrollment():
    """County-level Medicare enrollment for Alabama, all years, annual rows only."""
    print("CMS Medicare Monthly Enrollment")
    url = (
        f"https://data.cms.gov/data-api/v1/dataset/{ENROLLMENT_ID}/data"
        f"?filter[BENE_STATE_ABRVTN]={STATE}&filter[BENE_GEO_LVL]=County"
        f"&filter[MONTH]=Year&size=5000"
    )
    rows = json.loads(get(url))
    years = sorted({r["YEAR"] for r in rows})
    print(f"  {len(rows)} rows, years {years[0]}-{years[-1]}")
    save("al_enrollment.json", json.dumps(rows))
    return years[-1]


def fetch_geovar():
    """County-level Original Medicare spend and utilization, filtered to Alabama.

    The API has no state column at county level -- county names are prefixed
    'AL-', so pull the national county set for the year and filter locally.
    """
    print("CMS Medicare Geographic Variation PUF")
    url = (
        f"https://data.cms.gov/data-api/v1/dataset/{GEOVAR_ID}/data"
        f"?filter[BENE_GEO_LVL]=County&filter[YEAR]={GEOVAR_YEAR}"
        f"&filter[BENE_AGE_LVL]=All&size=5000"
    )
    rows = json.loads(get(url))
    al = [r for r in rows if r["BENE_GEO_DESC"].startswith(f"{STATE}-")]
    print(f"  {len(rows)} US counties -> {len(al)} in Alabama")
    save("al_geovar.json", json.dumps(al))


def fetch_nursing_homes():
    """Certified beds and average daily residents for every Alabama nursing home."""
    print("CMS Care Compare Provider Information")
    url = (
        f"https://data.cms.gov/provider-data/api/1/datastore/query/{NURSING_HOME_ID}/0"
        f"?conditions[0][property]=state&conditions[0][value]={STATE}"
        f"&conditions[0][operator]==&limit=1000"
    )
    payload = json.loads(get(url))
    print(f"  {payload.get('count')} facilities")
    save("al_nursing_homes.json", json.dumps(payload["results"]))


def fetch_adph():
    """Licensed assisted living (D) and specialty care / memory care (P) facilities.

    ADPH runs an ASP.NET WebForms app with *cookieless* sessions -- the session id
    is embedded in the URL path as (S(...)), so the report request has to be made
    against the same session-stamped root the search postback used. Selections live
    in server-side session state, not in the report query string.
    """
    print("Alabama ADPH Facilities Directory")
    base = "https://dph1.adph.state.al.us/FacilitiesDirectory/"

    def hidden(html):
        return dict(re.findall(r'name="(__[A-Z]+)"[^>]*value="([^"]*)"', html))

    for code, label in [("D", "assisted_living"), ("P", "memory_care")]:
        jar = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        op.addheaders = [("User-Agent", UA)]

        r = op.open(base, timeout=60)
        html = r.read().decode("utf-8", "replace")
        url = r.geturl()                      # carries the (S(sessionid)) path segment
        root = url.rsplit("/", 1)[0] + "/"

        form = hidden(html)
        form.update({
            "__EVENTTARGET": "ctl00$MainContent$DropDownListFacTypes",
            "__EVENTARGUMENT": "", "__LASTFOCUS": "",
            "__SCROLLPOSITIONX": "0", "__SCROLLPOSITIONY": "0",
            "ctl00$MainContent$RadioButtonListReportType": "Export to Excel",
            "ctl00$MainContent$DropDownListFacTypes": code,
            "ctl00$MainContent$DropDownListCounties": "(All)",
            "ctl00$MainContent$DropDownListCities": "(All)",
            "ctl00$MainContent$DropDownListLicenseStatus": "(All)",
        })
        post = lambda d: op.open(urllib.request.Request(
            url, urllib.parse.urlencode(d).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": url},
        ), timeout=90).read().decode("utf-8", "replace")

        html2 = post(form)
        # second postback commits the "Export to Excel" report type to session
        form2 = hidden(html2)
        form2.update({k: v for k, v in form.items() if k.startswith("ctl00")})
        form2.update({
            "__EVENTTARGET": "ctl00$MainContent$RadioButtonListReportType$2",
            "__EVENTARGUMENT": "", "__LASTFOCUS": "",
            "__SCROLLPOSITIONX": "0", "__SCROLLPOSITIONY": "0",
        })
        post(form2)

        body = op.open(root + "ReportView.aspx?Report=FacilitiesDirectory", timeout=180).read()
        if b"session has expired" in body:
            raise RuntimeError(f"ADPH session lost fetching {label}")
        save(f"al_{label}.xls", body)


def fetch_geometry():
    """US county boundaries; Alabama is filtered out at build time."""
    print("County boundary GeoJSON")
    save("us_counties.geojson", get(
        "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"))


if __name__ == "__main__":
    fetch_enrollment()
    fetch_geovar()
    fetch_nursing_homes()
    fetch_adph()
    fetch_geometry()
    print(f"\nAll sources written to {RAW}")
