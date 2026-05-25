"""Unit normalization helpers — prototype uses simple conversion tables."""

from decimal import Decimal, InvalidOperation

LITRE_TO_L = Decimal("1")
GAL_TO_L = Decimal("3.78541")
KG_TO_KG = Decimal("1")
LB_TO_KG = Decimal("0.453592")
KWH_TO_KWH = Decimal("1")
MWH_TO_KWH = Decimal("1000")

FUEL_UNITS = {
    "l": ("L", LITRE_TO_L),
    "litre": ("L", LITRE_TO_L),
    "litres": ("L", LITRE_TO_L),
    "liter": ("L", LITRE_TO_L),
    "liters": ("L", LITRE_TO_L),
    "gal": ("L", GAL_TO_L),
    "gallon": ("L", GAL_TO_L),
    "gallons": ("L", GAL_TO_L),
}

MASS_UNITS = {
    "kg": ("kg", KG_TO_KG),
    "kilogram": ("kg", KG_TO_KG),
    "kilograms": ("kg", KG_TO_KG),
    "lb": ("kg", LB_TO_KG),
    "lbs": ("kg", LB_TO_KG),
    "pound": ("kg", LB_TO_KG),
}

ENERGY_UNITS = {
    "kwh": ("kWh", KWH_TO_KWH),
    "kw·h": ("kWh", KWH_TO_KWH),
    "mwh": ("kWh", MWH_TO_KWH),
}

DISTANCE_UNITS = {
    "km": ("km", Decimal("1")),
    "mi": ("km", Decimal("1.60934")),
    "mile": ("km", Decimal("1.60934")),
    "miles": ("km", Decimal("1.60934")),
}


def normalize_quantity(value, unit_raw, unit_map):
    if value is None or unit_raw is None:
        return None, None
    key = str(unit_raw).strip().lower().replace(" ", "")
    try:
        qty = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None, None
    if key not in unit_map:
        return qty, unit_raw
    norm_unit, factor = unit_map[key]
    return qty * factor, norm_unit
