"""Tests for scripts/prepare_judgment_prompts.py — Stage C upstream fixes.

Covers the two structural problems surfaced by Round 1 rubric (ADR-0004):

1. `extract_sub_elements` — Multi-element Decision parser (P1 fix; Task 2(a)).
   Round 1 ADR-0009 / ADR-0012 collapsed K=2 onto a single facet because the
   prompt had no hint that the source Decision was multi-element. The parser
   detects H3 sub-headers and top-level numbered lists.

2. `select_judgment_prefix` — CA structural-vs-axiom prefix dispatch (P2 fix;
   Task 2(b)). CA ADR-0001 received the four-axiom prefix despite being a pure
   structural ADR, causing C2 Framework Application WEAK in Round 1.
"""

from __future__ import annotations

import pytest

from scripts.prepare_judgment_prompts import (
    extract_sub_elements,
    select_judgment_prefix,
)


# ----- extract_sub_elements -------------------------------------------------


class TestExtractSubElementsH3:
    """H3 sub-headers are the primary detection path (priority over numbered)."""

    def test_three_h3_sub_headers(self):
        """ADR-0009 shape: 3 numbered H3 + 1 boilerplate "What does not change"."""
        decision = (
            "## Decision\n\n"
            "AKC is reframed as a knowledge cycle.\n\n"
            "### 1. Cycle as the sole defining characteristic\n\n"
            "Body of element 1.\n\n"
            "### 2. Security by Absence demoted to a design principle\n\n"
            "Body of element 2.\n\n"
            "### 3. Bidirectional growth made explicit\n\n"
            "Body of element 3.\n\n"
            "### What does not change\n\n"
            "Boilerplate trailer.\n"
        )
        result = extract_sub_elements(decision)
        assert result == [
            "1. Cycle as the sole defining characteristic",
            "2. Security by Absence demoted to a design principle",
            "3. Bidirectional growth made explicit",
        ]

    def test_six_h3_sub_headers(self):
        """ADR-0012 shape: 6 numbered H3 + 1 boilerplate."""
        decision = (
            "## Decision\n\n"
            "Restructure front-door docs.\n\n"
            '### 1. README.md "What is AKC?" rewrite\n\n'
            "Body.\n\n"
            '### 2. README.md "Why AKC" H2 placed before the repo tree\n\n'
            "Body.\n\n"
            "### 3. llms.txt blockquote reordered\n\n"
            "Body.\n\n"
            "### 4. llms-full.txt opening rewrite + Q&A reorder\n\n"
            "Body.\n\n"
            "### 5. Translations sync\n\n"
            "Body.\n\n"
            "### 6. GitHub repo About is updated\n\n"
            "Body.\n\n"
            "### What does not change\n\n"
            "Trailer.\n"
        )
        result = extract_sub_elements(decision)
        assert len(result) == 6
        assert result[0].startswith("1. README.md")
        assert result[5].startswith("6. GitHub repo About")

    def test_what_stays_the_same_is_also_filtered(self):
        """Alternative boilerplate variants ('What stays the same') are filtered."""
        decision = (
            "### 1. First element\n\nBody.\n\n"
            "### 2. Second element\n\nBody.\n\n"
            "### 3. Third element\n\nBody.\n\n"
            "### What stays the same\n\nTrailer.\n"
        )
        result = extract_sub_elements(decision)
        assert result == ["1. First element", "2. Second element", "3. Third element"]

    def test_two_h3_below_threshold_returns_empty(self):
        """Below 3 H3 sub-headers → not enough structure for K=2 facet hint."""
        decision = (
            "### Single concern\n\nBody.\n\n"
            "### Second concern\n\nBody.\n"
        )
        result = extract_sub_elements(decision)
        assert result == []

    def test_h3_takes_priority_over_inner_numbered_list(self):
        """ADR-0012 H3 #1 contains an inner '1./2./3./4.' numbered list.

        The parser must return the outer H3 titles, not the inner numbered
        elements, because the K=2 alternatives must engage different *top-level*
        Decision elements.
        """
        decision = (
            "### 1. Outer element one\n\n"
            "Body with inner numbered list:\n"
            "1. **Inner first.** Inner body.\n"
            "2. **Inner second.** Inner body.\n"
            "3. **Inner third.** Inner body.\n\n"
            "### 2. Outer element two\n\nBody.\n\n"
            "### 3. Outer element three\n\nBody.\n"
        )
        result = extract_sub_elements(decision)
        assert result == [
            "1. Outer element one",
            "2. Outer element two",
            "3. Outer element three",
        ]


class TestExtractSubElementsNumberedList:
    """Fallback path: top-level numbered list when no H3 structure exists."""

    def test_top_level_numbered_list(self):
        decision = (
            "## Decision\n\n"
            "Adopt the following:\n\n"
            "1. First decision item\n"
            "2. Second decision item\n"
            "3. Third decision item\n"
        )
        result = extract_sub_elements(decision)
        assert result == [
            "First decision item",
            "Second decision item",
            "Third decision item",
        ]

    def test_top_level_numbered_with_bold(self):
        decision = (
            "1. **First.** Body of first.\n"
            "2. **Second.** Body of second.\n"
            "3. **Third.** Body of third.\n"
        )
        result = extract_sub_elements(decision)
        assert len(result) == 3
        assert result[0].startswith("First")
        assert result[2].startswith("Third")

    def test_two_numbered_items_below_threshold(self):
        decision = "1. Only one\n2. Only two\n"
        result = extract_sub_elements(decision)
        assert result == []

    def test_inline_bold_with_prose_does_not_leak_markdown(self):
        """Regression: ``**Title.** Rest`` must not leak `**` into hint.

        Before fix, char-set ``strip("*")`` left dangling trailing ``**``
        markers on AKC ADR-0008 / ADR-0011 numbered Decision items.
        """
        decision = (
            "1. **LLM → Code guard.** LLM produces structured output.\n"
            "2. **Code filter → LLM.** Code narrows noisy input.\n"
            "3. **LLM judge + Code enforce.** LLM decides.\n"
        )
        result = extract_sub_elements(decision)
        assert len(result) == 3
        assert not any("**" in r for r in result), result


class TestExtractSubElementsFallbackGuard:
    """Numbered-list fallback fires ONLY when no substantive H3 exists."""

    def test_two_h3_plus_inner_numbered_does_not_promote_inner(self):
        """Regression: 2 substantive H3 + inner 1./2./3. → empty (NOT inner items).

        Before fix, the numbered-list fallback would promote inner steps as
        top-level facets when H3 count was below threshold. Now guarded by
        the "any substantive H3 → stop" check.
        """
        decision = (
            "### 1. Outer element one\n\n"
            "Body with inner numbered list:\n"
            "1. **Inner first.** Inner body.\n"
            "2. **Inner second.** Inner body.\n"
            "3. **Inner third.** Inner body.\n\n"
            "### 2. Outer element two\n\nBody.\n\n"
            "### What does not change\n\nTrailer.\n"
        )
        result = extract_sub_elements(decision)
        assert result == []


class TestExtractSubElementsSingleton:
    """Singleton decisions (no clear multi-element structure)."""

    def test_plain_prose_decision(self):
        decision = (
            "## Decision\n\n"
            "We will adopt approach X for reasons Y and Z. "
            "The implementation should preserve invariant W."
        )
        result = extract_sub_elements(decision)
        assert result == []

    def test_decision_with_only_bullets(self):
        """Bullets ('-') do not count as enumerated sub-elements."""
        decision = (
            "Adopt approach X with these properties:\n\n"
            "- Property A\n"
            "- Property B\n"
            "- Property C\n"
        )
        result = extract_sub_elements(decision)
        assert result == []

    def test_decision_with_only_boilerplate_h3(self):
        """If the only H3 is 'What does not change', return empty."""
        decision = (
            "Adopt approach X.\n\n"
            "### What does not change\n\n"
            "Y stays Y.\n"
        )
        result = extract_sub_elements(decision)
        assert result == []


# ----- select_judgment_prefix -----------------------------------------------


class TestSelectJudgmentPrefixCaStructural:
    """CA structural ADRs receive the structural prefix instead of axiom."""

    def _ca_line_cfg(self) -> dict:
        """Mirrors the new line_templates.yaml CA section shape."""
        return {
            "judgment_prefix": {
                "axiom": {
                    "en": "Applying the four contemplative axioms ...",
                    "ja": "4 つの contemplative axiom ...",
                },
                "structural": {
                    "en": "In the Contemplative Agent codebase ...",
                    "ja": "Contemplative Agent codebase では ...",
                },
            },
            "structural_adrs": ["0001", "0003"],
        }

    def test_structural_adr_selects_structural_prefix(self):
        cfg = self._ca_line_cfg()
        prefix = select_judgment_prefix(
            cfg,
            adr_source="docs/adr/0001-core-adapter-separation.md#decision",
            lang="en",
        )
        assert prefix.startswith("In the Contemplative Agent codebase")

    def test_non_structural_adr_selects_axiom_prefix(self):
        cfg = self._ca_line_cfg()
        prefix = select_judgment_prefix(
            cfg,
            adr_source="docs/adr/0002-paper-faithful-ccai.md#decision",
            lang="en",
        )
        assert prefix.startswith("Applying the four contemplative axioms")

    def test_japanese_lang_selects_japanese_prefix(self):
        cfg = self._ca_line_cfg()
        prefix = select_judgment_prefix(
            cfg,
            adr_source="docs/adr/0001-core-adapter-separation.md#decision",
            lang="ja",
        )
        assert "Contemplative Agent codebase" in prefix
        assert "では" in prefix


class TestSelectJudgmentPrefixLegacySchema:
    """Other lines (akc / aap / authorship-strategy) keep flat {en, ja} schema."""

    def _akc_line_cfg(self) -> dict:
        return {
            "judgment_prefix": {
                "en": "In the Agent Knowledge Cycle program ...",
                "ja": "Agent Knowledge Cycle では ...",
            },
        }

    def test_legacy_flat_schema_en(self):
        cfg = self._akc_line_cfg()
        prefix = select_judgment_prefix(
            cfg,
            adr_source="docs/adr/0009-akc-is-a-cycle-not-a-harness.md#decision",
            lang="en",
        )
        assert prefix.startswith("In the Agent Knowledge Cycle")

    def test_legacy_flat_schema_ja(self):
        cfg = self._akc_line_cfg()
        prefix = select_judgment_prefix(
            cfg,
            adr_source="docs/adr/0001-some-adr.md#decision",
            lang="ja",
        )
        assert prefix.startswith("Agent Knowledge Cycle")


class TestSelectJudgmentPrefixEdgeCases:
    """Edge cases that should not crash."""

    def test_missing_structural_adrs_list_defaults_to_axiom(self):
        """If a line has the new schema but no structural_adrs list, default to axiom."""
        cfg = {
            "judgment_prefix": {
                "axiom": {"en": "AXIOM EN"},
                "structural": {"en": "STRUCTURAL EN"},
            },
            # no structural_adrs key
        }
        prefix = select_judgment_prefix(
            cfg,
            adr_source="docs/adr/0001-any.md#decision",
            lang="en",
        )
        assert prefix == "AXIOM EN"

    def test_adr_number_not_parseable_defaults_to_axiom(self):
        """Sources without a 4-digit ADR number default to the axiom prefix."""
        cfg = {
            "judgment_prefix": {
                "axiom": {"en": "AXIOM EN"},
                "structural": {"en": "STRUCTURAL EN"},
            },
            "structural_adrs": ["0001"],
        }
        prefix = select_judgment_prefix(
            cfg,
            adr_source="docs/somewhere/not-an-adr.md",
            lang="en",
        )
        assert prefix == "AXIOM EN"

    def test_flat_schema_keyerror_on_missing_lang_not_swallowed(self):
        """Regression: partial flat schema must KeyError on missing lang.

        Before fix, ``lang in prefix_cfg`` returned False for the missing
        lang and the dispatcher fell through to the variant-aware branch,
        raising a confusing ``KeyError: 'axiom'``. Detection now keys on
        ``"axiom" not in prefix_cfg`` so a partial flat schema raises a
        precise ``KeyError`` naming the missing language key.
        """
        cfg = {"judgment_prefix": {"en": "EN ONLY"}}  # ja absent
        with pytest.raises(KeyError, match="ja"):
            select_judgment_prefix(
                cfg,
                adr_source="docs/adr/0001-any.md",
                lang="ja",
            )
