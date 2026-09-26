"""Read the documented USD sales-summary format; no Shopify API adapter is included."""

from datetime import date
from decimal import Decimal, InvalidOperation
import json

from json_contract import input_decimal, input_integer, reject_json_constant, unique_object


def extract(source: str) -> list[dict]:
    with open(source, encoding="utf-8") as fh:
        data = json.load(fh, parse_float=input_decimal, parse_int=input_integer,
                         parse_constant=reject_json_constant, object_pairs_hook=unique_object)
    if data == []:
        raise ValueError("input must contain at least one record")
    return data if isinstance(data, list) else [data]


def number(value, field, *, whole=False):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number, not a Boolean")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"{field} must be a decimal number") from error
    if not result.is_finite() or not 0 <= result <= Decimal("1e12"):
        raise ValueError(f"{field} must be finite and between 0 and 1e12")
    if whole:
        if result != result.to_integral_value():
            raise ValueError(f"{field} must be a whole number")
        return int(result)
    if result.as_tuple().exponent < -2:
        raise ValueError(f"{field} supports at most two decimal places")
    return result


def text(value, field):
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    return value.strip() if value is not None else None


def boolean(value, field):
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{field} must be true, false or null")
    return value


def calendar_date(value, field):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must use YYYY-MM-DD")
    try:
        result = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be a valid YYYY-MM-DD date") from error
    if result.isoformat() != value:
        raise ValueError(f"{field} must use YYYY-MM-DD")
    return result


def normalize(rec: dict, *, partial=False) -> dict:
    if not isinstance(rec, dict):
        raise ValueError("each state summary must be an object")
    converters = {
        "state": ("state", text), "sales": ("period_sales", number),
        "prior_year_sales": ("prior_year_sales", number),
        "orders": ("period_orders", lambda value, field: number(value, field, whole=True)),
        "tax_collected": ("tax_collected", number), "registered": ("registered", boolean),
        "home_state": ("home_state", boolean), "assessment_date": ("assessment_date", calendar_date),
        "period_start": ("period_start", calendar_date), "period_end": ("period_end", calendar_date),
        "sales_basis": ("sales_basis", text),
    }
    facts, errors = {}, []
    for target, (field, convert) in converters.items():
        try:
            facts[target] = convert(rec.get(field), field)
        except ValueError as error:
            if not partial:
                raise
            facts[target] = None
            errors.append(str(error))
    facts["state"] = facts["state"].upper() if facts["state"] else None
    return {**facts, "input_errors": errors}
