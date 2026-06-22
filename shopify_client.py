"""Shopify sales -> per-state totals for economic-nexus checking.

Reads a "sales by state" summary (the shape you get from Shopify's tax/finance
reports or by aggregating the Orders API) and normalizes each state's period
sales, order count, tax collected, and registration status — the facts the
economic-nexus check needs.
"""

from __future__ import annotations

import json


def extract(source: str) -> list[dict]:
    with open(source) as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else [data]


def normalize(rec: dict) -> dict:
    return {
        "state": (rec.get("state") or "").upper(),
        "sales": float(rec.get("period_sales", 0)),
        "orders": int(rec.get("period_orders", 0)),
        "tax_collected": float(rec.get("tax_collected", 0)),
        "registered": bool(rec.get("registered", False)),
        "home_state": bool(rec.get("home_state", False)),
    }
