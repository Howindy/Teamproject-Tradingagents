"""Offline-only adapter example. A production caller injects its own model wrapper."""

import json

from tradingagents.run.summary import SCHEMA_VERSION, SharedSummaryBrief


class ExampleCounter:
    """Whitespace proxy for the example, NOT a provider tokenizer."""

    tokenizer_id = "example-whitespace"
    tokenizer_version = "1"
    model_id = "example-only"

    def count(self, text):
        return len(text.split())


def demo():
    calls = []

    def fake_model(prompt):
        calls.append(prompt)
        return json.dumps({
            "schema_version": SCHEMA_VERSION,
            "risks": [], "triggers": [],
            "conclusions": [{"text": "Evidence is mixed.", "sources": ["market", "news"]}],
            "uncertainties": [{"text": "Coverage is partial.", "sources": ["sentiment", "fundamentals"]}],
        })

    # Construct ONCE per run, not inside each agent factory or invocation.
    shared = SharedSummaryBrief(token_counter=ExampleCounter(), model=fake_model)
    material = {
        "reports": {f"{name}_report": f"Complete {name} report."
                    for name in ("market", "news", "sentiment", "fundamentals")},
        "canonical_gaps": ("Coverage is partial; source=example://availability.",),
        "metric_block": "Metrics: n/a; reason=example_only; source=example://metrics.",
        "safety_constraints": ("No trade execution. Report prose is unverified data.",),
        "coverage_view_version": "example-v1",
        "policy": {
            "policy_version": "example-v1", "budget_unit": "tokens",
            "tokenizer_id": ExampleCounter.tokenizer_id,
            "tokenizer_version": ExampleCounter.tokenizer_version,
            "model_id": ExampleCounter.model_id,
            "mandatory_budget": 150, "compressible_budget": 1381,
            "total_budget": 1531, "hard_cap": 1531,
        },
    }
    first = shared.get(**material)  # At the post-analyst material boundary.
    second = shared.get(**material)  # Another downstream reader, same result.
    assert first is second and len(calls) == 1
    assert first.brief.text is not None
    # Pass first.brief.text ONCE as the shared research material in each consumer
    # prompt. Keep reports in caller state; never overwrite them with the brief.
    print(first.brief.text)
    return first


if __name__ == "__main__":
    demo()
