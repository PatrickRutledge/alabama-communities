#!/usr/bin/env python3
"""Build index.html from src/atlas.template.html plus the merged data.

Pass --artifact to write dist/atlas.artifact.html instead: the same page with the
data inlined but no document shell, for a host that supplies its own <head> and
light/dark theme stamp.

The template is authored to run both as a Claude Artifact (where the host supplies
the document shell and the light/dark theme stamp) and as a standalone page. This
script supplies what the host would otherwise provide: a document shell, a base
reset, a favicon, and a theme toggle -- then inlines the data so the published
page is a single file with no runtime fetches.

Run:  python scripts/build_site.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "src", "atlas.template.html")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "index.html")
OUT_ARTIFACT = os.path.join(ROOT, "dist", "atlas.artifact.html")

TITLE = "Alabama Senior Care Atlas"
DESCRIPTION = ("Medicare demand, cost and licensed senior-housing supply for all 67 Alabama "
               "counties: an interactive map, a filterable heatmap, and the assisted living "
               "and memory care supply gap.")

# The page exposes every measure in the merge, so the whole row ships. At 67 counties
# and ~90 short numeric fields this costs well under 100 KB and removes a whole class
# of bug where the measure catalogue references a field the payload dropped.
FIELDS = None  # None = ship every field

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


def main():
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    with open(os.path.join(DATA, "alabama_master.json"), encoding="utf-8") as f:
        rows = json.load(f)
    with open(os.path.join(DATA, "al_geo.json"), encoding="utf-8") as f:
        geo = json.load(f)

    for token in ("/*__DATA__*/ null", "/*__GEO__*/ null"):
        if token not in tpl:
            raise SystemExit(f"template is missing the {token} placeholder")

    slim = rows if FIELDS is None else [{k: r[k] for k in FIELDS} for r in rows]
    tpl = tpl.replace("/*__DATA__*/ null", json.dumps(slim, separators=(",", ":")))
    tpl = tpl.replace("/*__GEO__*/ null", json.dumps(geo, separators=(",", ":")))

    if "--artifact" in sys.argv:
        os.makedirs(os.path.dirname(OUT_ARTIFACT), exist_ok=True)
        with open(OUT_ARTIFACT, "w", encoding="utf-8") as f:
            f.write(tpl)
        print(f"dist/atlas.artifact.html  {os.path.getsize(OUT_ARTIFACT)/1024:.0f} KB "
              f"({len(slim)} counties)")
        return

    # The template's own <style> ends the head material; everything after it is body.
    split = tpl.index("</style>") + len("</style>")
    head, body = tpl[:split], tpl[split:]

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{DESCRIPTION}">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESCRIPTION}">
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
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html  {os.path.getsize(OUT)/1024:.0f} KB  ({len(slim)} counties)")


if __name__ == "__main__":
    main()
