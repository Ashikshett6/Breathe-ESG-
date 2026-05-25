"""
Parsers for three realistic source shapes:
- SAP: semicolon-delimited procurement/movement CSV (German or English headers)
- Utility: portal billing-period CSV (Green Button–style columns)
- Travel: Concur-style expense extract CSV
"""

import csv
import hashlib
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from dateutil import parser as date_parser

from core.models import (
    ActivityCategory,
    ActivityRecord,
    AuditEvent,
    IngestionBatch,
    PlantLookup,
    ReviewStatus,
    Scope,
    SourceType,
)
from ingestion.normalize import (
    DISTANCE_UNITS,
    ENERGY_UNITS,
    FUEL_UNITS,
    MASS_UNITS,
    normalize_quantity,
)

# SAP column aliases (English + German export variants)
SAP_HEADERS = {
    "document": ["belnr", "document_number", "document no", "belegnummer"],
    "item": ["buzei", "item", "line_item", "position"],
    "posting_date": ["budat", "posting_date", "posting date", "buchungsdatum"],
    "material": ["matnr", "material", "material_number", "materialnummer"],
    "description": ["maktx", "description", "material_description", "kurztext"],
    "quantity": ["menge", "quantity", "qty"],
    "unit": ["meins", "unit", "uom", "einheit"],
    "plant": ["werks", "plant", "plant_code", "werk"],
    "vendor": ["lifnr", "vendor", "supplier", "lieferant"],
    "amount": ["dmbtr", "amount", "net_value", "wert"],
    "currency": ["waers", "currency", "währung", "waehrung"],
    "movement_type": ["bwart", "movement_type", "movement type", "bewegungsart"],
}

UTILITY_HEADERS = {
    "account": ["account_number", "account", "service_account", "meter_account"],
    "meter": ["meter_number", "meter", "meter_id"],
    "site": ["service_address", "site_name", "facility", "location"],
    "start": ["start_date", "period_start", "billing_period_start", "start date"],
    "end": ["end_date", "period_end", "billing_period_end", "end date"],
    "usage": ["usage", "consumption", "units", "kwh", "energy_kwh"],
    "unit": ["unit", "uom", "units_of_measure"],
    "cost": ["total_charge", "amount", "cost", "charges"],
    "tariff": ["rate_schedule", "tariff", "rate_code"],
}

TRAVEL_HEADERS = {
    "report_id": ["report_id", "report key", "reportkey"],
    "entry_id": ["entry_id", "entry key", "entrykey"],
    "expense_type": ["expense_type", "expense type", "expense_type_name"],
    "transaction_date": ["transaction_date", "trans date", "expense_date"],
    "vendor": ["vendor_name", "vendor", "merchant"],
    "amount": ["transaction_amount", "amount", "posted_amount"],
    "currency": ["currency", "transaction_currency"],
    "from_loc": ["start_location", "from", "origin"],
    "to_loc": ["end_location", "to", "destination"],
    "distance": ["distance", "mileage"],
    "distance_unit": ["distance_unit", "mileage_unit"],
    "flight_class": ["airline_service_class", "class_of_service", "class"],
    "nights": ["hotel_nights", "number_of_nights"],
    "ticket": ["ticket_number", "confirmation"],
}


def _detect_delimiter(sample: str) -> str:
    if sample.count(";") > sample.count(","):
        return ";"
    return ","


def _map_headers(fieldnames, mapping):
    """Map canonical parser keys to actual CSV column names."""
    lower = {name.strip().lower(): name for name in (fieldnames or [])}
    result = {}
    for canonical, aliases in mapping.items():
        for alias in aliases:
            if alias in lower:
                result[canonical] = lower[alias]
                break
    return result


def _parse_date(val):
    if not val or not str(val).strip():
        return None
    s = str(val).strip()
    for fmt in ("%Y%m%d", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return date_parser.parse(s, dayfirst=True).date()
    except (ValueError, TypeError):
        return None


def _parse_decimal(val):
    if val is None or str(val).strip() == "":
        return None
    s = str(val).strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _row_hash(source_type, row_id, payload: dict) -> str:
    raw = f"{source_type}:{row_id}:{sorted(payload.items())}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _classify_sap(material_desc, movement_type):
    desc = (material_desc or "").lower()
    mov = (movement_type or "").strip()
    fuel_keywords = ("diesel", "petrol", "gasoline", "fuel", "heating oil", "kerosene")
    if any(k in desc for k in fuel_keywords) or mov in ("201", "261"):
        return ActivityCategory.FUEL, Scope.SCOPE_1
    return ActivityCategory.PROCUREMENT, Scope.SCOPE_3


def _classify_travel(expense_type):
    t = (expense_type or "").lower()
    if "air" in t or "flight" in t or "fare" in t:
        return ActivityCategory.FLIGHT, Scope.SCOPE_3
    if "hotel" in t or "lodging" in t:
        return ActivityCategory.HOTEL, Scope.SCOPE_3
    return ActivityCategory.GROUND, Scope.SCOPE_3


def _flags_sap(plant_code, qty, unit, plants):
    flags = []
    if plant_code and plant_code not in plants:
        flags.append(f"Unknown plant code: {plant_code}")
    if qty and qty > Decimal("50000"):
        flags.append("Unusually high quantity")
    if unit and str(unit).lower() not in FUEL_UNITS and str(unit).lower() not in MASS_UNITS:
        flags.append(f"Unrecognized unit: {unit}")
    return flags


def _flags_utility(usage, period_start, period_end):
    flags = []
    if usage and usage > Decimal("500000"):
        flags.append("Unusually high kWh for single period")
    if period_start and period_end and period_end < period_start:
        flags.append("Billing period end before start")
    if not usage:
        flags.append("Missing consumption value")
    return flags


def _flags_travel(category, from_loc, to_loc, distance):
    flags = []
    if category == ActivityCategory.FLIGHT:
        if not from_loc and not to_loc:
            flags.append("Flight missing origin/destination")
        if from_loc and to_loc and len(from_loc) == 3 and len(to_loc) == 3:
            if from_loc == to_loc:
                flags.append("Same origin and destination airport")
    if category == ActivityCategory.GROUND and not distance:
        flags.append("Ground trip missing distance — estimate required")
    return flags


def parse_sap_file(file_obj, batch: IngestionBatch, plants: dict) -> dict:
    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")
    delim = _detect_delimiter(content[:2000])
    reader = csv.DictReader(io.StringIO(content), delimiter=delim)
    colmap = _map_headers(reader.fieldnames or [], SAP_HEADERS)
    required = {"document", "quantity", "unit"}
    missing = required - set(colmap)
    if missing:
        batch.status = "failed"
        batch.error_summary = f"Missing SAP columns: {', '.join(missing)}"
        batch.save()
        return {"error": batch.error_summary}

    org = batch.organization
    success = failed = flagged = 0
    for i, row in enumerate(reader, start=1):
        doc = row.get(colmap.get("document", ""), "") or f"row-{i}"
        item = row.get(colmap.get("item", ""), "") or str(i)
        row_id = f"{doc}-{item}"
        payload = {k: row.get(v, "") for k, v in colmap.items()}
        row_hash = _row_hash(SourceType.SAP, row_id, payload)

        qty = _parse_decimal(row.get(colmap.get("quantity", ""), ""))
        unit = row.get(colmap.get("unit", ""), "")
        plant = row.get(colmap.get("plant", ""), "").strip()
        desc = row.get(colmap.get("description", ""), "")
        mov = row.get(colmap.get("movement_type", ""), "")
        category, scope = _classify_sap(desc, mov)
        unit_map = FUEL_UNITS if category == ActivityCategory.FUEL else MASS_UNITS
        norm_qty, norm_unit = normalize_quantity(qty, unit, unit_map)

        flags = _flags_sap(plant, qty, unit, plants)
        errors = []
        if qty is None:
            errors.append("Could not parse quantity")
        review = ReviewStatus.FAILED if errors else (
            ReviewStatus.FLAGGED if flags else ReviewStatus.PENDING
        )

        plant_name = plants.get(plant, {}).get("name", "") if plant else ""
        try:
            ActivityRecord.objects.update_or_create(
                organization=org,
                source_type=SourceType.SAP,
                source_row_hash=row_hash,
                defaults={
                    "batch": batch,
                    "source_row_id": row_id,
                    "scope": scope,
                    "category": category,
                    "activity_date": _parse_date(row.get(colmap.get("posting_date", ""), "")),
                    "description": desc[:500],
                    "site_code": plant,
                    "site_name": plant_name,
                    "vendor": row.get(colmap.get("vendor", ""), "")[:200],
                    "quantity": qty,
                    "unit": unit,
                    "normalized_quantity": norm_qty,
                    "normalized_unit": norm_unit,
                    "currency": row.get(colmap.get("currency", ""), "")[:3],
                    "amount": _parse_decimal(row.get(colmap.get("amount", ""), "")),
                    "review_status": review,
                    "flags": flags,
                    "validation_errors": errors,
                    "raw_payload": payload,
                },
            )
            if review == ReviewStatus.FAILED:
                failed += 1
            elif review == ReviewStatus.FLAGGED:
                flagged += 1
            else:
                success += 1
        except Exception as e:
            failed += 1
            if i <= 3:
                batch.error_summary += f" Row {i}: {e}"

    return {"success": success, "failed": failed, "flagged": flagged, "total": success + failed + flagged}


def parse_utility_file(file_obj, batch: IngestionBatch) -> dict:
    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")
    delim = _detect_delimiter(content[:2000])
    reader = csv.DictReader(io.StringIO(content), delimiter=delim)
    colmap = _map_headers(reader.fieldnames or [], UTILITY_HEADERS)
    if "usage" not in colmap and "start" not in colmap:
        batch.status = "failed"
        batch.error_summary = "Unrecognized utility CSV format"
        batch.save()
        return {"error": batch.error_summary}

    org = batch.organization
    success = failed = flagged = 0
    for i, row in enumerate(reader, start=1):
        acct = row.get(colmap.get("account", ""), "") or f"meter-{i}"
        meter = row.get(colmap.get("meter", ""), "")
        row_id = f"{acct}-{meter}-{i}"
        payload = {k: row.get(v, "") for k, v in colmap.items()}
        row_hash = _row_hash(SourceType.UTILITY, row_id, payload)

        usage_col = colmap.get("usage", "")
        usage = _parse_decimal(row.get(usage_col, "")) if usage_col else None
        unit_raw = row.get(colmap.get("unit", ""), "kWh") or "kWh"
        p_start = _parse_date(row.get(colmap.get("start", ""), ""))
        p_end = _parse_date(row.get(colmap.get("end", ""), ""))
        norm_qty, norm_unit = normalize_quantity(usage, unit_raw, ENERGY_UNITS)
        flags = _flags_utility(usage, p_start, p_end)
        errors = []
        if usage is None:
            errors.append("Could not parse usage")
        review = ReviewStatus.FAILED if errors else (
            ReviewStatus.FLAGGED if flags else ReviewStatus.PENDING
        )

        site = row.get(colmap.get("site", ""), "")[:200]
        try:
            ActivityRecord.objects.update_or_create(
                organization=org,
                source_type=SourceType.UTILITY,
                source_row_hash=row_hash,
                defaults={
                    "batch": batch,
                    "source_row_id": row_id,
                    "scope": Scope.SCOPE_2,
                    "category": ActivityCategory.ELECTRICITY,
                    "activity_date": p_end or p_start,
                    "period_start": p_start,
                    "period_end": p_end,
                    "description": f"Electricity — {row.get(colmap.get('tariff', ''), '')}"[:500],
                    "site_name": site,
                    "vendor": "Utility",
                    "quantity": usage,
                    "unit": unit_raw,
                    "normalized_quantity": norm_qty,
                    "normalized_unit": norm_unit,
                    "amount": _parse_decimal(row.get(colmap.get("cost", ""), "")),
                    "review_status": review,
                    "flags": flags,
                    "validation_errors": errors,
                    "raw_payload": payload,
                },
            )
            if review == ReviewStatus.FAILED:
                failed += 1
            elif review == ReviewStatus.FLAGGED:
                flagged += 1
            else:
                success += 1
        except Exception:
            failed += 1

    return {"success": success, "failed": failed, "flagged": flagged, "total": success + failed + flagged}


def parse_travel_file(file_obj, batch: IngestionBatch) -> dict:
    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")
    delim = _detect_delimiter(content[:2000])
    reader = csv.DictReader(io.StringIO(content), delimiter=delim)
    colmap = _map_headers(reader.fieldnames or [], TRAVEL_HEADERS)
    if "expense_type" not in colmap:
        batch.status = "failed"
        batch.error_summary = "Unrecognized travel extract format"
        batch.save()
        return {"error": batch.error_summary}

    org = batch.organization
    success = failed = flagged = 0
    for i, row in enumerate(reader, start=1):
        entry = row.get(colmap.get("entry_id", ""), "") or str(i)
        report = row.get(colmap.get("report_id", ""), "")
        row_id = f"{report}-{entry}"
        payload = {k: row.get(v, "") for k, v in colmap.items()}
        row_hash = _row_hash(SourceType.TRAVEL, row_id, payload)

        expense_type = row.get(colmap.get("expense_type", ""), "")
        category, scope = _classify_travel(expense_type)
        from_loc = row.get(colmap.get("from_loc", ""), "").strip()
        to_loc = row.get(colmap.get("to_loc", ""), "").strip()
        dist = _parse_decimal(row.get(colmap.get("distance", ""), ""))
        dist_unit = row.get(colmap.get("distance_unit", ""), "mi")
        norm_qty, norm_unit = normalize_quantity(dist, dist_unit, DISTANCE_UNITS)
        flags = _flags_travel(category, from_loc, to_loc, dist)

        if category == ActivityCategory.FLIGHT and not dist:
            airport_re = re.compile(r"^[A-Z]{3}$")
            if airport_re.match(from_loc.upper()) and airport_re.match(to_loc.upper()):
                flags.append("Distance not provided — airport pair only")

        review = ReviewStatus.FLAGGED if flags else ReviewStatus.PENDING

        try:
            ActivityRecord.objects.update_or_create(
                organization=org,
                source_type=SourceType.TRAVEL,
                source_row_hash=row_hash,
                defaults={
                    "batch": batch,
                    "source_row_id": row_id,
                    "scope": scope,
                    "category": category,
                    "activity_date": _parse_date(
                        row.get(colmap.get("transaction_date", ""), "")
                    ),
                    "description": expense_type[:500],
                    "vendor": row.get(colmap.get("vendor", ""), "")[:200],
                    "quantity": dist,
                    "unit": dist_unit if dist else "",
                    "normalized_quantity": norm_qty,
                    "normalized_unit": norm_unit or "",
                    "currency": row.get(colmap.get("currency", ""), "")[:3],
                    "amount": _parse_decimal(row.get(colmap.get("amount", ""), "")),
                    "review_status": review,
                    "flags": flags,
                    "validation_errors": [],
                    "raw_payload": payload,
                },
            )
            if review == ReviewStatus.FLAGGED:
                flagged += 1
            else:
                success += 1
        except Exception:
            failed += 1

    return {"success": success, "failed": failed, "flagged": flagged, "total": success + failed + flagged}


def run_ingestion(source_type: str, file_obj, filename: str, user, organization):
    batch = IngestionBatch.objects.create(
        organization=organization,
        source_type=source_type,
        filename=filename,
        uploaded_by=user,
        status="processing",
    )
    AuditEvent.objects.create(
        organization=organization,
        batch=batch,
        actor=user,
        action="upload",
        detail={"filename": filename, "source_type": source_type},
    )

    plants = {
        p.code: {"name": p.name, "country": p.country}
        for p in PlantLookup.objects.filter(organization=organization)
    }

    if source_type == SourceType.SAP:
        stats = parse_sap_file(file_obj, batch, plants)
    elif source_type == SourceType.UTILITY:
        stats = parse_utility_file(file_obj, batch)
    elif source_type == SourceType.TRAVEL:
        stats = parse_travel_file(file_obj, batch)
    else:
        batch.status = "failed"
        batch.error_summary = "Unknown source type"
        batch.save()
        return batch

    if stats.get("error"):
        return batch

    total = stats["total"]
    batch.total_rows = total
    batch.success_rows = stats["success"]
    batch.failed_rows = stats["failed"]
    batch.flagged_rows = stats["flagged"]
    if stats["failed"] == total and total > 0:
        batch.status = "failed"
    elif stats["failed"] > 0:
        batch.status = "partial"
    else:
        batch.status = "completed"
    batch.save()
    return batch
