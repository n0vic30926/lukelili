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
