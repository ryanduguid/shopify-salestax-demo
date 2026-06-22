"""Check a state's sales against the loaded OA economic-nexus thresholds.

The catch: economic nexus means you owe sales tax in a state once your sales
there cross a threshold ($100k or 200 transactions in many states) — with no
physical presence at all. Cross it and not collect, and the unremitted tax is
your liability. This flags the states where you're over the line and not
collecting, the ones you're approaching, and your physical-nexus home state.

DELIBERATE SCOPE: registration/economic-nexus signal only (not marketplace-
facilitator carve-outs, product taxability, or local district rates). Production
leans on the full OA skill + an agent step; the named-CPA sign-off makes it
relianceable.
"""

from __future__ import annotations


def check(s: dict, oa_skill: dict) -> dict:
    rules = oa_skill.get("rules", {})
    thresholds = rules.get("thresholds", {})
    base = {"oa_skill": oa_skill.get("slug"), "oa_skill_name": oa_skill.get("name"),
            "tier": oa_skill.get("tier"), "verifier": oa_skill.get("verifier")}
    st = s["state"]
    collecting = s["tax_collected"] > 0.005 or s["registered"]

    # Home state = physical nexus, always collect.
    if s["home_state"]:
        if collecting:
            return {**base, "status": "ok", "state": st,
                    "headline": f"{st} — home state (physical nexus), collecting ✓",
                    "detail": f"${s['sales']:,.0f} in sales, ${s['tax_collected']:,.0f} tax collected."}
        return {**base, "status": "warn", "state": st,
                "headline": f"{st} — home state (physical nexus) but NOT collecting",
                "detail": f"Physical presence creates nexus regardless of sales; you must register and collect."}

    th = thresholds.get(st)
    if not th:
        return {**base, "status": "info", "state": st,
                "headline": f"{st} — threshold not in the loaded skill",
                "detail": f"${s['sales']:,.0f} in sales; confirm {st}'s nexus rule."}

    over_amt = th.get("amount") is not None and s["sales"] >= th["amount"]
    over_tx = th.get("transactions") is not None and s["orders"] >= th["transactions"]
    nexus = (over_amt and over_tx) if th.get("combine") == "and" else (over_amt or over_tx)

    thr_str = (f"${th['amount']:,.0f}" if th.get("amount") else "")
    if th.get("transactions"):
        thr_str += f" {'AND' if th.get('combine') == 'and' else 'or'} {th['transactions']} sales"

    if nexus and not collecting:
        return {**base, "status": "warn", "state": st,
                "headline": f"{st} — economic nexus CROSSED, not collecting",
                "detail": f"${s['sales']:,.0f} / {s['orders']} sales is over the {thr_str} threshold — register and collect; unremitted tax is your liability."}
    if nexus and collecting:
        return {**base, "status": "ok", "state": st,
                "headline": f"{st} — nexus crossed, collecting ✓",
                "detail": f"${s['sales']:,.0f} in sales over the {thr_str} threshold; ${s['tax_collected']:,.0f} collected."}

    # AND-combine state where only the dollar test is met (e.g. NY).
    if th.get("combine") == "and" and over_amt and not over_tx:
        return {**base, "status": "info", "state": st,
                "headline": f"{st} — no nexus yet (requires BOTH tests)",
                "detail": f"${s['sales']:,.0f} is over the ${th['amount']:,.0f} amount, but {st} also needs {th['transactions']}+ sales — you have {s['orders']}."}

    # Not over threshold — note if approaching the dollar test.
    pct = (s["sales"] / th["amount"]) if th.get("amount") else 0
    if pct >= 0.7:
        return {**base, "status": "info", "state": st,
                "headline": f"{st} — approaching nexus ({pct:.0%} of {thr_str})",
                "detail": f"${s['sales']:,.0f} of the {thr_str} threshold — monitor; no obligation yet."}
    return {**base, "status": "info", "state": st,
            "headline": f"{st} — no economic nexus yet",
            "detail": f"${s['sales']:,.0f} / {s['orders']} sales is under the {thr_str} threshold."}
