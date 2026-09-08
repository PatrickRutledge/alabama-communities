# Alabama Senior Care Atlas — data, terms and sources

What the numbers on these two pages mean, where each one comes from, and what they
cannot tell you. If you arrived here from a link on either page, this is the reference
for everything you saw there.

| Page | What it shows |
| --- | --- |
| **[County atlas](https://patrickrutledge.github.io/alabama-communities/)** | 85 measures on an interactive county heat map, a filterable table, a profile for each county, and a supply-versus-institutional-intensity scatter |
| **[Bed map](https://patrickrutledge.github.io/alabama-communities/facilities.html)** | All 292 licensed assisted living and memory care communities as points sized by beds, zoomable to community name, bed count, licence class and administrator |

Building and rebuilding the site, the data pipeline and the scripts are documented
separately in **[docs/BUILDING.md](docs/BUILDING.md)**.

---

## Read this first

Four things change how every number here should be read.

**Medicare does not record where a beneficiary lives.** Claims identify the *service*
billed, never the residence. Someone in independent living, in assisted living, or in
their own house is indistinguishable in this data, and no public CMS file splits spend
by residential setting. Residence in this project therefore comes from **state
licensure**, and spend comes from **county-wide claims**. The two are joined by county,
never by person. No figure here tells you what Medicare spends on an assisted living
resident, because no public data can.

**Independent living has no data anywhere.** Alabama does not license IL — it is housing,
not care, so there is no registry, no bed count and no facility list. Every IL-related
question on these pages is answered with a proxy: the count of enrollees aged 75+ and
85+ set against licensed assisted living and memory care beds. That gap is an
addressable population, not a measured one.

**"Skilled nursing" here means post-acute SNF, not the nursing home.** Medicare covers
up to 100 days of skilled nursing after a qualifying hospital stay. Long-term custodial
nursing home care is paid by Medicaid and out of pocket and appears nowhere in these
dollars. The practical consequence: most of the savings from keeping someone out of a
nursing home accrue to **Medicaid**, not Medicare. No spend bundle in this dataset
represents a custodial nursing home stay.

The Medicare-side savings that *are* measurable appear throughout: inpatient stays per
1,000, readmission rate, ER visits per 1,000, SNF days per 1,000, and the tilt toward
home health and hospice. Those five vary more than two-fold between Alabama counties.

**Spend is Original Medicare only, and Alabama is 60.4% Medicare Advantage.** CMS
publishes no county-level MA spending at all. The $4.67B on these pages is therefore
roughly a third of true Medicare spend in the state, and counties with unusually high MA
penetration have a correspondingly smaller share of their care visible here.

---

## Statewide, at a glance

| Measure | Value |
| --- | --- |
| Medicare enrollees (2025) | 1,133,996 — 60.4% Medicare Advantage |
| Aged 75+ / aged 85+ | 420,666 / 98,865 |
| Growth since 2020 | 75+ cohort **+19.5%**, total enrollment +6.7% |
| Original Medicare spend (2024) | $4.67B, or $12,597 per FFS beneficiary |
| Assisted living | 185 facilities, 7,320 licensed beds |
| Memory care (SCALF) | 107 facilities, 3,499 licensed beds |
| Nursing homes | 224 facilities, 26,504 certified beds, 21,964 residents (83% full) |
| People aged 75+ per licensed AL/memory-care bed | 39 (statewide rate 25.7 beds per 1,000) |
| Counties with **no** licensed assisted living or memory care | **18** |
| Counties below the statewide bed rate | **49 of 67**, 1,947 beds short in total |

Where the fee-for-service dollar goes: acute hospital 50.2%, home and community 35.3%,
institutional post-acute 7.6%, hospice 5.6%.

---

## Page 1 — County atlas

One row per county, 93 fields, of which 85 are exposed as selectable measures. Any
measure can shade the county map; the same 85 appear as sortable table columns and drive
the ranked list, the distribution strip and each county profile.

### How shading works

Each measure is shaded one of two ways, and the control above the map lets you override
the default.

- **Low → high** (a single blue ramp) for counts and totals, where the question is
  simply how much. Breaks are septiles of the 67 observed values, so each shade holds
  roughly the same number of counties.
- **Compared to Alabama average** (blue below, grey at, red above) for rates, ratios and
  per-capita dollars, where the question is how a county sits against the state. Bands
  are ±4%, ±12% and ±25% around the state figure.

Red is not "bad" and blue is not "good" — the ramp encodes direction from the average,
nothing more. Whether high readmissions or high home-health use is good news depends
entirely on what you are looking for.

### The Alabama average

For rates and per-capita dollars, the state figure is **weighted by fee-for-service
beneficiaries**, not a plain mean of 67 counties — otherwise Greene County (577 FFS
beneficiaries) would count as much as Jefferson (34,085). For counts it is a plain
per-county mean. For the two growth measures it is true statewide growth, computed from
the 2020 and 2025 state totals rather than averaged across counties.

### Derived measures worth understanding

**Bed gap** is the market measure. It is the number of assisted living and memory care
beds a county would need to reach Alabama's own statewide rate of 25.7 beds per 1,000
enrollees aged 75+. A positive number means under-supplied. It is deliberately
benchmarked against the state's own average rather than an outside industry target, so
it needs no assumption beyond this data to defend. Largest gaps: Elmore 135 beds,
Russell 101, Dale 89, Mobile 82, Chilton 74, Lawrence 74.

**Per-capita dollars** are per *fee-for-service beneficiary with full Part A and B*, not
per enrollee. In Alabama those denominators differ by more than 3x in some counties, so
never multiply a per-capita figure by total enrollment.

**Standardized payment** removes geographic wage adjustments and policy add-ons. Use the
standardized column when comparing care intensity between counties, and the raw column
when you want actual dollars flowing.

**Per-user dollars** divide by beneficiaries who used that service, not by everyone. SNF
payment per user is what a SNF stay costs; SNF payment per capita is what SNF costs the
county's average beneficiary. They move independently — a county can have few SNF users
who each cost a great deal.

**Growth measures** compare 2025 with 2020.

### The 85 measures

### Demand — 13 measures

| Measure | Field | Units | Shading | What it means |
|---|---|---|---|---|
| Medicare enrollees | `enroll` | count | low→high | Total Medicare enrollees, 2025 |
| Aged 75+ | `a75` | count | low→high | Enrollees aged 75 and over — the core senior-living cohort |
| Aged 85+ | `a85` | count | low→high | Enrollees aged 85 and over |
| Growth in 75+, 5yr | `g5_a75` | percent change | vs AL avg | Change in the 75+ cohort since 2020 |
| Growth in enrollment, 5yr | `g5_enroll` | percent change | vs AL avg | Change in total Medicare enrollment since 2020 |
| Medicare Advantage share | `ma_pct` | percent | vs AL avg | Share enrolled in Medicare Advantage rather than Original Medicare |
| Original Medicare enrollees | `om` | count | low→high | Enrollees remaining in fee-for-service Medicare |
| Dual eligible | `dual_pct` | percent | vs AL avg | Share also covered by Medicaid — a proxy for low income |
| Average age | `avg_age` | 1 decimal | vs AL avg | Average age of fee-for-service beneficiaries |
| Female | `feml_pct` | percent | vs AL avg | Share female |
| Black | `blk_pct` | percent | vs AL avg | Share Black |
| White | `wht_pct` | percent | vs AL avg | Share White |
| Hispanic | `hsp_pct` | percent | vs AL avg | Share Hispanic |

### Opportunity — 7 measures

| Measure | Field | Units | Shading | What it means |
|---|---|---|---|---|
| Bed gap to state rate | `bed_gap` | signed count | vs AL avg | Assisted living and memory care beds needed to reach Alabama’s statewide rate of 25.7 per 1,000 aged 75+. Positive means under-supplied. |
| People 75+ per bed | `per_bed` | 1 decimal | vs AL avg | Enrollees aged 75+ for every licensed assisted living or memory care bed. Higher means thinner supply. |
| AL + memory care beds / 1k 75+ | `sl_per1k` | 1 decimal | vs AL avg | Licensed assisted living and memory care beds per 1,000 enrollees aged 75 and over |
| AL + memory care beds | `sl_bed` | count | low→high | Total licensed assisted living and memory care beds |
| Memory care share of beds | `mc_share` | percent | vs AL avg | Memory care share of a county’s licensed senior living beds |
| Nursing home residents / 1k 75+ | `nh_per1k` | 1 decimal | vs AL avg | Nursing home residents per 1,000 enrollees aged 75 and over |
| Nursing home occupancy | `nh_occ` | percent | vs AL avg | Average daily residents as a share of certified beds |

### Cost — 24 measures

| Measure | Field | Units | Shading | What it means |
|---|---|---|---|---|
| Total $ per beneficiary | `pc` | dollars | vs AL avg | Total Original Medicare payment per fee-for-service beneficiary, 2024 |
| Standardized $ per beneficiary | `pc_std` | dollars | vs AL avg | The same figure with wage and policy adjustments removed — the right one for comparing care intensity between counties |
| Total FFS spend | `tot_amt` | dollars (millions) | low→high | Total Original Medicare payments in the county |
| Home & community $ | `home_pc` | dollars | vs AL avg | Home health, office visits, DME, labs, imaging, clinics and Part B drugs, per beneficiary |
| Acute hospital $ | `acute_pc` | dollars | vs AL avg | Inpatient, outpatient, ambulatory surgery, procedures, ambulance and dialysis, per beneficiary |
| Institutional post-acute $ | `inst_pc` | dollars | vs AL avg | Skilled nursing, inpatient rehab and long-term care hospital, per beneficiary |
| Hospice $ | `eol_pc` | dollars | vs AL avg | Hospice payment per beneficiary |
| Inpatient $ | `pc_ip` | dollars | vs AL avg | Inpatient hospital payment per beneficiary |
| Outpatient $ | `pc_op` | dollars | vs AL avg | Hospital outpatient payment per beneficiary |
| Skilled nursing $ | `pc_snf` | dollars | vs AL avg | Post-acute SNF payment per beneficiary |
| Home health $ | `pc_hh` | dollars | vs AL avg | Home health payment per beneficiary |
| Hospice $ (bucket) | `pc_hospc` | dollars | vs AL avg | Hospice payment per beneficiary |
| Office visits $ | `pc_em` | dollars | vs AL avg | Evaluation and management payment per beneficiary |
| Durable equipment $ | `pc_dme` | dollars | vs AL avg | DME payment per beneficiary |
| Imaging $ | `pc_imgng` | dollars | vs AL avg | Imaging payment per beneficiary |
| Lab tests $ | `pc_tests` | dollars | vs AL avg | Laboratory test payment per beneficiary |
| Procedures $ | `pc_prcdrs` | dollars | vs AL avg | Procedure payment per beneficiary |
| Ambulatory surgery $ | `pc_asc` | dollars | vs AL avg | Ambulatory surgical centre payment per beneficiary |
| Inpatient rehab $ | `pc_irf` | dollars | vs AL avg | Inpatient rehabilitation facility payment per beneficiary |
| Long-term care hospital $ | `pc_ltch` | dollars | vs AL avg | LTCH payment per beneficiary |
| Ambulance $ | `pc_amblnc` | dollars | vs AL avg | Ambulance payment per beneficiary |
| Clinic $ (FQHC/RHC) | `pc_fqhc_rhc` | dollars | vs AL avg | Federally qualified health centre and rural health clinic payment per beneficiary |
| Part B drugs $ | `pc_trtmnts` | dollars | vs AL avg | Part B drug and treatment payment per beneficiary |
| Dialysis $ | `pc_op_dlys` | dollars | vs AL avg | Outpatient dialysis payment per beneficiary |

### Hospital — 9 measures

| Measure | Field | Units | Shading | What it means |
|---|---|---|---|---|
| Inpatient stays / 1k | `ip_stays` | 1 decimal | vs AL avg | Inpatient covered stays per 1,000 beneficiaries |
| Inpatient days / 1k | `ip_days` | 1 decimal | vs AL avg | Inpatient covered days per 1,000 beneficiaries |
| Had an inpatient stay | `ip_pct` | percent | vs AL avg | Share with at least one inpatient stay |
| Readmission rate | `readmit` | percent | vs AL avg | Share of acute hospital discharges followed by a readmission — the single clearest signal of care that is not holding after discharge |
| Inpatient $ per user | `ip_per_user` | dollars | vs AL avg | Inpatient payment per beneficiary who had a stay |
| ER visits / 1k | `er` | 1 decimal | vs AL avg | Emergency department visits per 1,000 beneficiaries |
| Had an ER visit | `er_pct` | percent | vs AL avg | Share with at least one emergency visit |
| Outpatient visits / 1k | `op_visits` | 1 decimal | vs AL avg | Hospital outpatient visits per 1,000 beneficiaries |
| Had an outpatient visit | `op_pct` | percent | vs AL avg | Share with at least one hospital outpatient visit |

### Post-acute — 8 measures

| Measure | Field | Units | Shading | What it means |
|---|---|---|---|---|
| SNF days / 1k | `snf_days` | 1 decimal | vs AL avg | Medicare-covered skilled nursing days per 1,000 beneficiaries |
| SNF stays / 1k | `snf_stays` | 1 decimal | vs AL avg | Medicare-covered SNF stays per 1,000 beneficiaries |
| Used SNF | `snf_pct` | percent | vs AL avg | Share with any Medicare-covered SNF stay |
| SNF $ per user | `snf_per_user` | dollars | vs AL avg | SNF payment per beneficiary who had a stay |
| Rehab stays / 1k | `irf_stays` | 1 decimal | vs AL avg | Inpatient rehabilitation stays per 1,000 beneficiaries |
| Used inpatient rehab | `irf_pct` | percent | vs AL avg | Share with any inpatient rehabilitation stay |
| LTCH stays / 1k | `ltch_stays` | 1 decimal | vs AL avg | Long-term care hospital stays per 1,000 beneficiaries |
| Used LTCH | `ltch_pct` | percent | vs AL avg | Share with any long-term care hospital stay |

### Home & community — 17 measures

| Measure | Field | Units | Shading | What it means |
|---|---|---|---|---|
| Used home health | `hh_pct` | percent | vs AL avg | Share with any home health episode |
| Home health episodes / 1k | `hh_eps` | 1 decimal | vs AL avg | Home health episodes per 1,000 beneficiaries |
| Home health visits / 1k | `hh_visits` | 1 decimal | vs AL avg | Home health visits per 1,000 beneficiaries |
| Home health $ per user | `hh_per_user` | dollars | vs AL avg | Home health payment per beneficiary who used it |
| Used hospice | `hospc_pct` | percent | vs AL avg | Share with any hospice stay |
| Hospice days / 1k | `hospc_days` | 1 decimal | vs AL avg | Hospice covered days per 1,000 beneficiaries |
| Hospice stays / 1k | `hospc_stays` | 1 decimal | vs AL avg | Hospice stays per 1,000 beneficiaries |
| Saw a doctor | `em_pct` | percent | vs AL avg | Share with any evaluation and management visit |
| Office visits / 1k | `em_events` | 1 decimal | vs AL avg | Evaluation and management events per 1,000 beneficiaries |
| Used durable equipment | `dme_pct` | percent | vs AL avg | Share with any DME claim |
| DME events / 1k | `dme_events` | 1 decimal | vs AL avg | DME events per 1,000 beneficiaries |
| Had lab tests | `tests_pct` | percent | vs AL avg | Share with any laboratory test |
| Had imaging | `imgng_pct` | percent | vs AL avg | Share with any imaging study |
| Used a clinic | `fqhc_pct` | percent | vs AL avg | Share using a federally qualified health centre or rural health clinic |
| Clinic visits / 1k | `fqhc_visits` | 1 decimal | vs AL avg | FQHC and RHC visits per 1,000 beneficiaries |
| Used an ambulance | `amblnc_pct` | percent | vs AL avg | Share with any ambulance claim |
| Ambulance runs / 1k | `amblnc_events` | 1 decimal | vs AL avg | Ambulance events per 1,000 beneficiaries |

### Supply — 7 measures

| Measure | Field | Units | Shading | What it means |
|---|---|---|---|---|
| Assisted living beds | `alf_bed` | count | low→high | Licensed assisted living beds |
| Assisted living facilities | `alf_fac` | count | low→high | Licensed assisted living facilities |
| Memory care beds | `mc_bed` | count | low→high | Licensed specialty care (memory care) beds |
| Memory care facilities | `mc_fac` | count | low→high | Licensed specialty care assisted living facilities |
| Nursing home residents | `nh_res` | count | low→high | Average daily nursing home residents |
| Nursing home beds | `nh_bed` | count | low→high | Certified nursing home beds |
| Nursing homes | `nh_fac` | count | low→high | Certified nursing homes |

---

## Page 2 — Bed map

Every licensed assisted living and memory care community in Alabama as a point, sized by
licensed beds, over a county choropleth of capacity. 292 licences, 10,819 beds.

Counties can be shaded by total beds, assisted living beds, memory care beds, number of
communities, beds per 1,000 aged 75+, or bed gap. Filter by licence type, minimum bed
count, county, or free text across name, city, county and administrator.

Largest county capacity: Madison 1,528 beds, Jefferson 1,466, Baldwin 911, Mobile 756,
Shelby 681, Tuscaloosa 665. Eighteen counties have none at all.

### What each record holds

Straight from the ADPH licence file, unmodified: community name, licence type, licence
class, licensed beds, street address, city, ZIP, county, **administrator name**, phone,
licensee type (corporation, LLC, hospital authority, and so on), licence status, and the
ADPH facility ID.

### Licence types and classes

Alabama licenses two distinct things, and a campus commonly holds both:

- **Assisted Living Facility (ALF)** — 185 licences, 7,320 beds.
- **Specialty Care Assisted Living Facility (SCALF)** — 107 licences, 3,499 beds. This is
  Alabama's licence class for dementia and Alzheimer's care, and it is what this project
  counts as **memory care**. A SCALF is licensed separately from any ALF at the same
  address.

Within each type, ADPH assigns a size class. Under
[Ala. Admin. Code r. 420-5-4](https://www.law.cornell.edu/regulations/alabama/Ala-Admin-Code-r-420-5-4-.12),
a **Group** facility is authorized to care for 3 to 16 adults and a **Congregate**
facility for 17 or more, with **Family** covering the smallest operations.

**A caution:** in the ADPH export the class label does not line up cleanly with the
licensed-bed count. Congregate ALFs in this file run from 8 to 160 beds, one Group ALF
carries 17 beds, and the single Family ALF is listed at 50. Read the class as the
category ADPH assigned to the licence, not as something you can infer from — or check
against — the bed number. Counts in this file: Congregate ALF 117, Group ALF 67,
Congregate SCALF 63, Group SCALF 44, Family ALF 1.

"Licensed beds" is authorized capacity, not occupancy. ADPH does not publish census for
assisted living, so nothing on these pages shows how full a community is. (Nursing home
occupancy *is* available, from a different source, and appears on the county atlas.)

### How precise the dots are

Addresses are geocoded through the US Census geocoder. Precision is flagged on every
record and drawn differently on the map:

| Precision | Count | Drawn as | Meaning |
| --- | --- | --- | --- |
| Street | 262 | solid dot | matched to a street segment |
| City | 24 | hollow ring | address not in the Census street file; placed at the centre of that city's other matched communities |
| County | 6 | hollow ring | no city fallback available; placed at the county centre |

The 30 non-street matches are mostly new subdivisions the Census address file does not
carry yet. **Bed counts, names, licence classes and administrators are exact in every
case — only the pin position is approximate,** and those records carry an "approx.
location" badge.

### Communities that share an address

156 licences across 71 addresses sit at identical coordinates — 60 pairs, 8 triples and
3 addresses with four licences — because a campus commonly holds both an ALF and a SCALF
licence, and some operators run several licences from one building. Identical points
cannot be separated by zooming, so co-located licences are nudged onto a small ring:
invisible at statewide view, cleanly separated once you zoom in. Each record shows a
badge naming how many licences share its address.

This is why the bed map's licence count (292) is higher than the number of distinct
campuses, and why a single campus can appear as both a blue and an orange dot.

---

## Glossary

**Original Medicare / fee-for-service (FFS)** — traditional Medicare, where CMS pays
providers per service and therefore has a claim record. All spend and utilization on
these pages is FFS only.

**Medicare Advantage (MA)** — private plans paid a capitated rate. CMS publishes no
county-level MA spending or utilization, so MA enrollees appear in the enrollment counts
but contribute nothing to the cost and use measures. Alabama is 60.4% MA.

**FFS beneficiary with full Part A and B** — the denominator for every per-capita dollar
here. Smaller than total enrollees, and much smaller in high-MA counties.

**Dual eligible** — covered by both Medicare and Medicaid. The most useful available
proxy for low income, and relevant to senior housing because Medicaid, not Medicare, pays
for custodial long-term care.

**SNF (skilled nursing facility)** — post-acute skilled care, Medicare-covered up to 100
days after a qualifying hospital stay. Not the same as a nursing home resident, most of
whom are long-stay and Medicaid-funded.

**IRF / LTCH** — inpatient rehabilitation facility and long-term care hospital: the two
other institutional post-acute settings, both small in Alabama.

**Home health** — skilled nursing or therapy delivered at the beneficiary's residence,
whatever that residence is. A home health episode in this data may well describe someone
living in assisted living, because the claim does not say.

**Hospice** — end-of-life care, most often delivered where the person already lives.

**Readmission rate** — share of acute hospital discharges followed by another admission.
The clearest single signal in this data of care not holding after discharge. Ranges from
Russell 24.1% to Cleburne 12.2%.

**Per 1,000 beneficiaries** — a utilization rate normalized for population, so counties
of different sizes can be compared.

**Standardized payment** — payment with geographic wage adjustments and policy add-ons
removed, for comparing intensity of care rather than dollars.

**ALF / SCALF** — see licence types above. SCALF is memory care.

**Licensed beds** — authorized capacity, not occupancy or census.

**Bed gap** — beds needed to reach Alabama's statewide rate of 25.7 AL and memory care
beds per 1,000 enrollees aged 75+.

---

## Sources

Everything here is public data. No source requires an API key or a licence.

| Source | Vintage | Used for |
| --- | --- | --- |
| [CMS Medicare Monthly Enrollment](https://data.cms.gov/summary-statistics-on-beneficiary-enrollment/medicare-and-medicaid-reports/medicare-monthly-enrollment) — dataset `d7fabe1e-d19b-4333-9eff-e80e0643f2fd` | annual 2025, growth vs 2020 | enrollees, MA share, age bands, dual eligibility |
| [CMS Medicare Geographic Variation by National, State & County](https://data.cms.gov/medicare-geographic-comparisons/medicare-geographic-variation-by-national-state-county) — dataset `6219697b-8f6c-4164-bed4-cd9317c58ebc` | 2024 | spend by service bucket, utilization rates, demographics |
| [CMS Care Compare Provider Information](https://data.cms.gov/provider-data/dataset/4pq5-n9py) — dataset `4pq5-n9py` | current | nursing home certified beds and average daily residents |
| [Alabama ADPH Facilities Directory](https://dph1.adph.state.al.us/FacilitiesDirectory/) | retrieved September 2026 | licensed ALF and SCALF communities, beds, administrators |
| [US Census Geocoder](https://geocoding.geo.census.gov/) | Public_AR_Current | facility coordinates |
| [Plotly US county GeoJSON](https://github.com/plotly/datasets) | — | county boundaries |

Vintages do not align: enrollment is 2025, claims are 2024, licensure is September 2026.
That is as current as each source gets, and it matters most when reading bed gap, which
sets 2026 licensed beds against 2025 population.

## Data you can download

| File | What it is |
| --- | --- |
| [`data/alabama_master.csv`](data/alabama_master.csv) | 67 counties × 93 fields — every measure on the county atlas, for spreadsheets |
| [`data/alabama_master.json`](data/alabama_master.json) | the same rows, as the site consumes them |
| [`data/al_facilities.json`](data/al_facilities.json) | 292 communities with coordinates, precision flags and full licence records |
| [`data/al_geo.json`](data/al_geo.json) | county boundaries as SVG paths, plus the shared projection bounds |

## Licence

Code is MIT — see [LICENSE](LICENSE). The underlying data is public domain (CMS, a US
federal agency) and public record (Alabama Department of Public Health). Neither is
covered by this repository's licence, and both should be cited to their source.
