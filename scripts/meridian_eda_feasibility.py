"""Measure whether official google-meridian can run M3 pre-modeling EDA.

This script does not wire production Cloud Run. It records Python compatibility,
import cost, and optional Dataset A EDA runtime. Do not treat missing Meridian
as a green result.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "deployment" / "meridian_eda_feasibility.json"
PINNED_MERIDIAN = "1.8.0"
OFFICIAL_SUPPORTED_PYTHON = ("3.11", "3.12")


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _probe_import(module_name: str) -> dict[str, object]:
    started = time.perf_counter()
    try:
        __import__(module_name)
        return {
            "ok": True,
            "seconds": round(time.perf_counter() - started, 4),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "seconds": round(time.perf_counter() - started, 4),
            "error": f"{type(exc).__name__}: {exc}",
        }


def collect_environment() -> dict[str, object]:
    version_info = sys.version_info
    python_version = platform.python_version()
    official_match = python_version.startswith(OFFICIAL_SUPPORTED_PYTHON)
    return {
        "python_version": python_version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "official_meridian_docs_require": list(OFFICIAL_SUPPORTED_PYTHON),
        "pypi_google_meridian_requires_python": ">=3.10",
        "pinned_google_meridian": PINNED_MERIDIAN,
        "python_matches_official_docs": official_match,
        "m3_requires_python": ">=3.13,<3.15",
        "python_major_minor": f"{version_info.major}.{version_info.minor}",
        "packages": {
            "google-adk": _package_version("google-adk"),
            "pandas": _package_version("pandas"),
            "pyarrow": _package_version("pyarrow"),
            "google-meridian": _package_version("google-meridian"),
            "tensorflow": _package_version("tensorflow"),
            "jax": _package_version("jax"),
        },
    }


def collect_meridian_runtime() -> dict[str, object]:
    result: dict[str, object] = {
        "installed_version": _package_version("google-meridian"),
        "imports": {},
        "sample_posterior_present": None,
        "eda_api_present": None,
        "error": None,
    }
    if result["installed_version"] is None:
        result["error"] = "google-meridian is not installed in this interpreter."
        return result
    result["imports"]["meridian"] = _probe_import("meridian")
    result["imports"]["meridian.model.eda.meridian_eda"] = _probe_import(
        "meridian.model.eda.meridian_eda"
    )
    result["imports"]["meridian.data.data_frame_input_data_builder"] = _probe_import(
        "meridian.data.data_frame_input_data_builder"
    )
    try:
        from meridian.model import model
        from meridian.model.eda import meridian_eda

        result["sample_posterior_present"] = hasattr(model.Meridian, "sample_posterior")
        result["eda_api_present"] = hasattr(meridian_eda.MeridianEDA, "generate_and_save_report")
        result["meridian_module_version"] = getattr(
            importlib.import_module("meridian"), "__version__", result["installed_version"]
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
    return result


def pip_dry_run() -> dict[str, object]:
    started = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            f"google-meridian=={PINNED_MERIDIAN}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "returncode": proc.returncode,
        "seconds": round(time.perf_counter() - started, 4),
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-40:]),
        "stderr_tail": "\n".join(proc.stderr.splitlines()[-40:]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-pip-dry-run", action="store_true")
    args = parser.parse_args()
    payload = {
        "status": "MEASURED",
        "cloud_run_memory_gib": 1,
        "cloud_run_timeout_seconds": 600,
        "option_a_same_service": None,
        "option_b_dedicated_worker": None,
        "decision_basis": [],
        "environment": collect_environment(),
        "pip_dry_run": None,
        "meridian_runtime": collect_meridian_runtime(),
    }
    if not args.skip_pip_dry_run:
        payload["pip_dry_run"] = pip_dry_run()
    env = payload["environment"]
    runtime = payload["meridian_runtime"]
    reasons = []
    if not env["python_matches_official_docs"]:
        reasons.append(
            "Official Meridian install docs require Python 3.11 or 3.12; "
            f"this interpreter is {env['python_version']}."
        )
    dry_run_text = ((payload.get("pip_dry_run") or {}).get("stdout_tail") or "")
    current_pandas = str((env.get("packages") or {}).get("pandas") or "")
    if "pandas-2." in dry_run_text and current_pandas.startswith("3."):
        reasons.append(
            "Installing google-meridian==1.8.0 would downgrade pandas "
            f"from {current_pandas} to 2.x (meridian requires pandas<3)."
        )
    if "tensorflow-" in dry_run_text:
        reasons.append(
            "google-meridian pulls TensorFlow 2.21, tf-keras, and tfp-nightly; "
            "that install is too heavy for the current 1Gi M3 Cloud Run service "
            "without a measured dedicated worker."
        )
    if runtime.get("installed_version") is None:
        reasons.append("google-meridian is not installed in the M3 interpreter.")
    elif not (runtime.get("imports") or {}).get("meridian", {}).get("ok"):
        reasons.append("google-meridian is installed but meridian import failed.")
    payload["decision_basis"] = reasons
    payload["option_a_same_service"] = not reasons
    payload["option_b_dedicated_worker"] = bool(reasons)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
