"""Offline consistency check; never declares source independence or Stage A approval."""

import hashlib
import json
from pathlib import Path

import build_reference
import inspect_saved_filings

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(manifest):
    projection = {k: v for k, v in manifest.items() if k not in ("manifest_content_sha256", "human_review")}
    expected = hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if expected != manifest["manifest_content_sha256"]:
        raise ValueError("manifest_projection_digest_mismatch")
    for name, value in manifest["files"].items():
        if digest(ROOT / name) != value:
            raise ValueError(f"artifact_digest_mismatch:{name}")
    if len({issuer["cik"] for issuer in manifest["issuers"]}) < 2:
        raise ValueError("need_two_distinct_issuers")
    assert all(issuer["cik"] != "0001045810" for issuer in manifest["issuers"])
    assert manifest["status"] == "pending_human_review_not_frozen"
    assert manifest["frozen_at"] is None and manifest["human_review"]["status"] == "pending"
    assert not manifest["application_implementation_started"]


def witness_checks():
    facts, prices = load("selected_facts.json"), load("price_records.json")
    checks = {}
    for path in sorted((ROOT / "controlled_variants").glob("*.json")):
        case = load(str(path.relative_to(ROOT)))
        key = case["base_record_id"]
        original = prices[key.split(".")[0]] if key.endswith(".price") else facts[key]
        assert original == case["base_record"]
        assert case["is_real_disclosure"] is False and case["application_test_executed"] is False
        operation = case["controlled_override"]["operation"]
        after = case["controlled_override"]["after"]
        if operation == "replace_record":
            replacement = facts[after]
            assert (original["fiscal_year"], original["fiscal_quarter"], original["span"]) != (
                replacement["fiscal_year"], replacement["fiscal_quarter"], replacement["span"])
        elif operation == "analysis_as_of":
            assert original.get("filed_at", original.get("actual_price_date")) > after
        elif operation == "remove_record":
            assert key in facts and after is None
        elif operation == "unit":
            assert original["unit"] != after
        elif operation == "currency":
            assert original["currency"] != after
        elif operation == "adjustment_basis":
            assert "unverified" in after
        elif operation == "raw_sign_rule":
            assert after == "unknown" and "PaymentsToAcquirePropertyPlantAndEquipment" in original["concept"]
        elif operation == "value":
            assert int(after) <= 0 and original["value"] != after
        elif operation == "target_fiscal_position":
            assert [original["fiscal_year"], original["fiscal_quarter"]] == after == [2025, 1]
            assert not any(f["issuer"] == "xom" and f["span"] == "quarter" and
                           (f["fiscal_year"], f["fiscal_quarter"]) == (2024, 4) for f in facts.values())
        else:
            raise AssertionError(f"unhandled_control:{operation}")
        checks[case["id"]] = "input/precondition witness consistent; expected n/a/exclusion remains a reviewed specification, NOT an application test"
    return checks


def verify():
    manifest = load("reference_manifest.json")
    verify_manifest(manifest)
    for path in sorted((ROOT / "sources").glob("*.htm")):
        parsed, text = inspect_saved_filings.inspect(path)
        assert parsed == load(f"inspection/{path.stem}.inline.json")
        assert "\n".join(text) + "\n" == (ROOT / f"inspection/{path.stem}.text.txt").read_text(encoding="utf-8")
    build_reference.main(check=True)
    rows = load("expected_metrics.json")
    assert len(rows) == 20 and sum(row["status"] == "computed" for row in rows) == 18
    assert len(load("selected_facts.json")) == 30
    assert all(row["status"] in ("computed", "n/a") for row in rows)
    assert not any("ttm" in row["metric_id"] or "fcf_yoy" in row["metric_id"] for row in rows)
    coverage = load("coverage.json")["metrics"]
    assert len(coverage) == 10 and all(entry["computed"] for entry in coverage.values())
    witnesses = witness_checks()
    assert len(witnesses) == 12
    return {"consistency_pass": True, "saved_source_files": len(load("source_manifest.json")["sources"]),
            "selected_fact_count": 30, "metric_rows": 20, "computed_reference_rows": 18, "n_a_reference_rows": 2,
            "positive_metric_families": 10, "controlled_precondition_witnesses": witnesses,
            "human_review": "pending", "frozen": False, "stage_a_pass": False,
            "limitation": "Consistency is not business/source independence approval or application acceptance.",
            "manifest_content_sha256": manifest["manifest_content_sha256"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
