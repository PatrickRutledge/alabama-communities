# Alabama Senior Care Atlas

Medicare demand, cost and licensed senior-housing supply for all 67 Alabama counties,
built as a single self-contained page: an interactive county map, a filterable heatmap,
a per-county profile, and a supply-versus-institutional-intensity scatter.

**Live site:** https://patrickrutledge.github.io/alabama-communities/

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
| People aged 75+ per licensed AL/memory-care bed | 39 |
| Counties with **no** licensed assisted living or memory care | **18** |

Where the fee-for-service dollar goes: acute hospital 50.2%, home and community 35.3%,
institutional post-acute 7.6%, hospice 5.6%.

## Sources

| Source | Vintage | Used for |
| --- | --- | --- |
| [CMS Medicare Monthly Enrollment](https://data.cms.gov/summary-statistics-on-beneficiary-enrollment/medicare-and-medicaid-reports/medicare-monthly-enrollment) (`d7fabe1e…`) | annual 2025 | enrollees, MA share, age bands, dual eligibility |
| [CMS Medicare Geographic Variation by National, State & County](https://data.cms.gov/medicare-geographic-comparisons/medicare-geographic-variation-by-national-state-county) (`6219697b…`) | 2024 | spend by service bucket, utilization rates |
| [CMS Care Compare Provider Information](https://data.cms.gov/provider-data/dataset/4pq5-n9py) (`4pq5-n9py`) | current | nursing home certified beds and average daily residents |
| [Alabama ADPH Facilities Directory](https://dph1.adph.state.al.us/FacilitiesDirectory/) | Sep 2026 | licensed ALF and SCALF facilities and beds |
| [Plotly US county GeoJSON](https://github.com/plotly/datasets) | — | county boundaries for the map |

**On SCALF:** Specialty Care Assisted Living Facility is Alabama's license class for
dementia and Alzheimer's care, counted here as memory care. Many SCALFs share an address
with an ALF and are licensed separately, so facility counts exceed distinct campuses.

All sources are public and require no API key.

## Rebuilding

```bash
pip install pandas xlrd
python scripts/fetch_data.py     # pull all five sources into data/raw/
python scripts/build_master.py   # merge to data/alabama_master.{json,csv} + al_geo.json
python scripts/build_site.py     # inline the data into index.html
```

`data/raw/` is gitignored; the derived outputs are committed so the site builds without
a network round trip. To move to a newer CMS vintage, bump `GEOVAR_YEAR` in
`scripts/fetch_data.py` — the enrollment feed picks up its latest year automatically.

## Layout

```
index.html                  built site — single file, no runtime fetches
src/atlas.template.html     page source with /*__DATA__*/ placeholders
scripts/fetch_data.py       downloads the five upstream sources
scripts/build_master.py     joins them into one row per county
scripts/build_site.py       inlines data, adds document shell and theme toggle
data/alabama_master.csv     67 counties x 50 fields, for spreadsheets
data/alabama_master.json    same, as the site consumes it
data/al_geo.json            county boundaries projected to SVG paths
```

### A note on the two joins

Counties are joined on 5-digit FIPS where available. The three sources spell counties
three different ways — `DeKalb`, `Dekalb`, `De Kalb` — so supply data joins on a
letters-only key instead. `build_master.py` fails loudly if any facility county does
not join, rather than silently dropping beds.

The ADPH directory is an ASP.NET WebForms app using *cookieless* sessions: the session
id lives in the URL path as `(S(...))`, and the facility-type selection is held in
server-side session state rather than in the report query string. `fetch_data.py`
documents the sequence.

## License

Code is MIT. The underlying data is public domain (CMS, a US federal agency) and public
record (Alabama Department of Public Health); neither is covered by this repository's
license and both should be cited to their source.
