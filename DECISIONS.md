# Decisions

## SAP — format and subset

**Researched:** SAP Sustainability Data Exchange (CSV templates), S/4 Export Master Data apps (technical + localized column names), IDoc/OData for real-time integration.

**Chose:** Semicolon-delimited **material document / goods movement CSV** with German *and* English header aliases — because sustainability teams most often receive ad-hoc extracts from MM/FI reports, not live OData. IDoc would be correct for ERP integration but overkill for a 4-day prototype.

**Subset handled:**
- Posting date, material, quantity, unit, plant, vendor, amount, movement type
- Fuel vs procurement via description keywords + movement types `201` / `261`

**Ignored:** IDoc configuration, batch scheduling, multi-company codes, currency translation, full material master sync.

**Ingestion:** File upload (analyst receives export via email/share drive).

**Would ask PM:** Which SAP report name do they actually run today? Is plant `WERKS` always populated?

---

## Utility — format and subset

**Researched:** Green Button “Download My Data” (TYPE, START DATE, END DATE, UNITS/kWh), utility portal interval/historic CSV guidelines (BGE-style).

**Chose:** **Portal billing-period CSV** — facilities teams routinely export monthly billing summaries, not AMI interval data. Billing periods intentionally don't align to calendar months.

**Subset handled:**
- Account/meter, service address, period start/end, kWh usage, tariff/rate schedule, cost

**Ignored:** PDF bill OCR, Green Button XML, hourly AMI, tariff line-item breakdown, demand charges (kW).

**Ingestion:** File upload.

**Would ask PM:** Do they have one utility or 40? Is address→site mapping maintained internally?

---

## Corporate travel

**Researched:** SAP Concur Extract API (`/api/expense/extract/v1.0` → CSV/ZIP), Expense v4 `travel` object (airline class, start/end location, hotel dates).

**Chose:** **Concur-style expense extract CSV** — same columns analysts see when Finance pulls approved reports. API pull is the production path; upload simulates the delivered file.

**Subset handled:**
- Expense type, transaction date, vendor, amount, origin/destination, distance when present, flight class
- Categories → flight / hotel / ground (Scope 3)

**Ignored:** Itemizations, per-diem allowances, personal car mileage reimbursement rules, real-time TripLink API.

**Ingestion:** File upload (stands in for scheduled extract job).

**Would ask PM:** Concur or Navan? Do they need ticket-level class for DEFRA factors?

---

## Stack

- **Django + DRF** — fast multi-tenant API, admin, migrations
- **React (Vite)** — review UI; built to `frontend/dist`, served by Django + WhiteNoise on deploy
- **PostgreSQL on Render** — production; SQLite locally

## Auth

Token auth for API; demo user `analyst` / `demo1234` seeded on deploy. Single org in prototype — multi-org is a row filter, not separate deployments.

## Suspicious data

Automatic flags (unknown plant, huge kWh, inverted billing period, missing flight endpoints, ground without distance) — **flagged**, not silently dropped, so analysts see volume and judgment calls.

## Deployment

**Render** blueprint (`render.yaml`) — mandatory hosted URL; `build.sh` runs frontend build, migrations, seed.
