from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "brand" / "asset-manifest.json"
README_PATH = REPO_ROOT / "README.md"
NAMING_DOC = REPO_ROOT / "docs" / "PREM3_BRAND_AND_NAMING.md"
BRAND_GUIDE = REPO_ROOT / "brand" / "README.md"
INVENTORY = REPO_ROOT / "brand" / "ASSET_INVENTORY.md"
DOCS_BRAND_POINTER = REPO_ROOT / "docs" / "brand" / "README.md"
README_LOGO = (
    "brand/brand-assets/reference/prem3-approved-primary-logo-reference.png"
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_brand_docs_and_readme_logo_exist() -> None:
    assert MANIFEST_PATH.is_file()
    assert README_PATH.is_file()
    assert NAMING_DOC.is_file()
    assert BRAND_GUIDE.is_file()
    assert INVENTORY.is_file()
    assert DOCS_BRAND_POINTER.is_file()
    assert (REPO_ROOT / README_LOGO).is_file()
    readme = README_PATH.read_text(encoding="utf-8")
    assert README_LOGO in readme
    assert 'alt="PreM3 — Map. Mend. Model."' in readme
    assert "width=\"640\"" in readme
    assert "ModelReady" not in readme.split("working name ModelReady")[0]
    assert "brand/brand-assets/" in DOCS_BRAND_POINTER.read_text(encoding="utf-8")
    assert "Approved PreM3 Brand System" in NAMING_DOC.read_text(encoding="utf-8")


def test_source_asset_hashes_match_manifest() -> None:
    payload = _manifest()
    assert payload["canonical_source_dir"] == "brand/brand-assets"
    assets = payload["assets"]
    assert assets
    for asset in assets:
        path = REPO_ROOT / asset["path"]
        assert path.is_file(), asset["path"]
        assert asset["source_asset"] is True
        if asset["format"] == "png":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == asset["sha256"], asset["path"]


def test_no_runtime_or_derived_logo_copies() -> None:
    payload = _manifest()
    assert payload["deployments"] == []
    assert payload["derived_assets"] == []
    assert payload["pending"]["MASTER_VECTOR_PENDING"] is True
    assets_dir = REPO_ROOT / "brand" / "brand-assets" / "assets"
    produced = [path for path in assets_dir.iterdir() if path.suffix.lower() in {".svg", ".png"}]
    assert produced == []
