# Data model

## Design goal

Every ingested row becomes one **ActivityRecord** — the object analysts review before audit lock. The model separates **tenant**, **provenance**, **GHG classification**, **normalized quantities**, and **review state** so we can answer: who uploaded what, what scope does it fall under, was it changed after ingest, and is it approved for auditors.

## Entity relationship (conceptual)

```
Organization (tenant)
├── PlantLookup (SAP plant code → site name / grid region)
├── IngestionBatch (one file upload per source)
│   └── ActivityRecord (normalized row)
│       └── AuditEvent (approve / edit / flag)
└── AnalystProfile → User
```

## Multi-tenancy

- **`Organization`** is the tenant boundary. All `IngestionBatch`, `ActivityRecord`, `PlantLookup`, and `AuditEvent` rows carry `organization_id`.
- **`AnalystProfile`** binds a Django `User` to exactly one organization. API querysets always filter through `request.user.analystprofile.organization`.
- Cross-tenant leakage is prevented at the view layer (no org ID in URLs — org is inferred from auth).

## Scope 1 / 2 / 3

Stored on **`ActivityRecord.scope`** (char `1` | `2` | `3`):

| Source   | Category      | Scope | Rationale |
|----------|---------------|-------|-----------|
| SAP      | fuel          | 1     | Direct combustion (diesel, gas movement types) |
| SAP      | procurement   | 3     | Purchased goods / materials |
| Utility  | electricity   | 2     | Purchased electricity |
| Travel   | flight/hotel/ground | 3 | Business travel (Category 6) |

Classification is rule-based in parsers (keywords + SAP movement type). Production would use a configurable factor mapping table.

## Source-of-truth tracking

| Field | Purpose |
|-------|---------|
| `source_type` | Which system produced the row (`sap`, `utility`, `travel`) |
| `batch` | FK to `IngestionBatch` (filename, upload time, uploader) |
| `source_row_id` | Stable ID from source file (e.g. `BELNR-BUZEI`, meter account) |
| `source_row_hash` | SHA-256 of source type + row id + raw payload — dedup on re-upload |
| `raw_payload` | JSON copy of mapped source columns (audit/debug) |
| `ingested_at` | When normalization ran |
| `is_edited` | True if analyst PATCH changed quantity/dates/etc. |
| `reviewed_by` / `reviewed_at` | Set on approve |

**`AuditEvent`** append-only log: `upload`, `approve`, `edit`, `flag`, `lock_for_audit` with JSON `detail` (field-level diffs on edit).

## Unit normalization

- **`quantity` / `unit`**: as reported by source (may be `L`, `GAL`, `M3`, `kWh`, `mi`).
- **`normalized_quantity` / `normalized_unit`**: prototype targets activity units for later emission factors:
  - Fuel → litres (`L`)
  - Procurement mass → `kg`
  - Electricity → `kWh`
  - Travel distance → `km`

Unrecognized units leave normalized fields null and add a **flag** — analyst must fix or approve with note.

## Review workflow

`review_status` on **ActivityRecord**:

1. **`pending`** — parsed OK, no flags
2. **`flagged`** — suspicious but parseable (unknown plant, missing distance, bad billing period)
3. **`failed`** — validation errors (unparseable quantity, missing usage)
4. **`approved`** — analyst signed off
5. **`locked`** — bulk lock for external audit (immutable in prototype)

State transitions: pending/flagged/failed → approved → locked. Locked rows reject approve/edit.

## What we deliberately did not model

- Full emission factor catalog / CO₂e calculation (downstream of activity data)
- Supplier master data sync
- Document storage (PDF utility bills) — only structured CSV path
- Per-field versioning table (audit JSON is enough for prototype)

## Indexes

- `(organization, review_status)` — review queue
- `(organization, scope, category)` — reporting
- Unique `(organization, source_type, source_row_hash)` — idempotent re-ingest
