"""Compose the FR-08 assembler from configuration; one place to replace.

``fr08_enabled`` adds the shared-brief node. ``fr08_summary_enabled`` makes that
brief a single structured-summary call (with deterministic fallback); when off,
the same node still assembles the deterministic brief. Both off keeps the
original four-report prompts and the original graph.
"""

from tradingagents.run.assembler import DownstreamContextAssembler
from tradingagents.run.counter import WhitespaceTokenCounter


def _summary_model(llm):
    """Adapt a chat model to the one-string-in/one-string-out summary seam."""

    def call(prompt: str) -> str:
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        return content if isinstance(content, str) else ""

    return call


def build_context_assembler(config, *, metrics_factory=None, summary_llm=None, token_counter=None):
    config = config or {}
    if not config.get("fr08_enabled"):
        return None
    use_summary = bool(config.get("fr08_summary_enabled")) and summary_llm is not None
    budget = config.get("fr08_brief_budget") or 4000
    return DownstreamContextAssembler(
        token_counter=token_counter or WhitespaceTokenCounter(),
        coverage_view_version=config.get("fr08_coverage_view_version") or "fr08-downstream-v1",
        total_budget=int(budget),
        mandatory_budget=int(config.get("fr08_protected_budget") or 600),
        metrics_factory=metrics_factory,
        summary_model=_summary_model(summary_llm) if use_summary else None,
    ).node
