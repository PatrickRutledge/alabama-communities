#!/usr/bin/env python3
"""Build a state's pages from src/*.template.html plus that state's merged data.

    python scripts/build_site.py --state AL          -> index.html, facilities.html
    python scripts/build_site.py --state TX          -> texas/index.html, texas/facilities.html
    python scripts/build_site.py --all               -> every configured state
    python scripts/build_site.py --state TX --artifact

The templates carry no state-specific prose. Every figure in the copy -- totals, rates,
counts, the Medicare Advantage share -- is computed here from that state's own master
data, so a state's words can never drift from its numbers. That was the standing
maintenance hazard when the Alabama copy was hand-written.

`--artifact` writes dist/<state>-*.artifact.html: the same pages with data inlined but
no document shell, for a host that supplies its own <head> and theme stamp.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import states as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DATA = os.path.join(ROOT, "data")
DIST = os.path.join(ROOT, "dist")

SITE = "https://patrickrutledge.github.io/alabama-communities/"
REPO = "https://github.com/PatrickRutledge/alabama-communities"

COUNTY_SLIM = ["fips", "county", "a75", "bed_gap"]

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
           "%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%A1%3C/text%3E%3C/svg%3E")

SHELL_CSS = """
  html{-webkit-text-size-adjust:100%}
  body{margin:0}
  img{max-width:100%}
  [hidden]{display:none!important}
  #themeToggle{position:fixed;top:14px;right:14px;z-index:80;
    font-family:"Libre Franklin","Helvetica Neue",Arial,sans-serif;font-size:11px;font-weight:600;
    letter-spacing:.08em;text-transform:uppercase;padding:7px 12px;cursor:pointer;border-radius:2px;
    background:var(--surface);color:var(--ink-2);border:1px solid var(--rule-2)}
  #themeToggle:hover{color:var(--accent);border-color:var(--accent)}
  @media print{#themeToggle{display:none}}
"""

THEME_JS = """
(function(){
  var root=document.documentElement, btn=document.getElementById('themeToggle');
  var saved=null;
  try{saved=localStorage.getItem('atlas-theme')}catch(e){}
  if(saved==='dark'||saved==='light')root.setAttribute('data-theme',saved);
  function dark(){
    var t=root.getAttribute('data-theme');
    return t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);
  }
  function label(){btn.textContent=dark()?'Light':'Dark';
    btn.setAttribute('aria-label','Switch to '+(dark()?'light':'dark')+' theme')}
  btn.addEventListener('click',function(){
    var next=dark()?'light':'dark';
    root.setAttribute('data-theme',next);
    try{localStorage.setItem('atlas-theme',next)}catch(e){}
    label();
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change',label);
  label();
})();
"""

n = lambda v: f"{round(v):,}"


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def totals(rows, facs, cfg):
    """Everything the prose quotes, computed once from the state's own data."""
    t = lambda k: sum((r.get(k) or 0) for r in rows)
    additive = cfg["mc_mode"] == "additive"
    sl, a75 = t("sl_bed"), t("a75")
    short = [r for r in rows if (r.get("bed_gap") or 0) > 0]
    d = {
        "counties": len(rows), "enroll": t("enroll"),
        "ma_pct": t("ma") / t("enroll") if t("enroll") else 0,
        "a75": a75, "a85": t("a85"),
        "spend": t("tot_amt"), "ffs": t("ffs_benes"),
        "pc": t("tot_amt") / t("ffs_benes") if t("ffs_benes") else 0,
        "sl_bed": sl, "mc_bed": t("mc_bed"), "alf_bed": t("alf_bed"),
        "licences": len(facs) if facs else t("sl_fac"),
        "alf_fac": t("alf_fac"), "mc_fac": t("mc_fac"),
        "nh_fac": t("nh_fac"), "nh_bed": t("nh_bed"), "nh_res": t("nh_res"),
        "rate": sl / a75 * 1000 if a75 else 0,
        "per_bed": a75 / sl if sl else 0,
        "zero": sum(1 for r in rows if not r.get("sl_bed")),
        "short_n": len(short), "short_beds": sum(r["bed_gap"] for r in short),
        "additive": additive,
    }
    # Where the fee-for-service dollar goes, weighted by FFS beneficiaries.
    for k in ("home_pc", "acute_pc", "inst_pc", "eol_pc"):
        num = sum((r.get(k) or 0) * r["ffs_benes"] for r in rows)
        d[k] = num / d["ffs"] if d["ffs"] else 0
    d["pc_sum"] = d["home_pc"] + d["acute_pc"] + d["inst_pc"] + d["eol_pc"]
    return d


def caveat(cfg, T):
    """The four limits, phrased for this state's own licence structure."""
    nm, lbl = cfg["name"], cfg["labels"]
    if T["additive"]:
        mc = (f"{nm} licenses memory care separately as a {lbl['licence']}, so a memory-care "
              f"bed and an assisted-living bed are different beds and the two counts add up.")
    else:
        mc = (f"{nm} licenses one assisted living facility and certifies some of its beds for "
              f"Alzheimer's care, so {lbl['mc'].lower()} is a <b>subset</b> of licensed capacity "
              f"and is never added to it.")
    return f'''<div class="caveat">
  <h3>Read this before you read the numbers</h3>
  <ul>
    <li><b>Medicare does not record where a beneficiary lives.</b> Claims identify the <i>service</i> billed, never the residence. Someone in independent living, in assisted living, or in their own house is indistinguishable in this data, and no public CMS file splits spend by residential setting. So the residence measures here come from state licensure, and the spend measures are county-wide.</li>
    <li><b>Independent living is invisible on purpose.</b> {nm} does not license IL &mdash; it is housing, not care, so there is no registry and no bed count. The closest honest proxy is the <b>75+ and 85+ enrollee counts</b> ({n(T['a75'])} and {n(T['a85'])} here) set against licensed capacity: that gap is your addressable population.</li>
    <li><b>&ldquo;Skilled nursing&rdquo; here means post-acute SNF, not the nursing home.</b> Medicare covers up to 100 days after a qualifying hospital stay. Long-term custodial care is paid by Medicaid and out of pocket and never appears in these dollars &mdash; which means most of the savings from keeping someone out of a nursing home accrue to <b>Medicaid</b>, not Medicare.</li>
    <li class="ok"><b>What Medicare savings do look like is on this page:</b> fewer inpatient stays, lower readmission rates, fewer ER visits, fewer SNF days per 1,000, and a heavier tilt toward home health and hospice. Those five are the measurable case for aging in place, and they vary by more than two-fold across {nm} counties.</li>
    <li><b>Spend is Original Medicare only, and {nm} is {T['ma_pct']*100:.0f}% Medicare Advantage.</b> CMS publishes no county-level MA spending, so the ${T['spend']/1e9:.2f}B here covers only the {n(T['ffs'])} fee-for-service beneficiaries. Per-capita figures are per FFS beneficiary with full Part A and B &mdash; not per enrollee.</li>
    <li><b>How this state counts memory care.</b> {mc} Every figure on this page follows {nm}'s own definitions; nothing is converted to another state's categories.</li>
  </ul>
</div>'''


def footer(cfg, T, page):
    nm = cfg["name"]
    rows = [
        ("Enrollment", "CMS Medicare Monthly Enrollment, annual 2025 &mdash; dataset "
                       "d7fabe1e-d19b-4333-9eff-e80e0643f2fd. Growth compares 2025 with 2020."),
        ("Spend &amp; use", "CMS Medicare Geographic Variation by National, State &amp; County, "
                            "2024 &mdash; dataset 6219697b-8f6c-4164-bed4-cd9317c58ebc, "
                            "Original Medicare only"),
        ("Nursing homes", f"CMS Care Compare Provider Information &mdash; {n(T['nh_fac'])} "
                          f"{nm} facilities, certified beds and average daily residents"),
        ("Communities", f"{cfg['source']} &mdash; {n(T['licences'])} active licences, "
                        f"{n(T['sl_bed'])} {cfg['capacity_word']}, retrieved September 2026"),
        ("Bed gap", f"Beds required to reach {nm}'s own statewide rate of {T['rate']:.1f} per "
                    f"1,000 enrollees aged 75+. Benchmarked against this state's average rather "
                    f"than an outside industry target, so it needs no assumption beyond this data."),
        ("Definitions", f"All categories are {nm}'s own. Licence classes are not converted to "
                        f"another state's scheme, and totals here should not be added to another "
                        f"state's without deciding what the sum means."),
    ]
    if page == "facilities" and not cfg["geocode"]:
        rows.insert(4, ("Coordinates", f"Published by {cfg['source'].split(' Directory')[0]} "
                                       f"with the directory; no geocoding step required."))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    return f'<footer><h3>Sources &amp; vintage</h3><dl>{dl}</dl></footer>'


def note(cfg, T, facs):
    """The bed map's honesty note, written for how this state's data actually arrived."""
    nm, lbl = cfg["name"], cfg["labels"]
    if cfg["geocode"]:
        prec = {}
        for f in facs:
            prec[f.get("prec")] = prec.get(f.get("prec"), 0) + 1
        geo = (f"<b>On the dots.</b> {prec.get('street',0)} of the {len(facs)} communities "
               f"geocode to a street address. The remaining {len(facs)-prec.get('street',0)} sit "
               f"on newer streets the Census address file does not carry; those are placed at the "
               f"centre of their own city ({prec.get('city',0)}) or county ({prec.get('county',0)}) "
               f"and are drawn with a hollow ring rather than a solid fill. Bed counts, names, "
               f"licence class and administrators are exact in every case &mdash; only the pin "
               f"position is approximate.")
    else:
        geo = (f"<b>On the dots.</b> Coordinates are published by the state with the directory "
               f"itself, so every one of the {len(facs)} communities sits at its own recorded "
               f"position and nothing here is geocoded or approximated.")
    if T["additive"]:
        lic = (f"<b>On the licence classes.</b> {nm} licenses memory care separately as a "
               f"{lbl['licence']}, and many campuses hold both licences at one address &mdash; two "
               f"licences with two separate bed counts, which add together. Rather than stack one "
               f"dot invisibly on another, co-located licences are nudged onto a tiny ring so both "
               f"stay clickable.")
    else:
        lic = (f"<b>On the licence classes.</b> {nm} issues one assisted living licence per "
               f"community and certifies part of its capacity for Alzheimer's care. That "
               f"{lbl['mc'].lower()} is a <b>subset</b> of the community's licensed capacity, so a "
               f"community with 80 beds of which 30 are Alzheimer-certified has 80 beds, not 110. "
               f"Dots are sized by total licensed capacity, and the memory-care figure is shown "
               f"inside each record.")
    return f'<div class="note">{geo} {lic}</div>'


def cfg_js(cfg, T):
    lbl = cfg["labels"]
    return {
        "name": cfg["name"], "abbr": [k for k, v in S.STATES.items() if v is cfg][0],
        "mcMode": cfg["mc_mode"],
        "overrides": {
            "sl_bed": {"l": lbl["total"], "d": f"Total licensed {cfg['capacity_word']}"},
            "mc_bed": {"l": lbl["mc"],
                       "d": ("Licensed memory care beds, a separate licence" if T["additive"]
                             else "Capacity certified for Alzheimer's care, a subset of the total")},
            "alf_bed": {"l": ("Assisted living beds" if T["additive"]
                              else "Capacity outside the Alzheimer certificate")},
            "mc_fac": {"l": ("Memory care facilities" if T["additive"]
                             else "Communities with Alzheimer capacity")},
            "mc_share": {"l": lbl["mc_share"]},
            "sl_per1k": {"l": lbl["per1k"],
                         "d": f"Licensed {cfg['capacity_word']} per 1,000 enrollees aged 75 and over"},
            "per_bed": {"l": "People 75+ per bed",
                        "d": f"Enrollees aged 75+ for every licensed bed. Higher means thinner supply."},
            "bed_gap": {"d": (f"Beds needed to reach {cfg['name']}'s statewide rate of "
                              f"{T['rate']:.1f} per 1,000 aged 75+. Positive means under-supplied.")},
        },
        "shade": {"beds": f"Total {cfg['capacity_word']}", "albeds": lbl.get("total"),
                  "mcbeds": lbl["mc"], "per1k": lbl["per1k"]},
        "unit": cfg["capacity_word"],
        "extra": cfg.get("extra_measures", []),
        "types": cfg.get("types") or [
            {"k": "AL", "label": "Assisted living"},
            {"k": "MC", "label": lbl["mc"]},
        ],
    }


def nav_html(cfg, current):
    items = []
    for code, c in S.STATES.items():
        items.append((c["out_prefix"] + "index.html", c["name"]))
    links = []
    for href, label in items:
        mark = ' aria-current="page"' if href == current else ""
        links.append(f'<a href="{SITE}{href}"{mark}>{label}</a>')
    links.append(f'<a href="{SITE}{cfg["out_prefix"]}facilities.html"'
                 f'{" aria-current=\"page\"" if current.endswith("facilities.html") else ""}>'
                 f'{cfg["name"]} bed map</a>')
    links.append(f'<a href="{REPO}#readme" target="_blank" rel="noopener">Data &amp; sources</a>')
    return f'<nav class="nav">{"".join(links)}</nav>'


def build(code, artifact):
    cfg = S.get(code)
    pre = cfg["name"].lower() + "_"
    rows = load(pre + "master.json")
    geo = load(pre + "geo.json")
    facs = load(pre + "facilities.json")
    T = totals(rows, facs, cfg)
    CJ = cfg_js(cfg, T)
    nm = cfg["name"]

    pages = [
        {"tpl": "atlas.template.html", "out": "index.html", "kind": "atlas",
         "title": f"{nm} Senior Care Atlas",
         "desc": (f"Medicare demand, cost and licensed senior-housing supply for all "
                  f"{T['counties']} {nm} counties: 85 measures on an interactive heat map, "
                  f"plus the assisted living and memory care bed gap."),
         "h1": f"{nm} Senior Care Atlas",
         "eyebrow": (f"<b>{nm}</b><span>{T['counties']} counties</span>"
                     f"<span>Enrollment 2025</span><span>Claims 2024</span>"
                     f"<span>Licensure Sep 2026</span>"),
         "dek": (f"Medicare demand, cost and licensed senior-housing supply for every county in "
                 f"{nm} &mdash; built to show where independent living, assisted living and "
                 f"memory care have room to grow, and what Medicare actually spends where they "
                 f"don't. Every category is {nm}'s own."),
         "data": {"/*__DATA__*/ null": rows, "/*__GEO__*/ null": geo, "/*__CFG__*/ null": CJ}},
        {"tpl": "facilities.template.html", "out": "facilities.html", "kind": "facilities",
         "title": f"{nm} Senior Living Bed Map",
         "desc": (f"Every licensed assisted living and memory care community in {nm}, mapped and "
                  f"sized by licensed beds, zoomable to community name, bed count, licence class "
                  f"and administrator."),
         "h1": f"{nm} Senior Living Bed Map",
         "eyebrow": (f"<b>{nm}</b><span>{n(T['licences'])} licensed communities</span>"
                     f"<span>{n(T['sl_bed'])} {cfg['capacity_word']}</span>"
                     f"<span>Licensure Sep 2026</span>"),
         "dek": (f"Every licensed assisted living and memory care community in {nm}, placed on the "
                 f"map and sized by licensed beds. Counties are shaded by total capacity. Zoom "
                 f"into a hotspot to read community names, bed counts, licence class and "
                 f"administrator."),
         "data": {"/*__FAC__*/ null": facs, "/*__GEO__*/ null": geo, "/*__CFG__*/ null": CJ,
                  "/*__CNTY__*/ null": [{k: r[k] for k in COUNTY_SLIM} for r in rows]}},
    ]

    for pg in pages:
        with open(os.path.join(SRC, pg["tpl"]), encoding="utf-8") as f:
            tpl = f.read()
        for token, payload in pg["data"].items():
            if token not in tpl:
                raise SystemExit(f"{pg['tpl']} is missing {token}")
            tpl = tpl.replace(token, json.dumps(payload, separators=(",", ":")))
        rel = cfg["out_prefix"] + pg["out"]
        tpl = (tpl.replace("<!--TITLE-->", pg["title"])
                  .replace("<!--H1-->", pg["h1"])
                  .replace("<!--EYEBROW-->", pg["eyebrow"])
                  .replace("<!--DEK-->", pg["dek"])
                  .replace("<!--SOURCES-->", "".join(
                      f"<span>{x}</span>" for x in
                      ["CMS Monthly Enrollment", "CMS Geographic Variation PUF",
                       "CMS Care Compare", cfg["source"].split(" Directory")[0]]))
                  .replace("<!--CAVEAT-->", caveat(cfg, T))
                  .replace("<!--NOTE-->", note(cfg, T, facs))
                  .replace("<!--FOOTER-->", footer(cfg, T, pg["kind"]))
                  .replace("<!--NAV-->", nav_html(cfg, rel)))

        if artifact:
            os.makedirs(DIST, exist_ok=True)
            out = os.path.join(DIST, f"{code.lower()}-{pg['out'].replace('.html','')}.artifact.html")
            body = tpl
        else:
            split = tpl.index("</style>") + len("</style>")
            head, rest = tpl[:split], tpl[split:]
            out = os.path.join(ROOT, rel)
            os.makedirs(os.path.dirname(out) or ROOT, exist_ok=True)
            body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{pg['desc']}">
<meta property="og:title" content="{pg['title']}">
<meta property="og:description" content="{pg['desc']}">
<meta property="og:type" content="website">
<link rel="icon" href="{FAVICON}">
{head}
<style>{SHELL_CSS}</style>
</head>
<body>
<button id="themeToggle" type="button">Dark</button>
{rest}
<script>{THEME_JS}</script>
</body>
</html>
"""
        with open(out, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"  {os.path.relpath(out, ROOT).replace(os.sep,'/'):40} "
              f"{os.path.getsize(out)/1024:>4.0f} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--artifact", action="store_true")
    a = ap.parse_args()
    codes = sorted(S.STATES) if a.all else [a.state]
    if not codes or codes == [None]:
        raise SystemExit("pass --state XX or --all")
    for c in codes:
        print(f"{S.get(c)['name']}{' (artifact)' if a.artifact else ''}:")
        build(c, a.artifact)


if __name__ == "__main__":
    main()
