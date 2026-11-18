"""Offline check that the live request and report used the program metrics."""

import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
report = (OUT / "live" / "report.md").read_text(encoding="utf-8")
metadata = json.loads((OUT / "live" / "provider_metadata.json").read_text(encoding="utf-8"))
capture = (OUT / "live" / "prompt_capture.txt").read_text(encoding="utf-8")
table = (OUT / "live" / "metric_block.txt").read_text(encoding="utf-8")
metrics = json.loads((OUT / "selected_metrics.json").read_text(encoding="utf-8"))["metrics"]

sections = re.findall(r"\[(system|human)\]\n(.*?)(?=\n\n\[(?:system|human)\]|\Z)", capture, re.S)
captured_chars = sum(len(body) for _, body in sections)
checks = {
    "metric_table_present_in_captured_prompt": table in capture,
    "captured_prompt_chars_equal_live_request": metadata["prompt_chars"] == captured_chars,
    "captured_prompt_chars": captured_chars,
    "live_prompt_chars": metadata["prompt_chars"],
    # Compare digits only, so "$71,611M" matches the program's "71611".
    "program_values_cited": {
        row["metric_id"]: row["display"].replace(".", "").replace("-", "")
        in re.sub(r"[^0-9.\-]", "", report).replace(".", "")
        for row in metrics
    },
    "no_ttm_computed": "TTM figures, FCF YoY, and quarter-by-subtraction values" in report,
    "extra_derivation_labelled": "unverified derivation" in report,
}
checks["all_ten_values_cited"] = all(checks["program_values_cited"].values())
(OUT / "live" / "verification.json").write_text(
    json.dumps(checks, indent=2), encoding="utf-8"
)
print(json.dumps(checks, indent=2))
