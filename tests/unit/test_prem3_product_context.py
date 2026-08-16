"""Acceptance tests for canonical PreM3 product intelligence."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = (ROOT / "docs/context/prem3_product_context.md").read_text(encoding="utf-8")
BOOT = (ROOT / "docs/context/prem3_mmm_boot_context.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_product_context_exists_and_is_versioned() -> None:
    assert "Context version:** 2.0" in PRODUCT
    assert "Intelligence version:** 2.0.0" in PRODUCT
    assert "A self-learning, autonomous pre-modeling agent for Google Meridian" in PRODUCT


def test_four_behaviors_are_distinct_pillars() -> None:
    for heading in ("### ASSESS", "### ADVISE", "### INSIGHT", "### GUIDE"):
        assert heading in PRODUCT
    assert "Four-behavior product statement" in PRODUCT
    assert "assesses your marketing data" in PRODUCT.lower()
    assert "convert correlation into causal claims" in PRODUCT.lower()
    assert "what PreM3 can safely fix" in PRODUCT


def test_canonical_product_questions_are_answered() -> None:
    required = [
        "What are you?",
        "Why do you exist?",
        "What major problems do you solve?",
        "Who are you for?",
        "Why should I buy/adopt PreM3?",
        "Why not just use Meridian?",
        "Why not use a generic LLM/RAG system?",
        "Why not write scripts?",
        "Why not use an analyst or consultant?",
        "Why should I trust your handoff?",
        "What has been proven?",
        "What are you building next?",
        "What do you not do?",
        "What could make the product defensible over time?",
    ]
    for question in required:
        assert question in PRODUCT, f"missing product question: {question}"


def test_buyer_analyst_modeler_executive_lenses_exist() -> None:
    assert "### Buyer questions" in PRODUCT
    assert "### Analyst questions" in PRODUCT
    assert "### Modeler questions" in PRODUCT
    assert "### Executive questions" in PRODUCT
    assert "**Marketer:**" in PRODUCT
    assert "**Judge/investor:**" in PRODUCT


def test_proof_vs_roadmap_is_explicit() -> None:
    assert "## 14. What is proven today" in PRODUCT
    assert "## 15. Current / next capabilities" in PRODUCT
    assert "Do not turn roadmap capabilities into proven claims." in PRODUCT
    assert "MEL Episode Core" in PRODUCT
    assert "complete Episode Core and `EXPERIENCE_APPLIED` proof remain an active milestone" in PRODUCT


def test_product_claims_do_not_invent_roi() -> None:
    assert "Do not invent hours saved" in PRODUCT
    assert "Never invent:" in PRODUCT
    assert "customer counts;" in PRODUCT
    assert "Do not invent quantified ROI" in PRODUCT or "without measured evidence" in PRODUCT
    assert "saved 40 hours" not in PRODUCT.lower()
    assert "increased roi by" not in PRODUCT.lower()


def test_why_buy_answer_preserves_meaning() -> None:
    assert "does more than tell you whether a file passes a checklist" in PRODUCT
    assert "Where a repair is deterministic and safe, PreM3 can perform it." in PRODUCT
    assert "The goal is not to remove the modeler." in PRODUCT


def test_agents_routing_loads_boot_for_every_agent() -> None:
    assert "docs/context/prem3_mmm_boot_context.md" in AGENTS
    assert "docs/context/prem3_product_context.md" in AGENTS
    assert "meridian_data_prep_context.md" in AGENTS
    assert "meridian_advisor_playbook.md" in AGENTS
    assert "Do not turn execution agents into sales bots." in AGENTS


def test_boot_context_is_short_constitution() -> None:
    words = len(BOOT.split())
    assert words < 1200, f"boot context too long for every-agent load: {words} words"
    assert "Causal-first" in BOOT
    assert "Official Meridian sources outrank heuristics" in BOOT
    assert "Missing is not automatically zero" in BOOT
    assert "Do not append product marketing to execution work." in BOOT
