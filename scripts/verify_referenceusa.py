#!/usr/bin/env python3
"""Sample ReferenceUSA records and check what their websites actually are.

    python scripts/verify_referenceusa.py --n 90

ReferenceUSA is a business directory, so a record's presence proves a business was
coded to an industry, not that a licensed senior living community exists at that
address today. This fetches a stratified sample of the websites and sorts them into:

    community    the site is a specific senior living community
    referral     a placement or referral service, not a community
    care_other   a care business, but home health / staffing / agency rather than housing
    unrelated    a live site with no senior housing content
    parked       domain registered but holding a for-sale or placeholder page
    unreachable  DNS failure, refused, timed out, or an HTTP error

    dns_fail     the domain does not resolve at all
    blocked      alive but refusing a scripted request (403/429/TLS)
    no_connect   refused or timed out
    http_error   reachable host, HTTP error on the page

Only dns_fail and parked are a closure signal. A 403 means the site is very much alive
and simply will not talk to a script -- large operators block scripted requests as a
matter of course, so counting those as closures would invent a closure rate out of bot
protection.

This samples; it does not verify the whole file. Nothing here substitutes for matching
against a state's licensure list.
"""
import argparse
import concurrent.futures as cf
import csv
import os
import re
import ssl
import urllib.error
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMBINED = os.path.join(ROOT, "reference-usa", "combined")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

COMMUNITY = re.compile(
    r"(?i)(assisted living|memory care|senior living|independent living|"
    r"retirement (community|living|home)|personal care home|our community|"
    r"schedule a tour|floor plans|respite care)")
REFERRAL = re.compile(
    r"(?i)(find (the right |a )?(senior|assisted)|placement (service|specialist)|"
    r"we help families find|no cost to you|referral service|compare communities|"
    r"local senior living advisors?)")
CARE_OTHER = re.compile(
    r"(?i)(home health|home care|in-home care|staffing|caregiver agency|"
    r"hospice|skilled nursing agency|medical supply)")
PARKED = re.compile(
    r"(?i)(domain (is )?for sale|buy this domain|parked (free|domain)|"
    r"godaddy|sedo|hugedomains|this domain may be for sale|under construction|"
    r"coming soon)")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE          # many small operators run expired certs


HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "close",
}


def fetch(url, timeout=15):
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read(220_000).decode("utf-8", "replace")


def classify(row):
    url = str(row["Website"]).strip()
    if not url:
        return "no_website", ""
    # A domain that does not resolve is genuinely gone. A 403 or 429 means the site is
    # very much alive and simply refusing a script -- counting those as closures would
    # invent a closure rate out of bot protection.
    try:
        html = fetch(url)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 406, 429, 503):
            return "blocked", f"HTTP {e.code}"
        return "http_error", f"HTTP {e.code}"
    except urllib.error.URLError as e:
        reason = str(getattr(e, "reason", e))
        if re.search(r"(?i)name (or service )?not known|getaddrinfo|nodename|"
                     r"no such host|temporary failure in name resolution", reason):
            return "dns_fail", "domain does not resolve"
        if re.search(r"(?i)certificate|ssl", reason):
            return "blocked", "tls problem"
        return "no_connect", reason[:40]
    except (ssl.SSLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
        return "no_connect", type(e).__name__
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)[:60_000]
    if PARKED.search(text) and not COMMUNITY.search(text):
        return "parked", ""
    if REFERRAL.search(text) and not COMMUNITY.search(text):
        return "referral", ""
    if COMMUNITY.search(text):
        return "community", ""
    if CARE_OTHER.search(text):
        return "care_other", ""
    return "unrelated", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=90, help="records to sample")
    ap.add_argument("--state", default=None)
    args = ap.parse_args()

    df = pd.read_csv(os.path.join(COMBINED, "referenceusa_all.csv"),
                     dtype=str, keep_default_na=False)
    if args.state:
        df = df[df["State"] == args.state.upper()]
    df = df[df["Website"].str.strip() != ""]

    # Stratify so the sample says something about each bucket, not just the biggest one.
    strata = [
        ("assisted_living", df["category"] == "assisted_living"),
        ("ccrc", df["category"] == "ccrc"),
        ("home_health", df["category"] == "home_health"),
        ("other_named", (df["category"] == "other") & (df["name_signal"] == "strong")),
        ("other_unnamed", (df["category"] == "other") & (df["name_signal"] != "strong")),
    ]
    picks = []
    per = max(6, args.n // len(strata))
    for label, mask in strata:
        g = df[mask]
        if len(g):
            s = g.sample(min(per, len(g)), random_state=7).copy()
            s["stratum"] = label
            picks.append(s)
    sample = pd.concat(picks, ignore_index=True)
    print(f"checking {len(sample)} websites across {sample['stratum'].nunique()} strata\n")

    results = []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(classify, r): r for _, r in sample.iterrows()}
        done = 0
        for fut in cf.as_completed(futs):
            r = futs[fut]
            try:
                verdict, note = fut.result()
            except Exception as e:
                verdict, note = "unreachable", type(e).__name__
            results.append({"stratum": r["stratum"], "category": r["category"],
                            "name_signal": r["name_signal"], "state": r["State"],
                            "name": r["Company Name"], "website": r["Website"],
                            "verdict": verdict, "note": note})
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(sample)}")

    out = pd.DataFrame(results)
    path = os.path.join(COMBINED, "referenceusa_website_check.csv")
    out.sort_values(["stratum", "verdict", "name"]).to_csv(path, index=False)

    print("\nVERDICT BY STRATUM")
    piv = pd.crosstab(out["stratum"], out["verdict"])
    print(piv.to_string())
    print("\nOVERALL")
    for v, n in out["verdict"].value_counts().items():
        print(f"  {n:>4}  {n/len(out)*100:>5.1f}%  {v}")
    dead = int(out["verdict"].isin(["unreachable", "parked"]).sum())
    print(f"\n  {dead} of {len(out)} sampled sites are dead or parked "
          f"({dead/len(out)*100:.0f}%) -- the closure/staleness signal.")
    print(f"  written to {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
