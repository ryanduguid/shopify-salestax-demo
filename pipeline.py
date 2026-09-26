#!/usr/bin/env python3
"""Compare the documented state sales summaries with dated illustrative thresholds."""

import argparse
from pathlib import Path
import sys
import textwrap

import shopify_client
import nexus_check
from oa_client import OAClient
from reporting import configure_output, safe_text


def run(source: str, oa: OAClient) -> bool:
    states = shopify_client.extract(source)
    plan = oa.start("Compare supplied totals with illustrative state thresholds", "US")
    if not isinstance(plan, dict):
        raise ValueError("start must return an object")
    skills = plan.get("skills_to_load", [])
    if not isinstance(skills, list) or any(not isinstance(slug, str) for slug in skills):
        raise ValueError("skills_to_load must be an array of names")
    skill = oa.get_skill(skills[0]) if skills else {}
    complete = True
    for index, record in enumerate(states, 1):
        try:
            facts = shopify_client.normalize(record, partial=True)
            verdict = nexus_check.check(facts, skill)
        except ValueError as error:
            print(f"\nState record {index}: invalid input: {safe_text(error)}")
            complete = False
            continue
        for error in facts["input_errors"]:
            print(f"\nState record {index}: invalid input: {safe_text(error)}")
        sales = "unknown sales" if facts["sales"] is None else f"USD {facts['sales']:,.2f} sales"
        print(f"\n🏬  {safe_text(facts['state'] or 'unknown state')} · {sales} · assessment {facts['assessment_date'] or 'unknown'}")
        print(f"    Period: {facts['period_start'] or 'unknown'} to {facts['period_end'] or 'unknown'}")
        if facts["state"] == "CA":
            prior = "unknown" if facts["prior_year_sales"] is None else f"USD {facts['prior_year_sales']:,.2f}"
            print(f"    Prior calendar-year sales: {prior}")
        if facts["state"] == "NY":
            orders = "unknown" if facts["orders"] is None else str(facts["orders"])
            print(f"    Eligible sales count: {orders}")
        trust = ("unverified sample rules" if verdict["provenance"] == "sample"
                 else "provider metadata; not independently verified")
        print(f"    OpenAccountants → {safe_text(verdict.get('oa_skill_name') or 'state thresholds')} ({trust})")
        marker = "ℹ️" if verdict["status"] == "info" else "⚠️"
        print(f"    {marker} {safe_text(verdict['headline'])}")
        print(textwrap.fill(safe_text(verdict["detail"]), width=96, initial_indent="       ", subsequent_indent="       "))
        for field, label in (("registered", "Registration reported"), ("home_state", "Home state reported")):
            print(f"    {label}: " + {True: "yes", False: "no", None: "unknown"}[facts[field]])
        collected = "unknown" if facts["tax_collected"] is None else f"USD {facts['tax_collected']:,.2f}"
        print(f"    Tax collected reported: {collected}; registration does not prove collection.")
        complete = complete and verdict["complete"]
    return complete


def main(argv: list[str]) -> int:
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=str(Path(__file__).parent / "samples/sales_by_state.json"))
    parser.add_argument("--live", action="store_true", help="use the unverified OpenAccountants adapter")
    args = parser.parse_args(argv[1:])
    oa = OAClient() if args.live else OAClient(token=None)
    if args.live and not oa.live:
        parser.error("--live requires OA_MCP_TOKEN")
    mode = "LIVE ADAPTER (unverified)" if oa.live else "BUNDLED ILLUSTRATIVE RULES"
    print(f"Shopify → OpenAccountants · threshold demo [{mode}]")
    try:
        complete = run(args.source, oa)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Comparison failed: {safe_text(error)}", file=sys.stderr)
        return 2
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
