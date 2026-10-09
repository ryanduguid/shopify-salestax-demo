# Shopify → OpenAccountants: illustrative state thresholds

**Fork status**

[![Fork code quality](https://app.codacy.com/project/badge/Grade/14c2d469dbc941249f5e33a52cef917c?branch=main)](https://app.codacy.com/gh/ryanduguid/shopify-salestax-demo/dashboard)

Compare explicitly scoped USD sales summaries with a fixed example of six
state thresholds. The output distinguishes a threshold comparison from
registration, reported tax collection and other possible nexus grounds.
Bundled rules have no professional sign-off.

![Illustrative state threshold comparisons](demo.svg)

## Run it

Python 3.10 or later and the standard library are sufficient.

```bash
python pipeline.py
python pipeline.py samples/sales_by_state.json
python -m unittest discover -s tests -v
python make_svg.py
```

The default CLI and SVG generator use bundled examples. Empty, invalid or
incomplete input returns exit code 2; other rows remain visible. Exit code 0
means the modelled comparison and reporting facts were complete, not that the
seller has met its legal obligations.

## Thresholds and source coverage

The fixed example covers assessment dates from 1 January to 26 September 2026.
Dates outside that interval remain incomplete. Sources were checked on
26 September 2026; this is not an automatically updated rules service.

| State | Modelled comparison | Measurement period |
|---|---|---|
| IL | At least US$100,000; no transaction-count test in 2026 | Twelve months ending at the most recent calendar-quarter end |
| NY | More than US$500,000 **and** more than 100 sales | Immediately preceding four New York sales-tax quarters |
| CA | More than US$500,000 in either year separately | Current calendar year to the assessment date and the preceding calendar year |
| PA | At least US$100,000 | Preceding calendar year, following the department's annual measurement guidance |
| FL | More than US$100,000 | Preceding calendar year |
| TX | Below or above US$500,000; equality remains incomplete | Preceding twelve complete calendar months |

[Illinois bulletin FY 2026-12](https://tax.illinois.gov/research/publications/bulletins/fy-2026-12.html)
removes the transaction-count threshold from 1 January 2026.
[New York's guidance](https://www.tax.ny.gov/pubs_and_bulls/publications/sales/nexus.htm)
uses strict comparisons for both tests and quarters ending in February, May,
August and November. [California's guidance](https://cdtfa.ca.gov/industry/wayfair/)
requires combined sales by the retailer and related persons in either the
current or preceding calendar year; the demo does not add the two years together.

[Pennsylvania's statute, section 201(b)(3.5)](https://www.palegis.us/statutes/unconsolidated/law-information/view-statute?SESSYR=1971&SESSIND=0&ACTNUM=0002.&SMTHLWIND=&CHPT=002.&SCTN=001.&SUBSCTN=000.)
uses an inclusive US$100,000 threshold. The
[department's guidance](https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax/online-retailers)
contains both inclusive and strict wording; this example follows the statute
for equality and the guidance for annual measurement. The April-to-March
collection schedule is not calculated.

[Florida section 212.0596](https://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0200-0299/0212/Sections/0212.0596.html)
uses taxable remote sales in the previous calendar year.
[Texas's remote-seller guidance](https://comptroller.texas.gov/taxes/sales/remote-sellers.php)
and [rule 3.286](https://texas-sos.appianportalsgov.com/rules-and-meetings?$locale=en_US&interface=VIEW_TAC_SUMMARY&recordId=197579)
describe a safe harbour below US$500,000 and a trigger above that amount. The
exact-equality case needs separate review, so the demo does not resolve it.

## JSON contract

This is a documented summary format, not a verified Shopify export or Orders
API adapter. All monetary values are USD. The five sample state records are
fabricated, with explicitly supplied measurement facts.

- Supply `assessment_date`, `period_start` and `period_end` as `YYYY-MM-DD`.
  The dates must match the state's measurement period in the table above.
- `period_sales` contains sales for that period. California also requires
  `prior_year_sales` for the entire preceding calendar year.
- New York's `period_orders` must count eligible sales of tangible personal
  property, not an unfiltered Shopify order count. Other states in this
  example do not use a transaction-count test.
- `registered` and `home_state` accept JSON Booleans or null. Missing values
  remain unknown; strings such as `"false"` are invalid.
- `tax_collected` is the reported amount for the supplied period. Zero, unknown
  and registration status are separate facts. A positive amount does not prove
  correct collection.
- Numeric values or decimal strings must be finite, non-negative and at most
  `1e12`. Monetary values allow two decimal places; orders must be whole numbers.

The required `sales_basis` states what the supplied aggregate includes:

| Value | Required aggregate |
|---|---|
| `il_tpp_gross_receipts` | Eligible Illinois gross receipts from tangible personal property |
| `ny_tpp_gross_receipts` | Gross receipts from tangible personal property delivered in New York |
| `ca_related_tpp_sales` | California tangible-personal-property sales by the retailer and related persons |
| `pa_eligible_gross_sales` | Eligible Pennsylvania gross sales across channels, with the relevant marketplace exclusions already applied |
| `fl_taxable_remote_sales` | Taxable remote sales delivered in Florida |
| `tx_total_revenue` | Total Texas revenue, including the taxable, nontaxable and fee amounts described in the source |

The demo validates the declared contract, not the underlying order ledger.
Product taxability, marketplace treatment, related-party identification and
other adjustments must be established before supplying these totals.

## Interpretation and limits

A comparison below the modelled threshold does not establish that no nexus or
collection duty exists. Home-state status does not prove physical presence or
collection. Prior registration, continuing obligations, other nexus grounds,
commencement dates, exemptions, tax rates and tax due are outside this example.
Missing reporting facts leave the run incomplete without discarding a known
threshold comparison.

`python pipeline.py --live` explicitly selects the experimental OpenAccountants
JSON-RPC adapter and requires `OA_MCP_TOKEN` configured outside the repository.
The live authentication and response contract remain unverified; failed calls
never fall back to samples. Only the exact `state-threshold-screen-v1` contract
in `nexus_rules.py` is supported. Provider metadata is reported information,
not independent attestation.

JSON inputs and provider responses reject duplicate object properties and
non-standard numeric constants instead of silently choosing a value.
Control characters in supplied text appear as visible escapes. Redirected
output tolerates encodings that cannot represent the display symbols.
An invalid field remains unknown and retains its diagnostic. Usable facts
for the same state still produce a comparison when its dependencies are valid.

## Files

| File | Role |
|---|---|
| `pipeline.py` | CLI, partial results and separate reporting facts |
| `shopify_client.py` | JSON extraction and normalisation |
| `nexus_rules.py` | Fixed version, date coverage and six supported state contracts |
| `nexus_check.py` | Measurement-period validation and threshold comparisons |
| `oa_client.py` | Bundled examples and experimental live adapter |
| `samples/sales_by_state.json` | Five fabricated state summaries |
| `reporting.py` | Visible control-character escapes and portable output |
| `json_contract.py` | JSON object and numeric-token validation |
| `tests/` | Offline calculation, adapter and command-line regressions |
