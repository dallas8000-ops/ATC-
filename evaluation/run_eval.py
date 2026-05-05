#!/usr/bin/env python3
"""
Regression evaluation for webapp ATCFormatter + classify_speaker_role.

Usage (from repo root):
  python evaluation/run_eval.py
  python evaluation/run_eval.py --golden evaluation/custom_gold.json
  python evaluation/run_eval.py --json

Exit code 1 if any configured threshold fails (for CI).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def _load_core(repo_root: Path):
    """Import shared atc_core (single source of truth for formatter + classifier)."""
    core_path = repo_root / "atc_core.py"
    if not core_path.is_file():
        raise FileNotFoundError(f"Missing {core_path}")
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    import atc_core  # noqa: PLC0415 — defer until repo_root is on path

    return atc_core


def _word_edit_distance(ref_words: list[str], hyp_words: list[str]) -> int:
    m, n = len(ref_words), len(hyp_words)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[m][n]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words and not hyp_words:
        return 0.0
    dist = _word_edit_distance(ref_words, hyp_words)
    return dist / max(len(ref_words), 1)


def _violation_multiset_delta(actual: list[str], expected: list[str]) -> tuple[int, int, int]:
    """Returns (false_positives, false_negatives, true_positives) treating strings as multiset items."""
    ca, ce = Counter(actual), Counter(expected)
    fp = sum((ca - ce).values())
    fn = sum((ce - ca).values())
    tp = sum((ca & ce).values())
    return fp, fn, tp


def run_case(formatter, classify, case: dict) -> dict:
    text = case["input"]
    expected_fmt = case["expected_formatted"]
    expected_v = list(case.get("expected_violations", []))
    expected_role = case.get("expected_role")

    formatted, violations = formatter.format_transcript(text)
    role_result = classify(text)
    actual_role = role_result["speaker_role"]

    wer = word_error_rate(expected_fmt, formatted)
    exact = formatted == expected_fmt
    fp, fn, tp = _violation_multiset_delta(violations, expected_v)
    violations_exact = fp == 0 and fn == 0

    role_ok = True
    if expected_role is not None:
        role_ok = actual_role == expected_role

    return {
        "id": case["id"],
        "format_exact": exact,
        "wer": wer,
        "violations_exact": violations_exact,
        "violation_fp": fp,
        "violation_fn": fn,
        "violation_tp": tp,
        "role_ok": role_ok,
        "expected_role": expected_role,
        "actual_role": actual_role,
        "formatted": formatted,
        "expected_formatted": expected_fmt,
        "violations": violations,
        "expected_violations": expected_v,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ATC formatter + role golden evaluation")
    parser.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="Path to golden_set.json (default: evaluation/golden_set.json next to this file)",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable report only")
    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    repo_root = eval_dir.parent
    golden_path = args.golden or (eval_dir / "golden_set.json")

    with open(golden_path, encoding="utf-8") as f:
        bundle = json.load(f)

    cases = bundle["cases"]
    thresholds = bundle.get("thresholds", {})

    core = _load_core(repo_root)
    formatter = core.ATCFormatter()
    classify = core.classify_speaker_role

    rows = [run_case(formatter, classify, c) for c in cases]
    n = len(rows)

    format_exact_rate = sum(1 for r in rows if r["format_exact"]) / n
    mean_wer = sum(r["wer"] for r in rows) / n
    violation_exact_rate = sum(1 for r in rows if r["violations_exact"]) / n
    role_rows = [r for r in rows if r["expected_role"] is not None]
    role_accuracy = (
        sum(1 for r in role_rows if r["role_ok"]) / len(role_rows) if role_rows else 1.0
    )

    total_v_fp = sum(r["violation_fp"] for r in rows)
    total_v_actual = sum(len(r["violations"]) for r in rows)
    false_violation_rate = total_v_fp / max(total_v_actual, 1)

    min_fmt = float(thresholds.get("min_format_exact_rate", 1.0))
    max_wer = float(thresholds.get("max_mean_wer", 0.0))
    min_viol = float(thresholds.get("min_violation_exact_rate", 1.0))
    min_role = float(thresholds.get("min_role_accuracy", 1.0))

    failures = []
    if format_exact_rate + 1e-9 < min_fmt:
        failures.append(
            f"format_exact_rate {format_exact_rate:.4f} < threshold {min_fmt}"
        )
    if mean_wer > max_wer + 1e-9:
        failures.append(f"mean_wer {mean_wer:.4f} > threshold {max_wer}")
    if violation_exact_rate + 1e-9 < min_viol:
        failures.append(
            f"violation_exact_rate {violation_exact_rate:.4f} < threshold {min_viol}"
        )
    if role_accuracy + 1e-9 < min_role:
        failures.append(f"role_accuracy {role_accuracy:.4f} < threshold {min_role}")

    report = {
        "golden_file": str(golden_path),
        "case_count": n,
        "format_exact_rate": format_exact_rate,
        "mean_wer": mean_wer,
        "violation_exact_rate": violation_exact_rate,
        "role_accuracy": role_accuracy,
        "false_violation_rate": false_violation_rate,
        "total_violation_false_positives": total_v_fp,
        "total_actual_violations": total_v_actual,
        "thresholds": thresholds,
        "failures": failures,
        "cases": rows,
    }

    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(f"Golden: {golden_path}")
        print(f"Cases: {n}")
        print(f"  format_exact_rate:    {format_exact_rate:.4f} (min {min_fmt})")
        print(f"  mean_wer:             {mean_wer:.4f} (max {max_wer})")
        print(f"  violation_exact_rate: {violation_exact_rate:.4f} (min {min_viol})")
        print(f"  role_accuracy:        {role_accuracy:.4f} (min {min_role})")
        print(f"  false_violation_rate: {false_violation_rate:.4f} (FP/total actual violations)")
        if failures:
            print("FAILED:")
            for line in failures:
                print(f"  - {line}")
        else:
            print("PASS — all thresholds met.")
        for r in rows:
            if not (r["format_exact"] and r["violations_exact"] and r["role_ok"]):
                print(f"\n[{r['id']}]")
                if not r["format_exact"]:
                    print("  format: EXACT mismatch (WER={:.4f})".format(r["wer"]))
                    print("  exp:", r["expected_formatted"][:200])
                    print("  act:", r["formatted"][:200])
                if not r["violations_exact"]:
                    print(
                        f"  violations: exact mismatch (fp={r['violation_fp']} fn={r['violation_fn']})"
                    )
                if not r["role_ok"]:
                    print(
                        f"  role: expected {r['expected_role']!r} got {r['actual_role']!r}"
                    )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
