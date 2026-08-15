import json
from pathlib import Path

import pandas as pd
import pytest

from app.core.errors import RegistryTrustError, ValidationBlockedError
from app.tools.adk_tools import (
    apply_mapping_to_file,
    canonicalize_channel_labels_in_file,
    get_meridian_pocket_card,
    lookup_provider_card,
    set_model_ready_gate,
    write_meridian_contract,
)
from app.tools.io import write_table


def test_lookup_provider_card_found() -> None:
    result = lookup_provider_card("shopify")
    assert result["found"] is True
    assert result["entry"]["provider_id"] == "shopify"


def test_apply_mapping_blocks_directory_provider(tmp_path: Path) -> None:
    path = tmp_path / "tiktok.csv"
    write_table(pd.DataFrame({"spend": [1]}), path)
    with pytest.raises(RegistryTrustError):
        apply_mapping_to_file(
            str(path),
            {"spend": "media_spend"},
            str(tmp_path / "out.csv"),
            provider_id="tiktok_ads",
        )


def test_canonicalize_tool_reports_unmapped(tmp_path: Path) -> None:
    path = tmp_path / "meta.csv"
    write_table(pd.DataFrame({"channel": ["Meta", "unknown"]}), path)
    result = canonicalize_channel_labels_in_file(
        str(path),
        "channel",
        {"Meta": "paid_social"},
        str(tmp_path / "out.csv"),
    )
    assert result["unmapped_values"] == ["unknown"]


def test_set_model_ready_gate_requires_all_proofs(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    contract_path = tmp_path / "contract.json"
    readiness.write_text(json.dumps({"all_passed": True}), encoding="utf-8")
    write_meridian_contract(
        str(contract_path),
        run_id="run-1",
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run-1",
        time_field="time",
        kpi_field="kpi_orders",
        geo_field="geo",
    )
    with pytest.raises(ValidationBlockedError):
        set_model_ready_gate(str(readiness), "FAIL", str(contract_path))
    gate = set_model_ready_gate(str(readiness), "PASS", str(contract_path))
    assert gate["status"] == "MODEL_READY"


def test_pocket_card_forbids_prose_model_ready() -> None:
    card = get_meridian_pocket_card()
    assert "deterministic_readiness_pass" in card["model_ready_requires"]
    assert "MR-006" in card["rules"]
