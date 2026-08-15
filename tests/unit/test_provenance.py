from copy import deepcopy

from app.tools.provenance import FRAME_SOURCE_ROLES
from app.tools.validation import REQUIRED_DATASET_A_TOOLS, validate_provenance_complete

DIGEST = "ab" * 32


def _complete_manifest() -> dict:
    transforms = []
    for tool in REQUIRED_DATASET_A_TOOLS:
        if tool == "build_model_ready_frame":
            sources = [
                {"role": role, "uri": f"gs://bucket/{role}.csv", "sha256": f"{index:064d}"}
                for index, role in enumerate(FRAME_SOURCE_ROLES)
            ]
            transforms.append(
                {
                    "tool": tool,
                    "status": "APPLIED",
                    "source_sha256": sources[0]["sha256"],
                    "output_sha256": DIGEST,
                    "sources": sources,
                }
            )
            continue
        transforms.append(
            {
                "tool": tool,
                "status": "APPLIED",
                "source_sha256": DIGEST,
                "output_sha256": DIGEST,
                "sources": [{"role": "source", "uri": f"gs://bucket/{tool}.csv", "sha256": DIGEST}],
            }
        )
    return {"dataset_fingerprint": DIGEST, "transforms": transforms, "records": transforms}


def test_mr018_passes_complete_provenance() -> None:
    result = validate_provenance_complete(_complete_manifest(), REQUIRED_DATASET_A_TOOLS)
    assert result.passed is True
    assert result.rule_id == "MR-018"


def test_mr018_fails_when_source_hash_missing() -> None:
    manifest = _complete_manifest()
    first = manifest["transforms"][0]
    first["source_sha256"] = ""
    first["sources"] = [{"role": "source", "uri": "gs://bucket/in.csv", "sha256": ""}]
    result = validate_provenance_complete(manifest, REQUIRED_DATASET_A_TOOLS)
    assert result.passed is False
    assert first["tool"] in (result.evidence or {})["missing_input_fingerprints"]


def test_mr018_fails_when_full_frame_source_missing() -> None:
    manifest = deepcopy(_complete_manifest())
    frame = next(
        item for item in manifest["transforms"] if item["tool"] == "build_model_ready_frame"
    )
    frame["sources"] = [source for source in frame["sources"] if source["role"] != "population"]
    result = validate_provenance_complete(manifest, REQUIRED_DATASET_A_TOOLS)
    assert result.passed is False
    assert "population" in (result.evidence or {})["missing_frame_roles"]


def test_mr018_fails_when_final_output_fingerprint_missing() -> None:
    manifest = deepcopy(_complete_manifest())
    frame = next(
        item for item in manifest["transforms"] if item["tool"] == "build_model_ready_frame"
    )
    frame["output_sha256"] = ""
    result = validate_provenance_complete(manifest, REQUIRED_DATASET_A_TOOLS)
    assert result.passed is False
    assert (result.evidence or {})["final_output_sha256"] is None
