# Tradeoffs — three things we did not build

## 1. Live API connectors (SAP OData, Concur Extract job, utility Green Button API)

**Why not:** Each requires customer-specific credentials, IP allowlists, OAuth apps, and weeks of integration testing. The assignment’s pain is *data shape heterogeneity*, not HTTP auth.

**What we did instead:** File upload with parsers tolerant of header variants — mirrors how data actually arrives in year one.

**Cost:** Re-upload replaces sync; no incremental delta detection beyond `source_row_hash` dedup.

---

## 2. CO₂e calculation engine and emission factor library

**Why not:** Factors depend on client methodology (DEFRA vs EPA vs supplier-specific), grid regions, and vintage. Building a fake calculator would score “feature-rich” but fail the “can you defend it?” bar.

**What we did instead:** Normalize **activity data** (litres, kWh, km) and scope classification — the handoff point to a real calc service.

**Cost:** Analyst approves activity rows, not tCO₂e totals auditors see on final reports.

---

## 3. PDF utility bill ingestion (OCR / ML extraction)

**Why not:** Many facilities teams *do* have PDFs, but OCR pipelines are brittle, expensive to validate, and wrong for a 4-day scope without labeled bills per utility format.

**What we did instead:** CSV portal export path — common when accounts exist on utility dashboards.

**Cost:** Clients stuck on PDF-only workflows need a manual CSV step or a future OCR service.
