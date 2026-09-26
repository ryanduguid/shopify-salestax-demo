"""Compare explicitly scoped sales totals without determining collection duties."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from nexus_rules import RULES


def expected_period(assessment, period):
    if period == "prior_year":
        return date(assessment.year - 1, 1, 1), date(assessment.year - 1, 12, 31)
    if period == "current_and_prior_year":
        return date(assessment.year, 1, 1), assessment
    if period == "calendar_months":
        end = assessment.replace(day=1) - timedelta(days=1)
    else:
        months = (3, 6, 9, 12) if period == "calendar_quarters" else (2, 5, 8, 11)
        ends = [date(year, month, monthrange(year, month)[1])
                for year in (assessment.year - 1, assessment.year) for month in months]
        end = max(candidate for candidate in ends if candidate <= assessment)
    start = date(end.year - 1 + (end.month == 12), end.month % 12 + 1, 1)
    return start, end


def check(s: dict, oa_skill: dict) -> dict:
    base = {
        "oa_skill": oa_skill.get("slug"), "oa_skill_name": oa_skill.get("name"),
        "provenance": oa_skill.get("provenance", "unverified"),
        "reported_metadata": {key: oa_skill.get(key) for key in ("tier", "verifier", "source")},
        "state": s["state"], "threshold_met": None, "complete": False,
    }
    missing = []
    rules = oa_skill.get("rules", {})
    if rules != RULES:
        missing.append("supported rule contract")
    threshold = RULES["thresholds"].get(s["state"])
    if threshold is None:
        missing.append("supported state")
    assessment = s["assessment_date"]
    if assessment is None or not date.fromisoformat(RULES["covered_from"]) <= assessment <= date.fromisoformat(RULES["covered_through"]):
        missing.append("assessment date within the verified example coverage")
    elif threshold is not None:
        expected = expected_period(assessment, threshold["period"])
        if (s["period_start"], s["period_end"]) != expected:
            missing.append(f"measurement period {expected[0]} to {expected[1]}")
    if threshold is not None:
        if s["sales_basis"] != threshold["sales_basis"]:
            missing.append("explicit " + threshold["sales_basis"] + " sales basis")
        if threshold["period"] == "current_and_prior_year" and s["prior_year_sales"] is None:
            missing.append("prior calendar-year sales")
        if threshold["orders"] is not None and s["orders"] is None:
            missing.append("period_orders")
    if s["sales"] is None:
        missing.append("period_sales")
    if not missing:
        amount = Decimal(threshold["amount"])
        sales = max(s["sales"], s["prior_year_sales"]) if threshold["period"] == "current_and_prior_year" else s["sales"]
        comparison = threshold["comparison"]
        if comparison == "gt_review_equal" and sales == amount:
            missing.append("Texas equality boundary review")
        else:
            met = sales >= amount if comparison == "gte" else sales > amount
            if threshold["orders"] is not None:
                met = met and s["orders"] > threshold["orders"]
            base["threshold_met"] = met
    for field in ("registered", "home_state", "tax_collected"):
        if s[field] is None:
            missing.append(field)
    met = base["threshold_met"]
    headline = ("Threshold comparison incomplete" if met is None else
                "Supplied totals meet the modelled threshold" if met else
                "Supplied totals do not meet the modelled threshold")
    detail = "This comparison does not establish nexus, collection timing, tax due or correct collection."
    if missing:
        detail = "Missing or unsupported: " + ", ".join(missing) + ". " + detail
    complete = not missing and not s.get("input_errors")
    return {**base, "complete": complete, "status": "incomplete" if not complete else "review" if met else "info",
            "headline": headline, "detail": detail}
