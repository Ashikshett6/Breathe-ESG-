# Sources — research, samples, and production gaps

## 1. SAP (fuel & procurement)

### Real-world format researched

- SAP Sustainability Data Exchange and footprint templates: CSV as onboarding path alongside APIs ([SAP Community — Sustainability S/4HANA](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/sustainability-with-sap-s-4hana-cloud-public-edition-2402/ba-p/13600313)).
- Export Master Data apps export Excel/CSV with **technical field IDs** (`WERKS`, `MATNR`, `BUDAT`) and sometimes German UI labels ([Export Master Data apps](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/s-4hc-export-master-data-apps-access-quot-missing-quot-key-fields/ba-p/13471145)).

### What we learned

- Plant codes are meaningless without a lookup table.
- European exports use `;` delimiter and `,` decimal separator.
- Movement type (`BWART`) distinguishes fuel issues from goods receipts.
- Units vary (`L`, `KG`, `M3`, `EA`) — `EA` won’t convert to mass without material master.

### Sample file: `samples/sap_procurement_q1.csv`

- Semicolon delimiter, German headers (`BELNR`, `WERKS`, `MENGE`).
- Includes diesel (Scope 1 fuel), steel packaging (Scope 3), unknown plant `9999` (flag), `M3` gas (unit flag), `EA` misc.

### What breaks in production

- Multiple company codes / currencies in one file without mapping.
- Re-upload duplicates unless hash logic matches business keys (invoice + fiscal year).
- No OData delta — full file replace only.

---

## 2. Utility (electricity)

### Real-world format researched

- Green Button CSV: `START DATE`, `END DATE`, `UNITS` (kWh) per billing period ([Oracle Green Button docs](https://docs.oracle.com/en/industries/utilities/business-customer-engagement/business-customer-engagement-overview/green-button-download-my-data.html)).
- Utility data portals (e.g. BGE CDWeb): historic monthly usage CSV with `YYYY-MM-DD` periods.

### What we learned

- Billing periods span partial months and don’t match fiscal calendars.
- Site identity is often a free-text service address, not ERP plant code.
- Bad rows exist (end before start, blank usage).

### Sample file: `samples/utility_electricity_q1.csv`

- Comma CSV, mixed period lengths (Jan calendar vs mid-month cycle).
- Row with inverted dates and empty usage → flagged/failed.

### What breaks in production

- 50 utilities × 50 column layouts — needs per-vendor mapping config.
- Demand charges (kW) vs energy (kWh) conflated if columns ambiguous.
- PDF-only workflows unsupported.

---

## 3. Corporate travel

### Real-world format researched

- Concur Extract API delivers **`text/csv`** or **`application/zip`** after async job ([Extract v1.0](https://github.com/concur/developer.concur.com/blob/preview/src/api-reference/common/extracts/v1.extracts.markdown)).
- Expense v4 includes `travel.startLocation`, `travel.endLocation`, `airlineServiceClassCode`, hotel dates — distances often absent for flights ([v4 expenses](https://github.com/concur/developer.concur.com/blob/preview/src/api-reference/expense/expense-report/v4.expenses.markdown)).

### What we learned

- Flights may only have airport codes — distance must be estimated later.
- Same origin/destination is a data quality issue.
- Ground transport may lack distance (mileage in separate expense types).

### Sample file: `samples/concur_travel_q1.csv`

- Mixed EUR/USD, flight without distance (FRA–CDG), business class long-haul, same-airport ATL–ATL flag, Uber with miles.

### What breaks in production

- Extract definitions differ per tenant — column names won’t match without config UI.
- Hotel nights not modeled as activity quantity (only flags in prototype).
- Personal vs business trip classification not in extract.
