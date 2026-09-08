# Alabama Senior Care Atlas

Medicare demand, cost and licensed senior-housing supply for all 67 Alabama counties,
built as two self-contained pages.

| Page | What it is |
| --- | --- |
| **[County atlas](https://patrickrutledge.github.io/alabama-communities/)** | 85 measures on an interactive county heat map, a filterable table, per-county profiles, and a supply-versus-institutional-intensity scatter |
| **[Bed map](https://patrickrutledge.github.io/alabama-communities/facilities.html)** | All 292 licensed communities as points on a zoomable map, sized by beds — zoom a hotspot to read names, bed counts, licence class and administrators |

Built for senior-living market analysis — independent living, assisted living and
memory care — from public CMS and Alabama Department of Public Health data.

## What the data can and cannot tell you

This matters more than any number in the repo, so it is stated first.

**Medicare does not record where a beneficiary lives.** Claims identify the *service*
billed, never the residence. Someone in independent living, in assisted living, or in
their own house is indistinguishable in this data, and no public CMS file splits spend
by residential setting. So residence here comes from **state licensure**, and spend is
**county-wide**. The two are joined by county, not by person.

**Independent living has no data anywhere.** Alabama does not license IL — it is housing,
not care, so there is no registry and no bed count. The proxy used throughout is the
75+ and 85+ enrollee counts set against licensed AL and memory-care beds.

**"Skilled nursing" here means post-acute SNF, not the nursing home.** Medicare covers
up to 100 days after a qualifying hospital stay. Long-term custodial care is paid by
Medicaid and out of pocket and appears nowhere in these dollars — which means most of
the savings from keeping someone out of a nursing home accrue to **Medicaid**, not
Medicare. No spend bundle in this dataset represents a custodial nursing home stay.

**What Medicare-side savings do look like** is measurable and is on the page: inpatient
stays per 1,000, readmission rate, ER visits per 1,000, SNF days per 1,000, and the tilt
toward home health and hospice. Those five vary more than two-fold across Alabama counties.

**Spend is Original Medicare only, and Alabama is 60% Medicare Advantage.** CMS publishes
no county-level MA spending, so the $4.67B total is roughly a third of true Medicare spend
in the state. Every per-capita dollar is *per fee-for-service beneficiary with full Part A
and B* — not per enrollee. The two denominators differ by more than 3x in some counties.

## Statewide summary

| Measure | Value |
| --- | --- |
| Medicare enrollees (2025) | 1,133,996 — 60.4% Medicare Advantage |
| Aged 75+ / 85+ | 420,666 / 98,865 |
| Original Medicare spend (2024) | $4.67B, or $12,597 per FFS beneficiary |
| Assisted living | 185 facilities, 7,320 licensed beds |
| Memory care (SCALF) | 107 facilities, 3,499 licensed beds |
| Nursing homes | 224 facilities, 26,504 certified beds, 21,964 residents (83% full) |
| People aged 75+ per licensed AL/memory-care bed | 39 (statewide rate 25.7 beds per 1,000) |
| Counties with **no** licensed assisted living or memory care | **18** |
| Counties below the statewide bed rate | **49 of 67**, 1,947 beds short in total |

Where the fee-for-service dollar goes: acute hospital 50.2%, home and community 35.3%,
institutional post-acute 7.6%, hospice 5.6%.

## The bed map

Every licensed assisted living and memory care community in Alabama on one zoomable map,
running the full width of the page with the legend in the gutter beside the state outline.
Counties shade by total beds (or AL beds, memory care beds, community count, beds per 1,000
aged 75+, or bed gap); each community is a dot sized by licensed beds and coloured by licence
type. Scroll to zoom, drag to pan, click a county to fly to it, or use +/−/arrow keys with the
map focused. Community names appear past 2.5×, placed with collision detection so they stay
readable. Click any dot for the full record — licence class, administrator, phone, address,
licensee type and facility ID. The community record and the ranked list sit below the map.

**Dots hold their size on screen as you zoom** (radius divided by zoom^0.78) rather than
scaling with the map, so the gap between clustered communities grows while the dots do not —
which is what actually pulls a cluster apart. On top of that, 156 facilities across 71
addresses share exact coordinates, because a campus commonly holds both an ALF and a SCALF
licence. Those would stay permanently stacked at any zoom, so co-located licences are nudged
onto a small ring and each carries a badge saying how many licences share the address.

Filter by type, minimum bed count, county, or free text across name, city, county and
administrator. The ranked list beside the map follows the same filters and zooms to whatever
you click.

**Geocoding honesty:** 262 of 292 communities resolve to a street address through the US
Census geocoder. The other 30 sit on streets the Census address file does not yet carry;
those fall back to their own city's centroid (24) or their county's (6) and are drawn as
hollow rings rather than solid dots, with an "approx. location" badge on the record. Bed
counts, names, licence classes and administrators are exact in every case — only the pin
moves.

Note that many campuses hold both an ALF and a SCALF licence at one address, so they appear
as two dots at the same point. That is correct: two licences, two bed counts.

Biggest county capacity: Madison 1,528 beds, Jefferson 1,466, Baldwin 911, Mobile 756,
Shelby 681, Tuscaloosa 665. Eighteen counties have none at all.

## The heat map

Every one of the **85 measures** in the dataset can shade the county map — filter the list
by category (demand, opportunity, cost, hospital, post-acute, home and community, supply)
or search it by name. Alongside the map: the measure's Alabama average, median, and range;
a distribution strip showing where each county falls; and all 67 counties ranked. The same
85 measures are available as a sortable table, and clicking any county opens its full profile.

**Bed gap** is the market measure worth starting with. It is the number of assisted living
and memory care beds a county would need to reach Alabama's own statewide rate of 25.7 per
1,000 residents aged 75+. It is benchmarked against the state's own average rather than an
outside industry target, so it needs no assumption beyond this data. The largest gaps are
Elmore (135 beds), Russell (101), Dale (89), Mobile (82) and Chilton (74).

**Growth measures** compare 2025 with 2020. Statewide the 75+ cohort grew 19.5% while total
enrollment grew 6.7% — the demand curve is steepening. Lee (+36%), Baldwin (+34%) and
Shelby (+33%) are growing that cohort fastest among counties with a meaningful base.

## Sources

| Source | Vintage | Used for |
| --- | --- | --- |
| [CMS Medicare Monthly Enrollment](https://data.cms.gov/summary-statistics-on-beneficiary-enrollment/medicare-and-medicaid-reports/medicare-monthly-enrollment) (`d7fabe1e…`) | annual 2025 | enrollees, MA share, age bands, dual eligibility |
| [CMS Medicare Geographic Variation by National, State & County](https://data.cms.gov/medicare-geographic-comparisons/medicare-geographic-variation-by-national-state-county) (`6219697b…`) | 2024 | spend by service bucket, utilization rates |
| [CMS Care Compare Provider Information](https://data.cms.gov/provider-data/dataset/4pq5-n9py) (`4pq5-n9py`) | current | nursing home certified beds and average daily residents |
| [Alabama ADPH Facilities Directory](https://dph1.adph.state.al.us/FacilitiesDirectory/) | Sep 2026 | licensed ALF and SCALF facilities and beds |
| [Plotly US county GeoJSON](https://github.com/plotly/datasets) | — | county boundaries for the map |
| [US Census Geocoder](https://geocoding.geo.census.gov/) | Public_AR_Current | facility coordinates for the bed map |

**On SCALF:** Specialty Care Assisted Living Facility is Alabama's license class for
dementia and Alzheimer's care, counted here as memory care. Many SCALFs share an address
with an ALF and are licensed separately, so facility counts exceed distinct campuses.

All sources are public and require no API key.

## Rebuilding

```bash
pip install pandas xlrd
python scripts/fetch_data.py          # pull all five sources into data/raw/
python scripts/build_master.py        # merge to data/alabama_master.{json,csv} + al_geo.json
python scripts/geocode_facilities.py  # geocode communities to data/al_facilities.json
python scripts/build_site.py          # inline data into index.html + facilities.html
python scripts/build_site.py --artifact   # same pages without the document shell
```

`geocode_facilities.py` reads the scraped Excel exports by default; pass `--csv PATH` to use
a hand-supplied ADPH CSV export instead. Both produce identical output.

The `--artifact` form writes `dist/*.artifact.html` for hosts that supply their own `<head>`
and theme stamp (a Claude Artifact, for instance). Same pages, same data.

`data/raw/` is gitignored; the derived outputs are committed so the site builds without
a network round trip. To move to a newer CMS vintage, bump `GEOVAR_YEAR` in
`scripts/fetch_data.py` — the enrollment feed picks up its latest year automatically.

## Layout

```
index.html                     county atlas — single file, no runtime fetches
facilities.html                bed map — single file, no runtime fetches
src/atlas.template.html        atlas source with /*__DATA__*/ placeholders
src/facilities.template.html   bed map source
scripts/fetch_data.py          downloads the five upstream sources
scripts/build_master.py        joins them into one row per county
scripts/geocode_facilities.py  geocodes communities via the US Census geocoder
scripts/build_site.py          inlines data, adds document shell, nav and theme toggle
data/alabama_master.csv        67 counties x 93 fields, for spreadsheets
data/alabama_master.json       same, as the atlas consumes it
data/al_facilities.json        292 communities with coordinates and precision flags
data/al_geo.json               county boundaries as SVG paths, plus projection bounds
```

### A note on the two joins

Counties are joined on 5-digit FIPS where available. The three sources spell counties
three different ways — `DeKalb`, `Dekalb`, `De Kalb` — so supply data joins on a
letters-only key instead. `build_master.py` fails loudly if any facility county does
not join, rather than silently dropping beds.

The county map and the bed map share one projection. `build_master.py` writes the
projection bounds into `data/al_geo.json` alongside the county paths, and the bed map
projects each facility's lon/lat with the identical formula, so dots land inside the right
county rather than drifting.

The ADPH directory is an ASP.NET WebForms app using *cookieless* sessions: the session
id lives in the URL path as `(S(...))`, and the facility-type selection is held in
server-side session state rather than in the report query string. `fetch_data.py`
documents the sequence.

## License

Code is MIT. The underlying data is public domain (CMS, a US federal agency) and public
record (Alabama Department of Public Health); neither is covered by this repository's
license and both should be cited to their source.
