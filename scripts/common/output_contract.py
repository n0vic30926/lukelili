"""Investment output classification helpers."""


SECTION_ORDER = (
    ("facts", "Facts"),
    ("inferences", "Data-Derived Inferences"),
    ("judgments", "Model Judgment"),
    ("confirmations", "User Confirmation Required"),
)


def _items(values):
    return [str(value) for value in values or [] if str(value)]


def format_output_sections(sections):
    lines = []
    for key, title in SECTION_ORDER:
        lines.append(f"## {title}")
        values = _items(sections.get(key))
        if values:
            for value in values:
                lines.append(f"- {value}")
        else:
            lines.append("- none")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_report_output_sections(report_type, portfolio, run_summary):
    holdings = portfolio.get("holdings", [])
    watchlist = portfolio.get("watchlist", [])
    modules = (run_summary or {}).get("modules", {})
    data_quality = (run_summary or {}).get("data_quality", {})

    facts = [
        f"report_type={report_type}",
        "execution_allowed=false",
        f"portfolio_source={(run_summary or {}).get('portfolio_source', 'unknown')}",
        f"is_example_data={str((run_summary or {}).get('is_example_data', False)).lower()}",
        f"holdings={len(holdings)} watchlist={len(watchlist)}",
    ]
    if modules:
        facts.append(
            "modules "
            f"success={modules.get('success', 0)} "
            f"failed={modules.get('failed', 0)} "
            f"skipped={modules.get('skipped', 0)}"
        )

    inferences = []
    if data_quality:
        inferences.append(
            "data_quality "
            f"fresh={data_quality.get('fresh', 0)} "
            f"stale={data_quality.get('stale', 0)} "
            f"unknown={data_quality.get('unknown', 0)}"
        )
    if modules and modules.get("failed", 0):
        inferences.append("some data modules failed; report may be incomplete")
    if modules and modules.get("skipped", 0):
        inferences.append("some data modules were skipped by configuration or missing inputs")

    return {
        "facts": facts,
        "inferences": inferences,
        "judgments": [
            "report risk reminders are decision support only",
            "strategy and discipline notes are model/rule judgment, not user consent",
        ],
        "confirmations": [
            "user verifies data freshness before any portfolio change",
            "user confirms strategy still applies",
            "user confirms no broker action should be automated",
        ],
    }


def with_output_contract(content, sections):
    rendered = format_output_sections(sections)
    lines = str(content or "").splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join([lines[0], "", rendered, ""] + lines[1:])
    if content:
        return f"{rendered}\n\n{content}"
    return rendered
