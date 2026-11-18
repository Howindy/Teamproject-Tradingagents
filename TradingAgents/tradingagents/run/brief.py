"""FR-08 deterministic fallback and caller-protected delivery boundary.

This first-stage helper does not assemble prompts or implement references,
full-report fallback, budget expansion, publication, or a production tokenizer.
The caller supplies authoritative evidence; report prose is never its source.
"""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


class BriefConfigurationError(ValueError):
    """The standalone brief cannot be measured or configured reliably."""


class TokenCounter(Protocol):
    """Injected model/tokenizer identity and exact text-measurement boundary."""

    tokenizer_id: str
    tokenizer_version: str
    model_id: str

    def count(self, text: str) -> int: ...


@dataclass(frozen=True)
class BriefResult:
    """A view only, never a replacement for stored reports or a final decision.

    Rejection has no deliverable text and zero delivered tokens. mandatory_tokens
    still describes the complete, untruncated protected block for diagnostics.
    """

    status: str
    text: str | None
    rejection_reason: str | None
    mandatory_tokens: int
    total_tokens: int
    narrative_tokens: int = 0
    protected_content: str = ""
    coverage_view_version: str = ""


_REPORT_ORDER = (
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
)


class DownstreamBriefBuilder:
    """Extract original prose, reserving mandatory evidence before narrative.

    Extraction considers distinct, non-repeated paragraphs first,
    interleaved by report; repeated background last. Oversized ordinary
    paragraphs may reduce to complete sentences.
    Narrative is unlabeled to avoid unnecessary per-report label overhead; the
    caller-owned protected block carries explicit begin/end protection markers.
    """

    def __init__(self, *, token_counter: TokenCounter):
        self._counter = token_counter

    def _count(self, text: str) -> int:
        try:
            tokens = self._counter.count(text)
        except Exception as exc:
            raise BriefConfigurationError("tokenizer_unavailable") from exc
        if type(tokens) is not int or tokens < 0:
            raise BriefConfigurationError("invalid_token_count")
        return tokens

    def _validate_policy(self, policy: Mapping) -> None:
        if policy.get("budget_unit") != "tokens":
            raise BriefConfigurationError("budget_unit_must_be_tokens")
        if not policy.get("policy_version"):
            raise BriefConfigurationError("missing_policy_version")
        for name in ("tokenizer_id", "tokenizer_version", "model_id"):
            identity = getattr(self._counter, name, None)
            if not identity or policy.get(name) != identity:
                raise BriefConfigurationError(f"tokenizer_identity_mismatch:{name}")
        for name in ("mandatory_budget", "compressible_budget", "total_budget", "hard_cap"):
            value = policy.get(name)
            if type(value) is not int or value < 0:
                raise BriefConfigurationError(f"invalid_budget:{name}")
        if policy["total_budget"] != policy["mandatory_budget"] + policy["compressible_budget"]:
            raise BriefConfigurationError("total_budget_must_equal_mandatory_plus_compressible")
        if policy["hard_cap"] < policy["total_budget"]:
            raise BriefConfigurationError("hard_cap_below_total_budget")
        # Do not silently ignore capabilities that this phase cannot perform.
        for name in (
            "expansion_allowed",
            "reference_fallback_allowed",
            "full_report_fallback_allowed",
        ):
            if policy.get(name, False) is not False:
                raise BriefConfigurationError(f"unsupported_standalone_capability:{name}")

    def build(
        self,
        *,
        reports: Mapping[str, str],
        canonical_gaps: Sequence[str],
        metric_block: str,
        safety_constraints: Sequence[str],
        policy: Mapping,
        coverage_view_version: str,
        narrative: str | None = None,
    ) -> BriefResult:
        """Build without changing caller inputs; all limits include actual text.

        M is a reservation, not permission to truncate evidence exceeding M.
        Narrative must fit C AND the remaining initial total T; H is an
        additional independent ceiling. No expansion happens here. When a
        rendered narrative is supplied, validate it whole without truncation;
        otherwise use deterministic extraction. Empty narrative is useful for
        preflighting protected content before an optional model request.
        """
        self._validate_policy(policy)
        if set(reports) != set(_REPORT_ORDER) or any(
            not isinstance(report, str) for report in reports.values()
        ):
            raise BriefConfigurationError("expected_four_text_reports")
        if not isinstance(metric_block, str):
            raise BriefConfigurationError("metric_block_must_be_text")
        if not isinstance(coverage_view_version, str) or not coverage_view_version.strip():
            raise BriefConfigurationError("missing_coverage_view_version")
        for entries in (canonical_gaps, safety_constraints):
            if isinstance(entries, str) or any(not isinstance(entry, str) for entry in entries):
                raise BriefConfigurationError("mandatory_entries_must_be_text_sequences")

        # Preserve the metric block verbatim, including periods, sources and n/a
        # reasons. No keyword-based gap inference or financial recomputation.
        evidence = list(dict.fromkeys((*canonical_gaps, metric_block, *safety_constraints)))
        protected = "\n".join(
            ("[PROTECTED]", f"Coverage: {coverage_view_version}", *evidence, "[/PROTECTED]")
        )
        mandatory_tokens = self._count(protected)

        def reject(reason: str) -> BriefResult:
            return BriefResult(
                status="BRIEF_REJECTED",
                text=None,
                rejection_reason=reason,
                mandatory_tokens=mandatory_tokens,
                total_tokens=0,
                protected_content=protected,
                coverage_view_version=coverage_view_version,
            )

        if mandatory_tokens > policy["hard_cap"]:
            return reject("mandatory_exceeds_hard_cap")
        if mandatory_tokens > policy["total_budget"]:
            return reject("mandatory_exceeds_initial_budget")

        if narrative is not None:
            if not isinstance(narrative, str):
                raise BriefConfigurationError("narrative_must_be_text")
            text = protected + ("\n\n" + narrative if narrative else "")
            narrative_tokens = self._count(narrative)
            total_tokens = self._count(text)
            if narrative_tokens > policy["compressible_budget"]:
                return reject("narrative_exceeds_compressible_budget")
            if total_tokens > policy["hard_cap"]:
                return reject("delivered_exceeds_hard_cap")
            if total_tokens > policy["total_budget"]:
                return reject("delivered_exceeds_initial_budget")
            return BriefResult(
                status="BRIEF_OK",
                text=text,
                rejection_reason=None,
                mandatory_tokens=mandatory_tokens,
                total_tokens=total_tokens,
                narrative_tokens=narrative_tokens,
                protected_content=protected,
                coverage_view_version=coverage_view_version,
            )

        selected: list[str] = []
        seen: set[str] = set()

        def retain(candidate: str) -> bool:
            narrative = "\n".join((*selected, candidate))
            delivered = protected + "\n\n" + narrative
            if (
                self._count(narrative) <= policy["compressible_budget"]
                and self._count(delivered) <= policy["total_budget"]
                and self._count(delivered) <= policy["hard_cap"]
            ):
                selected.append(candidate)
                return True
            return False

        # Match complete standalone entries, not occurrences within sentences.
        # Longest blocks first: a multi-line metric block is removed only when
        # all of its lines match; a partial block remains ordinary report text.
        evidence_entries = sorted(
            {
                tuple(line.strip() for line in item.splitlines())
                for item in evidence
                if item.strip()
            },
            key=lambda entry: (-len(entry), entry),
        )
        # Local copies only; the original reports and protected evidence are
        # unchanged. Whitespace at line edges is ignored for standalone matching.
        paragraphs = []
        for source in _REPORT_ORDER:
            lines = [line.strip() for line in reports[source].splitlines()]
            parts = []
            index = 0
            while index < len(lines):
                matched = next(
                    (
                        entry
                        for entry in evidence_entries
                        if tuple(lines[index : index + len(entry)]) == entry
                    ),
                    None,
                )
                if matched is not None:
                    index += len(matched)
                else:
                    if lines[index]:
                        parts.append(lines[index])
                    index += 1
            paragraphs.append(parts)

        frequency = Counter(part for parts in paragraphs for part in parts)
        candidates = []
        for repeated in (False, True):
            groups = [
                list(dict.fromkeys(part for part in parts if (frequency[part] > 1) == repeated))
                for parts in paragraphs
            ]
            for index in range(max((len(group) for group in groups), default=0)):
                candidates.extend(group[index] for group in groups if index < len(group))

        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            if not retain(candidate):
                # Original complete sentences only; no generated paraphrases.
                sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", candidate)
                if len(sentences) > 1:
                    for sentence in sentences:
                        if sentence not in seen:
                            seen.add(sentence)
                            retain(sentence)

        narrative = "\n".join(selected)
        text = protected + ("\n\n" + narrative if narrative else "")
        return BriefResult(
            status="BRIEF_OK",
            text=text,
            rejection_reason=None,
            mandatory_tokens=mandatory_tokens,
            total_tokens=self._count(text),
            narrative_tokens=self._count(narrative),
            protected_content=protected,
            coverage_view_version=coverage_view_version,
        )
