"""Interpret report data-module status into source-level impact notes."""


def interpret_data_module(item):
    module = str(item.get("module") or "unknown")
    status = str(item.get("status") or "unknown")
    freshness = str(item.get("freshness") or "unknown")

    if status == "success":
        return (
            f"{module} source_interpretation=available; "
            f"freshness={freshness}; usable with source freshness check"
        )
    if status == "failed":
        return (
            f"{module} source_interpretation=unavailable; "
            "report section remains incomplete until source recovers"
        )
    if status == "skipped":
        return (
            f"{module} source_interpretation=skipped; "
            "interpret as configuration or missing inputs, not a market signal"
        )
    return (
        f"{module} source_interpretation=unknown; "
        "treat related report section as unverified"
    )
