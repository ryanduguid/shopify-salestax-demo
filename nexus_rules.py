"""Fixed illustrative threshold contract; sources and exclusions are in README.md."""

# ponytail: Fixed 2026 snapshot; expand with verified state contracts and boundary tests.
RULES = {
    "schema": "state-threshold-screen-v1",
    "covered_from": "2026-01-01",
    "covered_through": "2026-09-26",
    "thresholds": {
        "IL": {"amount": "100000", "comparison": "gte", "orders": None,
               "period": "calendar_quarters", "sales_basis": "il_tpp_gross_receipts"},
        "NY": {"amount": "500000", "comparison": "gt", "orders": 100,
               "period": "sales_tax_quarters", "sales_basis": "ny_tpp_gross_receipts"},
        "CA": {"amount": "500000", "comparison": "gt", "orders": None,
               "period": "current_and_prior_year", "sales_basis": "ca_related_tpp_sales"},
        "PA": {"amount": "100000", "comparison": "gte", "orders": None,
               "period": "prior_year", "sales_basis": "pa_eligible_gross_sales"},
        "FL": {"amount": "100000", "comparison": "gt", "orders": None,
               "period": "prior_year", "sales_basis": "fl_taxable_remote_sales"},
        "TX": {"amount": "500000", "comparison": "gt_review_equal", "orders": None,
               "period": "calendar_months", "sales_basis": "tx_total_revenue"},
    },
}
