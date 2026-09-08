#!/usr/bin/env python3
"""Build the site's pages from src/*.template.html plus the merged data.

  index.html       the county atlas -- 85 measures on a choropleth and a heatmap
  facilities.html  every licensed community as a point on a zoomable bed map

Pass --artifact to write dist/*.artifact.html instead: the same pages with data
inlined but no document shell, for a host that supplies its own <head> and
light/dark theme stamp.

Each template is authored to run in either setting. This script supplies what a
host would otherwise provide -- a document shell, a base reset, a favicon, a
cross-page nav and a theme toggle -- then inlines the data so each published page
is a single file with no runtime fetches.

Run:  python scripts/build_site.py [--artifact]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DATA = os.path.join(ROOT, "data")
DIST = os.path.join(ROOT, "dist")

SITE = "https://patrickrutledge.github.io/alabama-communities/"
REPO = "https://github.com/PatrickRutledge/alabama-communities"

# Absolute links so the nav works from a published artifact as well as from the site.
# The last entry leaves the site for the data dictionary, so it is an absolute repo URL.
NAV = [("index.html", "County atlas"), ("facilities.html", "Bed map"),
       (REPO + "#readme", "Data &amp; sources")]

PAGES = [
    {
        "template": "atlas.template.html",
        "out": "index.html",
        "title": "Alabama Senior Care Atlas",
        "description": ("Medicare demand, cost and licensed senior-housing supply for all 67 "
                        "Alabama counties: 85 measures on an interactive heat map, plus the "
                        "assisted living and memory care bed gap."),
        "data": {"/*__DATA__*/ null": "alabama_master.json", "/*__GEO__*/ null": "al_geo.json"},
    },
    {
        "template": "facilities.template.html",
        "out": "facilities.html",
        "title": "Alabama Senior Living Bed Map",
        "description": ("Every licensed assisted living and memory care community in Alabama, "
                        "mapped and sized by licensed beds, zoomable to community name, bed "
                        "count, licence class and administrator."),
        "data": {"/*__FAC__*/ null": "al_facilities.json", "/*__GEO__*/ null": "al_geo.json",
                 "/*__CNTY__*/ null": "_county_slim"},
    },
]

# The facilities map needs only a slice of the county merge for its shading and context.
COUNTY_SLIM = ["fips", "county", "a75", "bed_gap"]

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
           "%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%A1%3C/text%3E%3C/svg%3E")

# The Artifact host ships a small reset; standalone has to bring its own.
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


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def nav_html(current):
    parts = []
    for href, label in NAV:
        url = href if href.startswith("http") else SITE + href
        mark = ' aria-current="page"' if href == current else ""
        ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
        parts.append(f'<a href="{url}"{mark}{ext}>{label}</a>')
    return f'<nav class="nav">{"".join(parts)}</nav>'


def build(page, artifact):
    with open(os.path.join(SRC, page["template"]), encoding="utf-8") as f:
        tpl = f.read()

    for token, source in page["data"].items():
        if token not in tpl:
            raise SystemExit(f"{page['template']} is missing the {token} placeholder")
        if source == "_county_slim":
            payload = [{k: r[k] for k in COUNTY_SLIM} for r in load("alabama_master.json")]
        else:
            payload = load(source)
        tpl = tpl.replace(token, json.dumps(payload, separators=(",", ":")))

    tpl = tpl.replace("<!--NAV-->", nav_html(page["out"]))

    if artifact:
        os.makedirs(DIST, exist_ok=True)
        out = os.path.join(DIST, page["out"].replace(".html", ".artifact.html"))
        with open(out, "w", encoding="utf-8") as f:
            f.write(tpl)
    else:
        # The template's own <style> ends the head material; everything after it is body.
        split = tpl.index("</style>") + len("</style>")
        head, body = tpl[:split], tpl[split:]
        out = os.path.join(ROOT, page["out"])
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{page['description']}">
<meta property="og:title" content="{page['title']}">
<meta property="og:description" content="{page['description']}">
<meta property="og:type" content="website">
<link rel="icon" href="{FAVICON}">
{head}
<style>{SHELL_CSS}</style>
</head>
<body>
<button id="themeToggle" type="button">Dark</button>
{body}
<script>{THEME_JS}</script>
</body>
</html>
""")
    print(f"  {os.path.relpath(out, ROOT).replace(os.sep, '/'):34} "
          f"{os.path.getsize(out)/1024:>4.0f} KB")


def main():
    artifact = "--artifact" in sys.argv
    print("building artifact pages" if artifact else "building site pages")
    for page in PAGES:
        build(page, artifact)


if __name__ == "__main__":
    main()
