# Building the Senior Care Atlas

How the sites are generated, what each script does, and the decisions that are easy to
undo by accident. For what the data *means*, see the [main README](../README.md).

## Quick start

```bash
pip install pandas xlrd openpyxl

python scripts/fetch_data.py                        # Alabama's upstream sources
python scripts/build_state.py --state AL            # merge to data/alabama_*.json
python scripts/geocode_facilities.py --state AL     # fill any missing coordinates
python scripts/build_site.py --all                  # build every configured state
```

Every script except `fetch_data.py` takes `--state XX`. `build_site.py --all` builds all
configured states in one pass.

## Adding a state

Four things, in this order:

1. **Get the licensure file.** State health departments publish these as Excel, CSV or
   an Access database, usually behind an interactive portal rather than a plain link.
   Put it in `data/raw-<state>/`.
2. **Fetch the CMS half.** Enrollment, spend and nursing homes are national files
   filtered by FIPS — identical work for every state, no state-specific code.
3. **Write a loader in `scripts/states.py`.** One function returning a normalised frame,
   plus a config entry declaring the state's own vocabulary and its `mc_mode`.
4. **Build.** `build_state.py --state XX`, then `geocode_facilities.py --state XX` if the
   state publishes no coordinates, then `build_site.py --state XX`.

The templates carry no state-specific prose, so nothing in `src/` needs touching.

### `mc_mode` is the decision that matters

It declares how a state's memory care relates to its total capacity, and getting it
wrong silently corrupts every capacity figure on the site:

- `"additive"` (Alabama) — memory care is a **separate licence** with its own beds, so
  total capacity is assisted living plus memory care.
- `"subset"` (Texas) — memory care is a **certification covering some of an existing
  licence's beds**, so it is already inside total capacity and must never be added.

Two more per-state hooks, both optional:

- `types` declares the licence categories the bed map colours and filters by. Kentucky
  uses three because its personal care homes are a different licence in a different unit;
  omit it and the map falls back to assisted living plus memory care.
- `extra_measures` appends measures only that state has (Kentucky's personal care home
  beds and facility counts) to the atlas catalogue, so no state carries another's rows.

Rows whose `kind` is `PCH` are aggregated separately in `build_state.py` and never enter
`sl_bed`. That is deliberate: Kentucky's assisted living is measured in units and its
personal care homes in beds, and adding them would sum two different quantities.

`capacity_word` sets the noun used throughout a state's pages — "beds" for Alabama,
"licensed capacity" for Texas, "units" for Kentucky.

Under `subset`, a community with 80 beds of which 30 are Alzheimer-certified has 80
beds. Treating Texas as additive would invent 21,655 beds that do not exist.

Nothing needs an API key. `fetch_data.py` takes a few minutes, mostly waiting on the
3 MB county GeoJSON and the two ADPH report exports.

Add `--artifact` to the last step to write `dist/*.artifact.html` instead: the same pages
with data inlined but no document shell, for a host that supplies its own `<head>` and
light/dark theme stamp (a Claude Artifact, for instance).

`data/raw/` and `dist/` are gitignored. The derived outputs in `data/` are committed, so
a fresh clone can run `build_site.py` alone and get working pages without touching the
network.

## Repository layout

```
index.html                     Alabama atlas (the site root, for URL stability)
facilities.html                Alabama bed map
tx/index.html                  Texas atlas
tx/facilities.html             Texas bed map
README.md                      data dictionary, terms and sources (linked from every page)
docs/BUILDING.md               this file

src/atlas.template.html        county atlas source — state-neutral, placeholder-driven
src/facilities.template.html   bed map source — state-neutral

scripts/states.py              per-state config and licensure loaders
scripts/fetch_data.py          downloads Alabama's upstream sources
scripts/build_state.py         joins one state into county rows, projects its geometry
scripts/geocode_facilities.py  fills missing coordinates via the US Census geocoder
scripts/build_site.py          generates each state's prose, inlines data, writes pages

data/<state>_master.{json,csv} one row per county, 93 fields
data/<state>_facilities.json   one row per licence, with coordinates and precision flags
data/<state>_geo.json          county SVG paths plus that state's projection bounds
data/raw/, data/raw-tx/        upstream downloads (gitignored)
dist/                          artifact-flavoured builds (gitignored)
```

The Texas output directory is , not . On a case-insensitive filesystem
 folds into a  research folder sitting beside it, and the built pages end
up mixed in with the source spreadsheet. GitHub Pages is case-sensitive, so that mismatch
would 404 in production while looking fine locally.

### Prose is generated, not written

Every figure in a page's copy — totals, rates, the Medicare Advantage share, the bed
gap benchmark — is computed in `build_site.py` from that state's own master data and
injected through `<!--CAVEAT-->`, `<!--FOOTER-->`, `<!--EYEBROW-->` and friends. This
replaced hand-written numbers in the templates, which was the one maintenance hazard
the earlier Alabama build carried: copy that could quietly disagree with its own data.

Measure labels follow the same rule. `CFG.overrides` in the injected config renames
supply measures per state, so Texas shows "Alzheimer-certified capacity" where Alabama
shows "Memory care beds", from one template.

## The pipeline

### `fetch_data.py`

Five sources into `data/raw/`:

| Output | Source |
| --- | --- |
| `al_enrollment.json` | CMS Medicare Monthly Enrollment, Alabama counties, annual rows, all years |
| `al_geovar.json` | CMS Geographic Variation PUF, county level, filtered to Alabama |
| `al_nursing_homes.json` | CMS Care Compare Provider Information, Alabama |
| `al_assisted_living.xls`, `al_memory_care.xls` | ADPH Facilities Directory, types D and P |
| `us_counties.geojson` | Plotly's US county boundaries |

Both CMS dataset ids are "latest vintage" ids that stay stable across annual refreshes,
so re-running picks up a newer enrollment year on its own. The Geographic Variation pull
is pinned by `GEOVAR_YEAR` at the top of the file — bump it when CMS publishes a new one.

The Geographic Variation API has no state column at county level; county names are
prefixed `AL-`, so the script pulls the national county set for the year and filters
locally.

**The ADPH scrape is the fragile part.** Their Facilities Directory is an ASP.NET
WebForms app with *cookieless* sessions: the session id is embedded in the URL path as
`(S(...))`, not in a cookie. The facility-type selection lives in server-side session
state rather than in the report query string, so the sequence is:

1. `GET /FacilitiesDirectory/` and keep the session-stamped URL it redirects to
2. POST the dropdown selection back to that same URL, carrying `__VIEWSTATE`,
   `__EVENTVALIDATION` and `__EVENTTARGET`
3. POST again to commit the "Export to Excel" report type
4. `GET <session-stamped root>/ReportView.aspx?Report=FacilitiesDirectory`

Requesting the report from the unstamped root returns "The session has expired" even
with a cookie jar attached. If ADPH ever changes their form control names, step 2 is
where it will break; the control names are spelled out in the script.

### `build_master.py`

Joins the four data sources into one row per county and writes the projected geometry.

**County joins.** The three sources spell counties three different ways — `DeKalb`,
`Dekalb`, `De Kalb`. Enrollment and Geographic Variation join on 5-digit FIPS. Facility
and nursing-home data have no FIPS, so they join on a letters-only key
(`re.sub(r"[^a-z]", "", name.lower())`). The script **exits with an error** if any
facility county fails to join, rather than silently dropping beds — if you see
`unjoined nursing home counties: [...]`, a source changed a spelling and the fix is the
key function, not the data.

**Suppressed cells.** CMS writes `*` for small cells. `num()` turns anything unparseable
into `None`, which flows through to `null` in JSON and an empty cell in the CSV. Do not
replace these with zero — a suppressed cell means "too few people to report", not "none".

**Spend bundles.** The 17 service buckets roll up into four groups defined at the top of
the file. `INST` is post-acute only (SNF, IRF, LTCH) — deliberately, because Medicare
pays no custodial long-term care and no bundle here should be read as a nursing home
stay.

**Bed gap** is computed in a second pass, after the state rate is known from the summed
rows. It benchmarks against Alabama's own average rather than an outside industry
target, so the measure needs no assumption beyond this dataset.

**Growth** compares the latest enrollment year with `GROWTH_YEARS` earlier (5). Prior-year
totals are carried through as `enroll_p` and `a75_p` so the site can compute *true*
statewide growth from state totals rather than averaging 67 county rates.

**Projection.** County rings are projected equirectangular with a `cos(lat)` correction
into a 600 × 957 viewBox. At Alabama's span the distortion is invisible, and it needs no
projection library. The bounds (`lon0`, `lon1`, `lat0`, `lat1`) are written into
`al_geo.json` alongside the paths, and the bed map projects facility points with the
identical formula — **that shared bounds object is what keeps dots inside the right
county.** If you change the projection, change it once here and both maps follow.

The upstream GeoJSON is already generalized, so there is no simplification pass. An
earlier attempt at Douglas–Peucker collapsed every ring to two points, because the first
and last point of a closed ring are identical and the perpendicular-distance test
degenerates. Don't re-add it without handling that.

### `geocode_facilities.py`

Geocodes communities through the US Census batch geocoder (public, free, no key), in
chunks of 900. Reads the scraped Excel exports by default; `--csv PATH` accepts a
hand-supplied ADPH CSV export instead. Both produce identical output.

Roughly 90% match a street segment. Non-matches fall back to the centroid of their own
city's matched siblings, then to the county centroid, and every record carries a `prec`
field of `street`, `city` or `county` so the map can draw its confidence honestly rather
than implying precision it does not have. A retry pass through the one-line geocoder was
tried and recovered 1 of 10, so it is not in the script — the remaining failures are new
subdivisions absent from the Census address file, and no amount of address normalizing
fixes that.

### `build_site.py`

Inlines the data into each template and wraps it in a document shell. Pages are declared
in the `PAGES` list — template, output name, title, description, and which placeholder
takes which data file. Adding a page means adding an entry there and a template.

The whole county row ships to the atlas (`FIELDS = None`). At 67 counties and ~90 short
numeric fields that costs well under 100 KB and removes a class of bug where the measure
catalogue references a field the payload dropped. The bed map takes only a four-field
slice of the county data, listed in `COUNTY_SLIM`.

Each template is authored to run either standalone or inside a host that provides the
document shell. The standalone build adds `<!doctype>`, meta and OG tags, a base reset,
an emoji favicon, and a theme toggle. Templates therefore must not carry their own
`<html>`, `<head>` or `<body>`.

The cross-page nav uses **absolute** URLs to the published site, so it works from a
published artifact as well as from GitHub Pages. `SITE` at the top of the file is the
one place to change if the site moves.

## Site-specific notes

### Theme

Every colour is a CSS custom property declared on bare `:root`, then redefined in two
places: `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`,
and `:root[data-theme="dark"]`. That covers all three viewer states — explicit light,
explicit dark, and the unstamped default where only the media query applies. A colour
whose only definition sits inside one of those blocks will render one theme's text on the
other theme's background. Charts and maps re-render on a `MutationObserver` watching
`data-theme` plus a `prefers-color-scheme` listener, because SVG fills are resolved at
draw time, not by CSS.

### The county atlas measure catalogue

All 85 measures are declared in one `CAT` array near the top of the atlas template:
`[key, label, format, shading mode, description]`, grouped by category. Adding a measure
means adding a field in `build_master.py` and one line in `CAT` — nothing else. Shading
mode is `seq` (low to high, septile breaks) or `div` (against the state average, ±4/12/25%
bands).

State averages are computed per measure by type: ratios from their component sums,
counts as a plain per-county mean, growth from state totals, and everything else weighted
by FFS beneficiaries. That weighting matters — an unweighted mean lets Greene County
(577 FFS beneficiaries) count as much as Jefferson (34,085).

The measure tables in the main README were generated from this array. If you add
measures, regenerate them rather than hand-editing.

### The bed map's zoom

Two non-obvious things make clustered dots readable, and both are easy to undo:

**Dot radius is divided by `zoom ** 0.78`.** Radius in plain map units means dots and the
gaps between them magnify together, so a cluster looks exactly as crowded at 40× as at
1×. Dividing by a power of the zoom holds a dot near its screen size while the map grows
underneath, which is what actually pulls a cluster apart. The exponent is below 1 on
purpose, so a zoomed-in dot still grows a little and doesn't look undersized against the
enlarged county beneath it. Dots set their own `stroke-width` at creation time, because
`drawDots()` runs after `applyTransform()` and would otherwise inherit an unscaled stroke.

**Co-located licences are nudged onto a small ring.** 156 licences across 71 addresses
share exact coordinates, because a campus commonly holds both an ALF and a SCALF licence.
Identical points cannot be separated by any zoom level, so one dot would sit permanently
invisible under another. The nudge is 1.5 map units, invisible statewide and cleanly
separated once zoomed.

Labels appear past 2.5× zoom with simple bounding-box collision detection, biggest
communities placed first, so dense areas show the communities that matter rather than an
unreadable pile.

### Layout

The bed map runs full width at up to `88vh`, with the legend in a fixed 206px gutter to
its left. Alabama's tall, narrow shape letterboxes badly in a wide container, and that
gutter is space the map cannot use anyway. Below 960px the shell flips to
`column-reverse` so the map stays above its legend.

## Updating to a new data vintage

1. Bump `GEOVAR_YEAR` in `fetch_data.py` when CMS publishes a new Geographic Variation
   file. Enrollment picks up its latest year automatically.
2. Re-run the four scripts in order.
3. Check the `build_master.py` summary output against the previous run. The county count
   should stay 67; a change in facility counts is real, a change in *unjoined* counties
   is a bug.
4. Update the figures quoted in `README.md`. The pages themselves regenerate their own
   numbers, so only the README needs a human pass.
