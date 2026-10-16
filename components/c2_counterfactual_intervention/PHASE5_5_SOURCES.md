# Phase 5.5 source and refresh guide

## Official food prices accessed

On 15 October 2026, the [Department of Census and Statistics retail-price index](https://www.statistics.gov.lk/InflationAndPrices/StaticalInformation/RetailPrices)
listed the [1st week of October 2026 Colombo District retail PDF](https://www.statistics.gov.lk/Resource/en/InflationAndPrices/retail/DCSB-WRP-2026-10-W1.pdf).
Its title states the observation week but gives no separate publication date;
`publication_date` stays null. The 1–7 October dates in the import are marked
`calendar_week_interpretation`, not printed dates. The coverage is main markets
in Colombo District. These are **indicative official references for a Kalmunai
planning scenario**, never verified Kalmunai market quotes. The DCS page has
PDF links; no documented machine-readable API was found. The [HARTI weekly
bulletin index](https://www.harti.gov.lk/weekly-price.php) was accessible through
18–24 September 2026 and includes missing PDFs; no HARTI prices were imported.
No undocumented endpoint is used.

`data/dcs_2026_10_w1.csv.txt` contains **13 checked retail average-price cells**
transcribed from the current-week column, each with report URL and page/row
locator. The exact-product catalog has **14 foods**; **curd has no matched
price** and remains null. Examples: Raw Red rice average LKR 193.22/kg (PDF
page 3), Mysore Dhall average LKR 334.52/kg (page 3), Egg average LKR
37.77/each (page 3), and Gotukola LKR 58.24/bunch (page 1). Exact variants
matter; no rice grade, fish, milk brand, or package is silently substituted.
The catalog covers rice/cereals, pulses, eggs, fish, chicken, milk powder,
vegetables, leafy vegetables, and fruits. Listing does not establish age or
clinical suitability.

## Formats, refresh, and history

`official_prices.py` imports **reviewed CSV transcriptions**, including CSV
prepared from a downloaded official PDF or spreadsheet. Direct PDF/XLSX table
parsing is not automatic: multi-column layouts, inherited row labels, and
current versus prior-week columns require human verification. The importer
requires institution, HTTPS report URL on that institution's domain, exact
product, observed week, market coverage, retail class, evidence status, and
page/row locator. Only checked retail rows are eligible for refresh.

For an on-demand refresh, inspect the latest published report on the official
index, transcribe its current-week retail average column to the same CSV schema,
and double-check rows against the source. Then run:

```powershell
py -m components.c2_counterfactual_intervention.official_prices --reviewed-csv C:\path\reviewed.csv --history C:\path\outside-repo\price_history.json
```

The equivalent `refresh(history_path, lambda: csv_text)` callable supports a
future scheduler after a trustworthy source-download step is supplied. A
failed download, malformed file, duplicate,
or changed value for an existing source row does not overwrite good history.
New rows are appended atomically; history is never replaced wholesale.

`catalog_from_history` uses the latest checked retail observation for each
exact product. `fresh_days` defaults to 14 and is configurable. Fresh official
references are distinguished from historical references, missing prices, and
unverified or wholesale observations. Historical prices remain in history but
leave food feasibility unresolved until refresh or review. Local availability
and its evidence are **null** until explicitly supplied by a caregiver or
authorized local source; an official Colombo price does not prove availability.

Cost calculation supports exact g↔kg and ml↔l conversions and rejects
incompatible units. For example, 100 g of the published Mysore Dhall average
costs **indicative LKR 33.452** at LKR 334.52/kg. Against a separately supplied
LKR 100/day food budget, the arithmetic is within budget, but a fully feasible
card still needs availability, age/clinical suitability, reviewed practice, and
other mandatory evidence. The card identifies
`affordability_scope=indicative_official_reference`, not locally verified
affordability. The caller must authenticate any supplied caregiver or local
evidence. Real C1 mode still fails safely without a registered predictor.

## Nutrition publications and review limits

`guideline_references.py` stores source document, edition, age range, concept,
food groups, exact located section, restrictions, and review status. The [WHO
2023 complementary-feeding publication overview](https://www.who.int/publications/i/item/9789240081864)
explicitly covers **6–23 months**. It supports that scope only; it does not
automatically set meal frequency, food groups, suitability, or the synthetic
diversity scale. The [Family Health Bureau Child Nutrition Unit](https://fhb.health.gov.lk/technical-units/child-nutrition)
lists a [January 2025 caregiver booklet](https://fhb.health.gov.lk/resources/2025-booklet-on-complementary-feeding-for-caregivers-e-en).
The [Ministry of Health Nutrition Division resources](https://nutrition.health.gov.lk/english/resources/)
list the 2021 Food Based Dietary Guidelines practitioner's handbook. Their
specific sections and age applicability have not been reviewed, so both are
index-only references and generate no feeding rules. Nothing is marked
independently expert-approved. WHO 6–23-month scope is never applied to
0–5 or 24–59 months. General adult advice is not made a child-specific rule.

## Verification

From the repository root, set `PYTHONPATH=.;backend` and run
`py -m pytest components/c2_counterfactual_intervention/tests -q`.
The new tests use synthetic import fixtures only; the bundled real values are
checked against the cited DCS PDF. No local market survey, independently
verified availability, clinical validation, or real C1 predictor is present.
