#!/usr/bin/env python3
"""Shopify -> OpenAccountants sales-tax economic-nexus pipeline.

    python pipeline.py                       # bundled sample sales-by-state (mock mode)
    python pipeline.py samples/sales_by_state.json

The flow:
    Shopify sales by state -> OA MCP (start -> get_skill) -> nexus check -> verdict

Set OA_MCP_TOKEN to use the live verified nexus thresholds.
"""

from __future__ import annotations

import os
import sys

import shopify_client
import nexus_check
from oa_client import OAClient

STATUS = {"ok": "✅", "warn": "⚠️ ", "info": "ℹ️ "}


def run(source: str, oa: OAClient) -> None:
    states = shopify_client.extract(source)
    plan = oa.start("Check sales-tax economic nexus", "US")
    slug = (plan.get("skills_to_load") or [None])[0]
    skill = oa.get_skill(slug) if slug else {}

    for rec in states:
        s = shopify_client.normalize(rec)
        print(f"\n🏬  {s['state']} · ${s['sales']:,.0f} sales · {s['orders']} orders · ${s['tax_collected']:,.0f} collected")
        v = nexus_check.check(s, skill)
        trust = f"tier {v.get('tier')}" + (f", signed off by {v['verifier']}" if v.get("verifier") else "")
        print(f"    OpenAccountants → {v.get('oa_skill_name') or 'nexus rules'}  ({trust})")
        print(f"    {STATUS.get(v['status'], '')} {v['headline']}")
        print(f"       {v['detail']}")


def main(argv: list[str]) -> int:
    oa = OAClient()
    mode = "LIVE" if oa.live else "MOCK (set OA_MCP_TOKEN to use the live verified thresholds)"
    print(f"Shopify → OpenAccountants · sales-tax economic-nexus demo  [{mode}]")
    here = os.path.dirname(os.path.abspath(__file__))
    source = argv[1] if len(argv) > 1 else os.path.join(here, "samples", "sales_by_state.json")
    run(source, oa)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
