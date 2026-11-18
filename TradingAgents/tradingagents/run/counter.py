"""Deterministic whitespace proxy counter for FR-08 budget accounting.

This is not a provider tokenizer. It measures the delivered text the same way on
every run so an offline test and a live run agree on the budget boundary; callers
that have a real tokenizer inject their own counter instead.
"""


class WhitespaceTokenCounter:
    tokenizer_id = "fr08-whitespace-proxy"
    tokenizer_version = "1"
    model_id = "fr08-whitespace-proxy"

    def count(self, text: str) -> int:
        return len(text.split())
