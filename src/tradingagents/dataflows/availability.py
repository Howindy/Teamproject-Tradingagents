"""Run-scoped data-availability tracking for FR-03 (C-07 / C-20).

This module is the single producer of the five-field ``AvailabilitySummary`` and
the finite per-method classifier. It owns, for one analysis (under a
``run_context.RunContext``):

* ``DataResultClassifier`` (C-20): a narrow, per-method classifier that maps a
  verified producer outcome (string or exception) to one of the four statuses
  ``available`` / ``no_data`` / ``unavailable`` / ``withheld``, a short safe
  reason, and a source when (and only when) reliably known.
* ``AvailabilityRegistry`` (C-07): accepted-update ordering, first-eligible
  target binding (before fetch, under one lock released before I/O), query-level
  failure marks, private pre-fetch call-failure notes and the private sticky
  ``availability_tracking_error``.
* ``AvailabilitySummarizer`` (IF-06): builds the five-field mapping once, matching
  the seven necessary items to their bound targets, applying marks, computing
  completeness once, and disclosing supplementary failures separately.

Design constraints from D2 §8.3 honoured here:

* A non-empty string is never sufficient for ``available``; an unrecognized
  format is ``unavailable`` with reason ``unrecognized result format``.
* Source is never inferred from the configured vendor chain; it is taken only
  from a ``source_hint`` a direct producer supplies.
* Bindings allocate no completion sequence and hold no lock across fetch.
* Observation handling never replaces the original fetch value/exception and
  never refetches.
* ``availability_tracking_error`` (sticky) makes later snapshots ``None``; a
  one-off snapshot construction failure returns ``None`` for that call only.
* No formal decision, no FR-01 reuse, no persistence, no new public status.
"""

from __future__ import annotations

import json
import logging
import threading

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Statuses and fixed texts                                                     #
# --------------------------------------------------------------------------- #
AVAILABLE = "available"
NO_DATA = "no_data"
UNAVAILABLE = "unavailable"
WITHHELD = "withheld"
STATUSES = (AVAILABLE, NO_DATA, UNAVAILABLE, WITHHELD)

NOT_ATTEMPTED = "not_attempted"

# Fixed, deterministic stage texts (D2: these are two DIFFERENT strings).
UNAVAILABLE_RESEARCH_TEXT = "program summary currently unavailable"
UNAVAILABLE_REPORT_TEXT = "program summary unavailable"

# Safe, bounded reasons (never raw vendor/exception text).
REASON_UNRECOGNIZED = "unrecognized result format"
REASON_MARKED = "availability record failed; cannot confirm"
REASON_CLASSIFIER_FAILED = "availability classification failed"
REASON_NO_COMPLETED = "no completed result available"
REASON_PARAM_REJECTED = (
    "no completed result available; related request was rejected during parameter handling"
)

# The seven necessity items: enabled analyst -> the items it makes necessary.
_ANALYST_ITEMS = {
    "market": ("get_stock_data", "get_verified_market_snapshot"),
    "fundamentals": ("get_income_statement", "get_balance_sheet", "get_cashflow"),
    "news": ("get_global_news",),
    "social": ("fetch_reddit_posts",),
}

# How a necessity item matches an observation/params: which params identify the
# bound target for the current object/range. Snapshots exclude look_back_days
# from necessity matching (utility lookback is not a necessity dimension).
_TARGET_KEYS = {
    "get_stock_data": ("symbol", "start_date", "end_date"),
    "get_verified_market_snapshot": ("symbol", "as_of"),
    "get_income_statement": ("ticker", "freq", "as_of"),
    "get_balance_sheet": ("ticker", "freq", "as_of"),
    "get_cashflow": ("ticker", "freq", "as_of"),
    "get_global_news": ("as_of", "look_back_days", "limit"),
    "fetch_reddit_posts": ("ticker", "subreddits", "start_date", "end_date", "limit_per_sub"),
}

_SUPPLEMENTARY_METHODS = {
    "get_indicators", "get_fundamentals", "get_insider_transactions", "get_news",
    "get_macro_indicators", "get_prediction_markets", "fetch_stocktwits_messages",
}

# The parameter key that carries the run's current object for a necessity item's
# method (None for global news, which has no ticker object). Used to judge whether
# a request's object matches the run's analysis object before binding a target.
_OBJECT_KEY = {
    "get_stock_data": "symbol",
    "get_verified_market_snapshot": "symbol",
    "get_income_statement": "ticker",
    "get_balance_sheet": "ticker",
    "get_cashflow": "ticker",
    "get_global_news": None,
    "fetch_reddit_posts": "ticker",
}


# --------------------------------------------------------------------------- #
# Classification (C-20)                                                        #
# --------------------------------------------------------------------------- #
class DataObservation:
    """One classified producer outcome (status/reason/source), not a registry record."""

    __slots__ = ("method", "status", "reason", "source", "effective_parameters")

    def __init__(self, method, status, reason, source, effective_parameters):
        self.method = method
        self.status = status
        self.reason = reason
        self.source = source
        self.effective_parameters = _copy_params(effective_parameters)

    def copy(self):
        return DataObservation(self.method, self.status, self.reason, self.source,
                               self.effective_parameters)

    def __repr__(self):  # pragma: no cover - debug aid
        return (f"DataObservation(method={self.method!r}, status={self.status!r}, "
                f"reason={self.reason!r}, source={self.source!r})")


def _copy_observation(observation):
    """An independent copy of a ``DataObservation`` (own parameter dict)."""
    if isinstance(observation, DataObservation):
        return observation.copy()
    # A foreign observation-like object: rebuild a plain copy from its fields.
    return DataObservation(
        getattr(observation, "method", None),
        getattr(observation, "status", None),
        getattr(observation, "reason", None),
        getattr(observation, "source", None),
        getattr(observation, "effective_parameters", None),
    )


class ClassificationFailure(Exception):
    """An internal classifier error (not a data-source status). IF-23."""


def _as_text(raw):
    if isinstance(raw, str):
        return raw
    return None


# Recognised Alpha Vantage OVERVIEW keys that carry basic company information.
# A populated value for one of these is the producer's real "overview present"
# signal; an arbitrary/unknown key is not.
_AV_OVERVIEW_FIELDS = frozenset({
    "AssetType", "Name", "Description", "Exchange", "Currency", "Country",
    "Sector", "Industry", "Address", "OfficialSite", "FiscalYearEnd",
    "LatestQuarter", "MarketCapitalization", "EBITDA", "PERatio",
    "PEGRatio", "BookValue", "DividendPerShare", "DividendYield", "EPS",
    "RevenuePerShareTTM", "ProfitMargin", "OperatingMarginTTM",
    "ReturnOnAssetsTTM", "ReturnOnEquityTTM", "RevenueTTM",
    "GrossProfitTTM", "DilutedEpsTTM", "QuarterlyEarningsGrowthYOY",
    "QuarterlyRevenueGrowthYOY", "AnalystTargetPrice", "TrailingPE",
    "ForwardPE", "PriceToSalesRatioTTM", "PriceToBookRatio",
    "EVToRevenue", "EVToEBITDA", "Beta", "52WeekHigh", "52WeekLow",
    "50DayMovingAverage", "200DayMovingAverage", "SharesOutstanding",
    "DividendDate", "ExDividendDate",
})

# A populated value that is not one of these placeholders counts as data.
_AV_EMPTY_VALUES = frozenset({"", "None", "-", "null", "N/A", "NaN"})


def _av_populated(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in _AV_EMPTY_VALUES
    # Numbers/containers are populated if present.
    return True


def _csv_lines(text: str):
    """The CSV rows of a body: non-blank lines with any leading ``#``-comment
    header block (e.g. the yahoo ``# Stock data ...`` prelude) removed."""
    lines = []
    seen_data_section = False
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            if seen_data_section:
                continue
            continue
        if s.startswith("#"):
            continue
        seen_data_section = True
        lines.append(s)
    return lines


def _is_data_row(row: str) -> bool:
    """A CSV row is an actual producer data row when it has at least two
    comma-separated fields AND a dated field (the price and statement producers
    always put the date/timestamp first). A lone number, a lone date, or a prose
    line with a stray number is NOT a data row."""
    import re

    if "," not in row:
        return False
    fields = [f.strip().strip('"') for f in row.split(",")]
    if len([f for f in fields if f]) < 2:
        return False
    return any(re.match(r"^\d{4}-\d{2}-\d{2}", f) for f in fields if f)


def _csv_has_rows(text: str) -> bool:
    """True when a CSV body has at least one actual data row.

    The first CSV line may be a header; a body counts only if some line is a real
    data row (a date or a number field), which also covers single-line bodies
    emitted without a header.
    """
    lines = _csv_lines(text)
    return any(_is_data_row(ln) for ln in lines)


def _looks_like_header_row(row: str) -> bool:
    """A CSV header row: at least one alphabetic field and no date/number field."""
    fields = [f.strip().strip('"') for f in row.split(",")]
    if not any(f for f in fields):
        return True  # all-empty field row is not a data row
    return not _is_data_row(row)


def _header_only_csv(text: str) -> bool:
    """A CSV body that has a comma-bearing line but no actual data row (a header
    line alone, possibly after a ``#``-comment prelude). A single line that is
    already a data row is NOT header-only."""
    lines = _csv_lines(text)
    if not lines:
        return False
    if not any("," in ln for ln in lines):
        return False
    return not any(_is_data_row(ln) for ln in lines)


def _json_obj(text: str):
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def _snapshot_has_finite_close(text: str) -> bool:
    """A verified snapshot's verified price record requires a PARSEABLE dated row
    (``- Latest trading row used: YYYY-MM-DD``) AND a finite ``| Close |`` value
    (the producer's OHLCV row). A snapshot missing either is not available."""
    import math
    import re

    dated = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- Latest trading row used:"):
            value = s.split(":", 1)[1].strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}", value):
                dated = True
            break
    if not dated:
        return False

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("| Close |"):
            continue
        parts = [p.strip() for p in s.strip("|").split("|")]
        if len(parts) < 2:
            continue
        value = parts[1]
        if value in ("N/A", "") or value.upper() == "NAN":
            return False
        try:
            number = float(value)
        except ValueError:
            return False
        return math.isfinite(number)
    return False


def _indicator_has_numeric_value(text: str) -> bool:
    """At least one dated numeric value line: ``YYYY-MM-DD: <number>``."""
    import re

    for line in text.splitlines():
        m = re.match(r"^\s*\d{4}-\d{2}-\d{2}:\s*(.+?)\s*$", line)
        if not m:
            continue
        value = m.group(1).strip()
        if value.upper().startswith("N/A"):
            continue
        try:
            float(value.replace("%", "").replace(",", ""))
            return True
        except ValueError:
            continue
    return False


def _has_news_entry(text: str) -> bool:
    """At least one real article entry: a ``### <title> (source: <publisher>)``
    heading with a non-empty title, or an AV feed entry rendered with a ``###``
    heading. A bare ``###`` heading with no title is not an article."""
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("### "):
            continue
        title = s[4:].strip()
        head = title.split("(source:", 1)[0].strip()
        if head:
            return True
    return False


_YAHOO_FUNDAMENTAL_LABELS = frozenset({
    "Name", "Sector", "Industry", "Market Cap", "PE Ratio (TTM)", "Forward PE",
    "PEG Ratio", "Price to Book", "EPS (TTM)", "Forward EPS", "Dividend Yield",
    "Beta", "52 Week High", "52 Week Low", "50 Day Average", "200 Day Average",
    "Revenue (TTM)", "Gross Profit", "EBITDA", "Net Income", "Profit Margin",
    "Operating Margin", "Return on Equity", "Return on Assets", "Debt to Equity",
    "Current Ratio", "Book Value", "Free Cash Flow",
})


def _fundamentals_has_field(text: str) -> bool:
    """At least one RECOGNISED ``label: value`` field beyond the header/placeholder.

    The yahoo producer emits a fixed label set; an arbitrary ``unknown: value``
    line under the ``# Company Fundamentals`` header is not a real field."""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            continue
        label, _, value = s.partition(":")
        label = label.strip()
        if label in _YAHOO_FUNDAMENTAL_LABELS and value.strip() and \
                value.strip().upper() not in ("N/A", "NONE", "NAN", "NULL", "-"):
            return True
    return False


class DataResultClassifier:
    """IF-23: narrow, per-method classification of a verified producer outcome."""

    @staticmethod
    def classify(method, effective_params, raw_result_or_exception, source_hint=None):
        try:
            return _classify(method, effective_params, raw_result_or_exception, source_hint)
        except Exception as exc:  # noqa: BLE001 - becomes ClassificationFailure
            raise ClassificationFailure(str(exc)) from exc


def _classify(method, params, raw, source_hint):
    # A propagated exception always means the call could not be served.
    if isinstance(raw, BaseException):
        return DataObservation(method, UNAVAILABLE, "vendor error", source_hint, params)

    text = _as_text(raw)
    if text is None:
        # Non-string, non-exception: unrecognized.
        return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)

    stripped = text.strip()
    upper = stripped.upper()
    if not stripped:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)

    # Router/tool fixed sentinels take precedence over body heuristics.
    if upper.startswith("DATA_UNAVAILABLE"):
        return DataObservation(method, UNAVAILABLE, "vendor unavailable", source_hint, params)
    if upper.startswith("NO_DATA_AVAILABLE"):
        return DataObservation(method, NO_DATA, "no usable data", source_hint, params)

    handler = _CLASSIFIERS.get(method, _classify_generic)
    return handler(method, params, stripped, source_hint)


def _classify_generic(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _classify_stock_data(method, params, text, source_hint):
    """P-01: available only for a real data row; header-only is no_data; a
    malformed body or a date-validation message is unavailable."""
    low = text.lower()
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    if _csv_has_rows(text):
        return DataObservation(method, AVAILABLE, "price rows present", source_hint, params)
    if _header_only_csv(text):
        return DataObservation(method, NO_DATA, "no data rows", source_hint, params)
    if (low.startswith("error") or "not be parsed" in low or "unparseable" in low
            or "not a date" in low or ("invalid" in low and "date" in low)):
        return DataObservation(method, UNAVAILABLE, "malformed price data", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _classify_snapshot(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty snapshot", source_hint, params)
    if "## Verified market data snapshot" in text:
        if _snapshot_has_finite_close(text):
            return DataObservation(method, AVAILABLE, "verified price row present", source_hint, params)
        return DataObservation(method, NO_DATA, "no finite price row", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _classify_indicator(method, params, text, source_hint):
    low = text.lower()
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    if "values from" in low:
        if _indicator_has_numeric_value(text):
            return DataObservation(method, AVAILABLE, "indicator values present", source_hint, params)
        return DataObservation(method, NO_DATA, "no numeric values", source_hint, params)
    if ("no data available for the specified date range" in low
            or "no data returned" in low):
        return DataObservation(method, NO_DATA, "no data in range", source_hint, params)
    if low.startswith("error:") or "not found" in low:
        return DataObservation(method, UNAVAILABLE, "indicator error", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _classify_fundamentals(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    # A historical withholding notice is the producer's own branch (before the JSON).
    if _is_withheld_profile(text):
        return DataObservation(method, WITHHELD, "withheld for this date", source_hint, params)
    obj = _json_obj(text)
    if obj is not None:                      # Alpha Vantage OVERVIEW JSON
        if not obj:
            return DataObservation(method, NO_DATA, "empty overview", source_hint, params)
        populated = [k for k, v in obj.items()
                     if k in _AV_OVERVIEW_FIELDS and _av_populated(v)]
        if populated:
            return DataObservation(method, AVAILABLE, "overview fields present", source_hint, params)
        return DataObservation(method, NO_DATA, "no populated overview fields", source_hint, params)
    if text.startswith("# Company Fundamentals"):
        if _fundamentals_has_field(text):
            return DataObservation(method, AVAILABLE, "fundamental fields present", source_hint, params)
        return DataObservation(method, NO_DATA, "no fundamental fields", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _is_withheld_profile(text):
    low = text.lower()
    return "profile fundamentals are withheld for this date" in low


def _is_withheld_statement(text):
    low = text.lower()
    return "data is withheld for this date" in low


def _is_withheld_insider(text):
    low = text.lower()
    return "insider transactions are withheld for this date" in low


def _is_withheld_prediction(text):
    low = text.lower()
    return "odds are withheld" in low


def _classify_statement(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    if _is_withheld_statement(text):
        return DataObservation(method, WITHHELD, "withheld for this date", source_hint, params)
    obj = _json_obj(text)
    if obj is not None:                      # Alpha Vantage statement JSON
        annual = obj.get("annualReports")
        quarterly = obj.get("quarterlyReports")
        # A wrong-type array (e.g. a placeholder string) is not a successful body.
        if annual is not None and not isinstance(annual, list):
            return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)
        if quarterly is not None and not isinstance(quarterly, list):
            return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)
        if any(isinstance(r, dict) for r in (annual or [])) or \
                any(isinstance(r, dict) for r in (quarterly or [])):
            return DataObservation(method, AVAILABLE, "report rows present", source_hint, params)
        return DataObservation(method, NO_DATA, "empty statement arrays", source_hint, params)
    if _header_only_csv(text):
        return DataObservation(method, NO_DATA, "no data rows", source_hint, params)
    if _csv_has_rows(text):
        return DataObservation(method, AVAILABLE, "statement rows present", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _classify_insider(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    if _is_withheld_insider(text):
        return DataObservation(method, WITHHELD, "withheld for this date", source_hint, params)
    obj = _json_obj(text)
    if obj is not None:
        data = obj.get("data")
        if data is not None and not isinstance(data, list):
            return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)
        if any(isinstance(r, dict) for r in (data or [])):
            return DataObservation(method, AVAILABLE, "insider rows present", source_hint, params)
        return DataObservation(method, NO_DATA, "empty insider array", source_hint, params)
    low = text.lower()
    if "no insider transactions reported" in low:
        return DataObservation(method, NO_DATA, "no insider transactions", source_hint, params)
    if text.startswith("# Insider Transactions"):
        if _header_only_csv(text):
            return DataObservation(method, NO_DATA, "no data rows", source_hint, params)
        if _csv_has_rows(text):
            return DataObservation(method, AVAILABLE, "insider rows present", source_hint, params)
        return DataObservation(method, NO_DATA, "no insider rows", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _classify_news(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    low = text.lower()
    # Real article entries take precedence: body words like "unavailable" or
    # "coverage" inside a real article must not flip it to unavailable.
    if _has_news_entry(text):
        return DataObservation(method, AVAILABLE, "article entries present", source_hint, params)
    obj = _json_obj(text)                     # Alpha Vantage NEWS_SENTIMENT JSON
    if obj is not None:
        feed = obj.get("feed")
        if feed is not None and not isinstance(feed, list):
            return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)
        if any(isinstance(a, dict) for a in (feed or [])):
            return DataObservation(method, AVAILABLE, "news feed present", source_hint, params)
        return DataObservation(method, NO_DATA, "empty news feed", source_hint, params)
    if ("no news found" in low or "no global news found" in low):
        return DataObservation(method, NO_DATA, "no news found", source_hint, params)
    if ("unavailable" in low or "coverage" in low
            or "only a sample of recent articles" in low):
        return DataObservation(method, UNAVAILABLE, "news unavailable", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _fred_has_observation(text):
    """An observation row ``| <date> | <value> |`` or a ``**Latest:**`` line with
    a value (the producer's real data presence, not just a table header)."""
    import re

    low = text.lower()
    if "**latest:**" in low:
        m = re.search(r"\*\*latest:\*\*\s*([^\s|]+)", low)
        if m and m.group(1) not in ("", "none", "n/a", "."):
            return True
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        fields = [f.strip() for f in s.strip("|").split("|")]
        if len(fields) != 2:
            continue
        d, v = fields
        if re.match(r"^\d{4}-\d{2}-\d{2}", d) and v and v not in ("Value", "---", "—"):
            return True
    return False


def _classify_macro(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    low = text.lower()
    if "not found" in low and low.startswith("fred"):
        return DataObservation(method, NO_DATA, "series not found", source_hint, params)
    if low.startswith("fred:"):
        return DataObservation(method, UNAVAILABLE, "invalid indicator", source_hint, params)
    if "no observations for" in low:
        return DataObservation(method, NO_DATA, "no observations", source_hint, params)
    if text.startswith("## FRED:") or "**latest:**" in low:
        if _fred_has_observation(text):
            return DataObservation(method, AVAILABLE, "observations present", source_hint, params)
        return DataObservation(method, NO_DATA, "no observations", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _prediction_has_market_line(text):
    """At least one real market line: ``- **<question>** — <label> <pct>% ...``."""
    import re

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        if "**" in s and re.search(r"\d+(?:\.\d+)?%", s):
            return True
    return False


def _classify_prediction(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    low = text.lower()
    if _is_withheld_prediction(text):
        return DataObservation(method, WITHHELD, "withheld for this date", source_hint, params)
    if "no open prediction markets" in low:
        return DataObservation(method, NO_DATA, "no matching markets", source_hint, params)
    if "currently unavailable" in low:
        return DataObservation(method, UNAVAILABLE, "prediction source unavailable", source_hint, params)
    # A real header requires at least one market line, not just a percent anywhere.
    if "prediction markets:" in low and _prediction_has_market_line(text):
        return DataObservation(method, AVAILABLE, "market lines present", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _stocktwits_has_message_line(text):
    """A real message line: ``[<created> · @<user> · <tag>] <body>``."""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and " · @" in s and "]" in s:
            return True
    return False


def _classify_stocktwits(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    low = text.lower()
    if "stocktwits unavailable" in low or "stocktwits unavailable for" in low:
        return DataObservation(method, UNAVAILABLE, "stocktwits unavailable", source_hint, params)
    if "none of the" in low and "is about" in low:
        return DataObservation(method, NO_DATA, "all messages off-topic", source_hint, params)
    if "no stocktwits messages" in low:
        return DataObservation(method, NO_DATA, "no messages", source_hint, params)
    # A normal block has at least one real message line (a summary alone is not enough).
    if _stocktwits_has_message_line(text):
        return DataObservation(method, AVAILABLE, "messages present", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


def _reddit_has_post_line(text):
    """At least one sub-block with a post line ``  [YYYY-MM-DD] <title>``."""
    import re

    for line in text.splitlines():
        s = line.rstrip()
        if s.lstrip().startswith("["):
            m = re.match(r"^\s*\[\d{4}-\d{2}-\d{2}\]", s)
            if m:
                return True
    return False


def _classify_reddit(method, params, text, source_hint):
    if not text:
        return DataObservation(method, NO_DATA, "empty result", source_hint, params)
    low = text.lower()
    if "reddit unavailable" in low:
        return DataObservation(method, UNAVAILABLE, "reddit unavailable", source_hint, params)
    if _reddit_has_post_line(text):
        return DataObservation(method, AVAILABLE, "posts present", source_hint, params)
    if ("no reddit posts" in low or "no posts" in low or "not among the newest" in low
            or "after screening" in low):
        return DataObservation(method, NO_DATA, "no posts", source_hint, params)
    return DataObservation(method, UNAVAILABLE, REASON_UNRECOGNIZED, source_hint, params)


_CLASSIFIERS = {
    "get_stock_data": _classify_stock_data,
    "get_verified_market_snapshot": _classify_snapshot,
    "get_indicators": _classify_indicator,
    "get_fundamentals": _classify_fundamentals,
    "get_income_statement": _classify_statement,
    "get_balance_sheet": _classify_statement,
    "get_cashflow": _classify_statement,
    "get_insider_transactions": _classify_insider,
    "get_news": _classify_news,
    "get_global_news": _classify_news,
    "get_macro_indicators": _classify_macro,
    "get_prediction_markets": _classify_prediction,
    "fetch_stocktwits_messages": _classify_stocktwits,
    "fetch_reddit_posts": _classify_reddit,
}


# --------------------------------------------------------------------------- #
# Query identity                                                               #
# --------------------------------------------------------------------------- #
def _normalize_value(value):
    if isinstance(value, (list, tuple)):
        return tuple(_normalize_value(v) for v in value)
    return value


def _copy_params(params):
    """An independent, normalized copy of a params mapping.

    Lists/arrays are normalized to tuples (so an equivalent list/tuple is the same
    logical query and the stored value cannot be mutated through a caller's list)
    and nested containers are copied. Plain data only; no framework."""
    if not params:
        return {}
    return {k: _normalize_value(v) for k, v in params.items()}


def _query_key(method, params):
    """Logical query identity: method + effective business parameters (no path)."""
    params = params or {}
    items = tuple(sorted((k, _normalize_value(v)) for k, v in params.items()
                         if v is not None))
    return (method, items)


# --------------------------------------------------------------------------- #
# Registry (C-07)                                                              #
# --------------------------------------------------------------------------- #
class _CompletedRecord:
    __slots__ = ("key", "observation", "sequence")

    def __init__(self, key, observation, sequence):
        self.key = key
        self.observation = observation
        self.sequence = sequence


class AvailabilityRegistry:
    """Per-run availability state: targets, accepted updates, marks, notes.

    ``analysis_context`` is the run's existing analysis identity (ticker/date/range).
    It is used only to judge whether a request is eligible to bind one of the seven
    necessity targets (current object / analysis date). It adds no new input,
    product schema or configuration; when omitted the registry cannot judge object
    eligibility and binds the first request (the identity-free unit surface).
    """

    def __init__(self, analysis_context=None):
        self._lock = threading.Lock()
        self._analysis_context = dict(analysis_context) if analysis_context else None
        self._targets = {}            # method -> params of the first eligible request
        self._records = {}            # query_key -> _CompletedRecord (last accepted)
        self._marks = {}              # query_key -> reason (latest update)
        self._sequences = {}          # query_key -> last accepted sequence
        self._order = 0
        self._path_assoc = {}         # query_key -> set of path ids
        self._executing_path = {}     # query_key -> first executing path id
        self.call_failures = []       # private pre-fetch rejection notes
        self.tracking_error = None    # private sticky reason or None

    # -- eligibility ------------------------------------------------------- #
    def _eligible_for_target(self, method, params):
        """Whether ``params`` may bind ``method``'s necessity target in this run.

        Eligibility follows the D2 §8.3 existing sources: the request must carry the
        run's current object (ticker/symbol) under the method's object key; global
        news (no ticker object) must carry the analysis date. A request missing the
        object identity, or for a different object/date, does not bind. With no
        analysis identity the registry cannot judge and accepts the first request.
        """
        params = params or {}
        ctx = self._analysis_context
        if ctx is None:
            return True
        object_key = _OBJECT_KEY.get(method)
        if object_key is not None:
            ticker = ctx.get("ticker")
            if ticker is None:
                return True
            return params.get(object_key) == ticker
        if method == "get_global_news":
            trade_date = ctx.get("trade_date")
            if trade_date is None:
                return True
            return params.get("as_of") == trade_date
        return True

    # -- target binding ---------------------------------------------------- #
    def request(self, method, params, path_id=None):
        """Bind the first eligible target for ``method`` (no sequence, no lock over I/O)."""
        with self._lock:
            if (method in _TARGET_KEYS and method not in self._targets
                    and self._eligible_for_target(method, params)):
                self._targets[method] = _copy_params(params)
            key = _query_key(method, params)
            if path_id is not None:
                self._path_assoc.setdefault(key, set()).add(path_id)
                self._executing_path.setdefault(key, path_id)

    def target_for(self, method):
        with self._lock:
            target = self._targets.get(method)
            return _copy_params(target) if target is not None else None

    def associate_path(self, method, params, path_id):
        key = _query_key(method, params)
        with self._lock:
            self._path_assoc.setdefault(key, set()).add(path_id)
            self._executing_path.setdefault(key, path_id)

    # -- accepting completed observations ---------------------------------- #
    def _next_sequence(self):
        self._order += 1
        return self._order

    def accept(self, observation, params=None):
        """Accept a completed observation under the lock; later update wins.

        The registry keeps its OWN copy of the observation's effective parameters
        and status fields so a caller mutating its params or classification result
        afterwards cannot change what the registry later reports.
        """
        params = observation.effective_parameters if params is None else params
        key = _query_key(observation.method, params)
        stored = _copy_observation(observation)
        with self._lock:
            seq = self._next_sequence()
            self._records[key] = _CompletedRecord(key, stored, seq)
            self._sequences[key] = seq
            # A later accepted result replaces a same-query mark.
            self._marks.pop(key, None)

    def accept_mark(self, method, params, reason):
        """Record/refresh a same-query failure mark as the latest update."""
        key = _query_key(method, params)
        with self._lock:
            seq = self._next_sequence()
            self._marks[key] = reason
            self._sequences[key] = seq

    def observe(self, observation, params=None):
        """Convenience: request-bind then accept in one step."""
        self.request(observation.method, params if params is not None else
                     observation.effective_parameters)
        self.accept(observation, params)

    def set_tracking_error(self, reason):
        """Set the private sticky tracking error on this (real) registry."""
        self.tracking_error = reason

    # -- introspection (internal) ------------------------------------------ #
    def completed_updates(self):
        with self._lock:
            return list(self._sequences.values())

    def snapshot_state(self):
        """A consistent copy of accepted records, marks, targets, notes, error.

        All reads happen under one lock acquisition so the sticky ``tracking_error``
        and the records/bindings reflect the SAME instant. Stored observations and
        parameter dicts are copied so the returned summary never aliases mutable
        registry state."""
        with self._lock:
            records = {k: (r.observation.copy(), r.sequence)
                       for k, r in self._records.items()}
            marks = {k: (reason, self._sequences.get(k)) for k, reason in self._marks.items()}
            return {
                "records": records,
                "marks": marks,
                "targets": {k: _copy_params(v) for k, v in self._targets.items()},
                "path_assoc": {k: set(v) for k, v in self._path_assoc.items()},
                "executing_path": dict(self._executing_path),
                "call_failures": [dict(n) for n in self.call_failures],
                "tracking_error": self.tracking_error,
            }


# --------------------------------------------------------------------------- #
# Local observation helper / failure marks / notes (IF-05)                     #
# --------------------------------------------------------------------------- #
def observe_call(registry, method, params, body, classifier=DataResultClassifier.classify):
    """Run ``body`` once and attempt one isolated observation; never alter the result.

    With no active registry the body runs directly. The original return value or
    exception is always preserved. A classifier exception becomes a conservative
    per-query ``unavailable`` observation; a failed acceptance becomes a query
    failure mark; if neither can be recorded, the sticky tracking error is set.
    """
    if registry is None:
        return body()

    fetch_failed = False
    try:
        raw = body()
    except BaseException as exc:   # noqa: BLE001 - preserve and re-raise
        raw = exc
        fetch_failed = True

    _handle_observation(registry, method, params, raw, classifier)

    if fetch_failed:
        raise raw
    return raw


def observe_supported_call(registry, method, params, path_id, body,
                           source_hint=None,
                           classifier=DataResultClassifier.classify):
    """Observation helper for a supported call path (P-01..P-15).

    With no active registry the body runs directly and nothing is recorded. With a
    registry it: (1) binds an eligible necessity target and associates the path
    BEFORE the fetch (no lock held across fetch, no sequence allocated for a bind);
    (2) executes the existing body ONCE with its existing arguments; (3) classifies
    the final value/exception and accepts one observation (or the mark/sticky chain
    on handling failure); (4) returns the original value or re-raises the original
    exception. It never refetches, retries, or calls a model.

    The pre-fetch binding is inside its own guard: a binding failure must NEVER
    block the original fetch or replace its result. Since the target/path could not
    be reliably recorded, the approved conservative handling is the run-local sticky
    tracking failure; the body still runs exactly once and its result/exception is
    preserved unchanged.
    """
    if registry is None:
        return body()

    try:
        registry.request(method, params, path_id)
    except Exception as exc:  # noqa: BLE001 - must not block the original fetch
        # Cannot reliably establish the necessary target/path tracking for this run;
        # take the run-local conservative tracking failure. Do not retry or alter
        # the fetch result. Never claim the summary is complete afterwards.
        logger.warning("availability request/binding failed: %s", exc)
        import contextlib

        with contextlib.suppress(Exception):  # best effort, still run the body
            set_tracking_error(registry, "availability target binding could not be recorded")

    fetch_failed = False
    try:
        raw = body()
    except BaseException as exc:   # noqa: BLE001 - preserve and re-raise
        raw = exc
        fetch_failed = True

    _handle_observation(registry, method, params, raw, classifier, source_hint)

    if fetch_failed:
        raise raw
    return raw


def _handle_observation(registry, method, params, raw, classifier, source_hint=None):
    try:
        observation = classifier(method, params, raw, source_hint)
    except Exception:  # noqa: BLE001 - classifier failure
        # Known-query conservative unavailable observation, then the SAME degrade
        # chain as a normal acceptance failure: mark, else sticky. Keep a reliably
        # known source on the conservative observation; null when unconfirmed.
        if method is not None and params is not None:
            try:
                conservative = DataObservation(
                    method, UNAVAILABLE, REASON_CLASSIFIER_FAILED, source_hint, params)
            except Exception:  # noqa: BLE001 - cannot build
                conservative = None
            if conservative is not None:
                _accept_or_mark(registry, conservative, method, params)
                return
        set_tracking_error(registry, "availability observation could not be recorded")
        return

    _accept_or_mark(registry, observation, method, params)


def _accept_or_mark(registry, observation, method, params):
    """Accept a completed observation; on acceptance failure try the single
    same-query mark interface, and only if that also fails set the sticky error.

    The normal observation and the conservative unavailable observation use this
    one chain (no divergent fallback paths)."""
    try:
        registry.accept(observation, params)
    except Exception:  # noqa: BLE001 - acceptance failure
        try:
            record_failure_mark(registry, method, params, REASON_MARKED)
        except Exception:  # noqa: BLE001 - cannot store mark
            set_tracking_error(registry, "availability record could not be stored")


def record_failure_mark(registry, method, params, reason):
    """Record a same-query failure mark as the latest accepted update.

    The single minimal internal mark interface is ``registry.accept_mark``. A
    wrapper may override it to simulate an unrecordable mark (which surfaces as an
    exception the caller turns into the sticky error). There is no multi-path
    dispatch to guess.
    """
    registry.accept_mark(method, params, reason)


def set_tracking_error(registry, reason):
    """Set the private sticky tracking error; later snapshots return ``None``.

    Uses the registry's ``set_tracking_error`` method when present so a proxy/wrapper
    forwards the write to the real registry; else sets the attribute directly."""
    setter = getattr(registry, "set_tracking_error", None)
    if callable(setter):
        setter(reason)
    else:
        registry.tracking_error = reason


def _record_prefetch_note(registry, method, params, reason):
    note = {
        "method": method,
        "object": (params or {}).get("symbol") or (params or {}).get("ticker"),
        "category": "parameter_rejection",
        "reason": reason,
    }
    registry.call_failures.append(note)


def observe_prefetch_rejection(registry, method, params, body, reason=REASON_PARAM_REJECTED):
    """Run a body that raises a pre-fetch parameter/date rejection.

    Records only a private call-failure note (no query/target/sequence/mark/sticky)
    and re-raises the original error. If the note cannot be written, it warns only.
    """
    try:
        body()
    except BaseException:
        _write_prefetch_note(registry, method, params, reason)   # warning-only
        raise


def record_prefetch_rejection(registry, method, params, reason=REASON_PARAM_REJECTED):
    """Record a private pre-fetch call-failure note for an ALREADY-handled rejection.

    Unlike ``observe_prefetch_rejection`` this neither runs a body nor raises: a tool
    that translates the date/parameter error to text (its original behaviour) calls
    this so its original text return is preserved with an active scope. With no
    registry it does nothing. The note contains no query/target/sequence/mark/sticky;
    a note-write failure warns only and never changes the tool's return value.
    """
    if registry is None:
        return
    _write_prefetch_note(registry, method, params, reason)


def _write_prefetch_note(registry, method, params, reason):
    try:
        recorder = getattr(registry, "note_call_failure", None)
        if recorder is not None:
            recorder(method, params, reason)
        else:
            _record_prefetch_note(registry, method, params, reason)
    except Exception as exc:  # noqa: BLE001 - warning only
        logger.warning("availability pre-fetch note could not be written: %s", exc)


# --------------------------------------------------------------------------- #
# Summarizer (IF-06)                                                           #
# --------------------------------------------------------------------------- #
def _analyst_required_items(enabled_analysts):
    items = []
    for analyst in enabled_analysts or ():
        for item in _ANALYST_ITEMS.get(analyst, ()):
            if item not in items:
                items.append(item)
    return items


def _target_params_for(item, snapshot, analysis_context):
    """The params identifying the necessity target for ``item`` in this run.

    Most items bind their target to the first eligible request's effective params
    (recorded by ``request``). The verified snapshot is special: its necessity
    target is the analysis date by construction (D2 §8.3), so an earlier-date
    snapshot request can never substitute for it — the target date is the analysis
    date regardless of which snapshot request happened first.
    """
    ctx = analysis_context or {}
    ticker = ctx.get("ticker")
    trade_date = ctx.get("trade_date")
    if item == "get_verified_market_snapshot":
        return {"symbol": ticker, "as_of": trade_date}
    targets = snapshot["targets"]
    if item in targets:
        return targets[item]
    start = ctx.get("stock_start")
    end = ctx.get("stock_end")
    if item == "get_stock_data":
        return {"symbol": ticker, "start_date": start, "end_date": end}
    return None


def _matches_target(item, candidate_params, target_params):
    """Whether a candidate query is the bound target for ``item``.

    Matching is exact on the target's identity keys: a candidate that is MISSING a
    key the target carries is a different query (it must not silently match by
    skipping the missing dimension). Snapshots exclude their utility lookback from
    necessity matching via ``_TARGET_KEYS``.
    """
    keys = _TARGET_KEYS.get(item, ())
    if target_params is None:
        return False
    candidate_params = candidate_params or {}
    for k in keys:
        if k not in target_params:
            continue
        if k not in candidate_params:
            return False      # incomplete identity: not the same query
        if candidate_params.get(k) != target_params.get(k):
            return False
    return True


def _select_current(item, snapshot, analysis_context):
    """Return (status, reason) for a necessity item using target then last-update."""
    target = _target_params_for(item, snapshot, analysis_context)
    best = None       # (sequence, kind, payload)
    for key, (obs, seq) in snapshot["records"].items():
        method, _items = key
        if method != item:
            continue
        if not _matches_target(item, obs.effective_parameters, target):
            continue
        if best is None or seq > best[0]:
            best = (seq, "record", obs)
    for key, (reason, seq) in snapshot["marks"].items():
        method, _items = key
        if method != item:
            continue
        # Reconstruct params from the key for matching.
        params = dict(key[1])
        if not _matches_target(item, params, target):
            continue
        if seq is None:
            continue
        if best is None or seq > best[0]:
            best = (seq, "mark", reason)
    if best is None:
        # No matching completed result: not_attempted, or parameter-rejection note.
        for note in snapshot["call_failures"]:
            if note.get("method") == item:
                return NOT_ATTEMPTED, REASON_PARAM_REJECTED
        return NOT_ATTEMPTED, REASON_NO_COMPLETED
    if best[1] == "mark":
        return UNAVAILABLE, best[2] or REASON_MARKED
    obs = best[2]
    return obs.status, obs.reason


def _object_of(method, params):
    """The real business object of a query for display (D2 §8.3).

    Object-bearing paths report the current object (symbol/ticker); macro reports
    the FRED indicator and prediction markets the topic; global news has no ticker
    object (``None``, never a fabricated one).
    """
    params = params or {}
    for key in ("symbol", "ticker"):
        if params.get(key):
            return params[key]
    if method == "get_macro_indicators":
        return params.get("indicator")
    if method == "get_prediction_markets":
        return params.get("topic")
    return None


# The target keys that express a necessary item's actual applicable range/date.
_RANGE_KEYS = {
    "get_stock_data": ("start_date", "end_date"),
    "get_verified_market_snapshot": ("as_of",),
    "get_income_statement": ("as_of", "freq"),
    "get_balance_sheet": ("as_of", "freq"),
    "get_cashflow": ("as_of", "freq"),
    "get_global_news": ("as_of", "look_back_days", "limit"),
    "fetch_reddit_posts": ("start_date", "end_date", "limit_per_sub"),
}


def _applicable_range_for(item, target):
    """The actual necessary target range/date for ``item`` (D2 §8.3)."""
    if not target:
        return None
    keys = _RANGE_KEYS.get(item, ())
    out = {k: target[k] for k in keys if k in target}
    return out or None


def _observations_projection(snapshot):
    """One projection per current logical query: the last effective result."""
    out = []
    # A single fixed-shape internal entry for both completed records and marks:
    # (observation-or-None, accepted-sequence, mark-reason-or-None). An entry with
    # obs is a completed record; obs is None => it projects a query-level mark.
    latest: dict[tuple, tuple[DataObservation | None, int, str | None]] = {}
    for key, (obs, seq) in snapshot["records"].items():
        existing = latest.get(key)
        if existing is None or seq > existing[1]:
            latest[key] = (obs, seq, None)
    # Marks project as unavailable observations for their query when latest.
    for key, (mark_reason, mark_seq) in snapshot["marks"].items():
        if mark_seq is None:
            continue
        existing = latest.get(key)
        if existing is None or mark_seq > existing[1]:
            latest[key] = (None, mark_seq, mark_reason)
    for key, (obs, _seq, mark_reason) in latest.items():
        method, items = key
        params = dict(items)
        if obs is not None:
            out.append({
                "method": method,
                "object": _object_of(method, params),
                "effective_parameters": params,
                "executing_path_id": snapshot["executing_path"].get(key),
                "supported_path_ids": sorted(snapshot["path_assoc"].get(key, ())),
                "source": obs.source,
                "status": obs.status,
                "reason": obs.reason,
            })
        else:
            out.append({
                "method": method,
                "object": _object_of(method, params),
                "effective_parameters": params,
                "executing_path_id": snapshot["executing_path"].get(key),
                "supported_path_ids": sorted(snapshot["path_assoc"].get(key, ())),
                "source": None,
                "status": UNAVAILABLE,
                "reason": mark_reason or REASON_MARKED,
            })
    return out


def _supplementary_limitations(snapshot, necessary_ids):
    """Actually failed/limited supplementary items plus supplementary pre-fetch
    parameter/date notes (D2 §8.3). Each keeps its reliable known parameters,
    object, source, status and short reason."""
    out = []
    seen = set()
    for obs in _observations_projection(snapshot):
        method = obs["method"]
        if method in necessary_ids:
            continue
        if method not in _SUPPLEMENTARY_METHODS:
            continue
        if obs["status"] == AVAILABLE:
            continue
        seen.add(_query_key(method, obs.get("effective_parameters")))
        out.append({
            "method": method,
            "object": obs["object"],
            "effective_parameters": dict(obs.get("effective_parameters") or {}),
            "status": obs["status"],
            "reason": obs["reason"],
            "source": obs["source"],
        })
    # A supplementary pre-fetch rejection has no legal query key; project it as an
    # unavailable limitation with the fixed parameter-failure reason, unless that
    # query already has a valid/failed observation above.
    for note in snapshot["call_failures"]:
        method = note.get("method")
        if method in necessary_ids or method not in _SUPPLEMENTARY_METHODS:
            continue
        if any(o["method"] == method for o in out):
            continue
        out.append({
            "method": method,
            "object": note.get("object"),
            "effective_parameters": {},
            "status": UNAVAILABLE,
            "reason": note.get("reason") or REASON_PARAM_REJECTED,
            "source": None,
        })
    return out


def _snapshot_from_records(asset_type, enabled_analysts, analysis_context, snapshot):
    """Build the five-field summary from a consistent registry copy (IF-06)."""
    items = _analyst_required_items(enabled_analysts)
    if asset_type != "stock" or not items:
        note = ("Availability summary does not apply to this asset/analyst selection."
                if asset_type != "stock" else "No applicable necessary data items.")
        return {
            "basic_completeness": "not_applicable",
            "applicability_note": note,
            "observations": _observations_projection(snapshot),
            "necessary_items": [],
            "supplementary_limitations": _supplementary_limitations(snapshot, set()),
        }

    necessary = []
    all_available = True
    for item in items:
        target = _target_params_for(item, snapshot, analysis_context)
        status, reason = _select_current(item, snapshot, analysis_context)
        if status != AVAILABLE:
            all_available = False
        necessary.append({
            "item_id": item,
            "method": item,
            "object": _object_of(item, target),
            "applicable_range": _applicable_range_for(item, target),
            "status": status,
            "reason": reason,
        })

    completeness = "complete" if all_available else "incomplete"
    return {
        "basic_completeness": completeness,
        "applicability_note": "",
        "observations": _observations_projection(snapshot),
        "necessary_items": necessary,
        "supplementary_limitations": _supplementary_limitations(snapshot, set(items)),
    }


class AvailabilitySummarizer:
    """IF-06: the sole producer/calculator of a run's availability summary."""

    def __init__(self, registry):
        self._registry = registry

    def snapshot(self, asset_type, enabled_analysts, analysis_context):
        try:
            # One consistent copy: records and the sticky tracking error are read
            # under the same lock, so the None decision uses the same instant as
            # the data (not a prior lock-free probe).
            state = self._registry.snapshot_state()
            if state.get("tracking_error") is not None:
                return None
            # Reference the module global so a test can inject a one-off failure at
            # this construction boundary without setting the sticky error.
            return _snapshot_from_records(asset_type, enabled_analysts,
                                          analysis_context, state)
        except Exception as exc:  # noqa: BLE001 - one-off construction failure
            logger.warning("Availability snapshot construction failed: %s", exc)
            return None


# --------------------------------------------------------------------------- #
# Deterministic renderer (research/final program blocks)                       #
# --------------------------------------------------------------------------- #
def render_summary_block(summary, *, stage="research"):
    """Render a summary mapping to a labeled, deterministic program block.

    ``summary is None`` renders the stage's fixed unavailable text (research vs
    report per D2). No model text, no truncation, no compression.
    """
    if summary is None:
        text = UNAVAILABLE_RESEARCH_TEXT if stage == "research" else UNAVAILABLE_REPORT_TEXT
        return f"Program data-availability summary: {text}"

    lines = [
        "Program data-availability summary (deterministic; not model-generated):",
        f"- basic_completeness: {summary.get('basic_completeness')}",
    ]
    if summary.get("applicability_note"):
        lines.append(f"- applicability_note: {summary['applicability_note']}")
    gaps = [i for i in summary.get("necessary_items", []) if i.get("status") != AVAILABLE]
    if gaps:
        lines.append("- necessary gaps:")
        for gap in gaps:
            lines.append(f"  - {gap.get('item_id')}: {gap.get('status')} "
                         f"({gap.get('reason')})")
    supp = summary.get("supplementary_limitations", [])
    if supp:
        lines.append("- supplementary limitations:")
        for lim in supp:
            lines.append(f"  - {lim.get('method')}: {lim.get('status')} "
                         f"({lim.get('reason')})")
    return "\n".join(lines)


def prepare_research_summary(registry, asset_type, enabled_analysts, analysis_context):
    """Build the ONE research-stage summary from the run's registry (research start).

    Returns the five-field JSON mapping or ``None`` (sticky/construction failure).
    Runs once per analysis at research start; later accepted observations do not
    refresh it. The summarizer alone computes completeness; consumers only render.
    """
    try:
        return AvailabilitySummarizer(registry).snapshot(
            asset_type, enabled_analysts, analysis_context)
    except Exception as exc:  # noqa: BLE001 - a missing summary is null, not fatal
        logger.warning("Research availability summary failed: %s", exc)
        return None


def research_block(summary):
    """The deterministic research-stage block for injection into the researcher
    prompts. ``None`` renders the fixed research-stage unavailable text."""
    return render_summary_block(summary, stage="research")


def research_prompt_block(summary):
    """Pair the fixed snapshot with guidance for its use in research reasoning."""
    return research_block(summary) + (
        "\nIn your reasoning, state what the program can confirm about necessary coverage "
        "for this asset. Distinguish coverage from the strength of the investment case. "
        "For a missing source, identify its scope and acknowledge any other source the "
        "reports show is available. Treat supplementary limitations separately. "
        "If the summary is missing, explain that coverage is unconfirmed and use the "
        "reports you have. If the rules do not apply, identify which rules and why; "
        "that status alone says nothing about individual source outcomes."
    )


def report_block(summary):
    """The deterministic report-stage block for the terminal report/display.
    ``None`` renders the fixed report-stage unavailable text."""
    return render_summary_block(summary, stage="report")
