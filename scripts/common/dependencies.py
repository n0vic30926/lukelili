"""Runtime dependency checks for report entrypoints."""

import importlib.util
import sys


REPORT_DEPENDENCIES = ["akshare", "pandas", "numpy"]


def missing_modules(module_names):
    return [name for name in module_names if importlib.util.find_spec(name) is None]


def format_missing_dependency_message(script_name, missing):
    missing_text = ", ".join(missing)
    return "\n".join(
        [
            f"{script_name}: Missing required runtime dependencies: {missing_text}",
            "Install them manually with:",
            "python3 -m pip install -r requirements.txt",
        ]
    )


def exit_if_missing(script_name, module_names=None):
    missing = missing_modules(module_names or REPORT_DEPENDENCIES)
    if not missing:
        return False
    print(format_missing_dependency_message(script_name, missing), file=sys.stderr)
    return True

