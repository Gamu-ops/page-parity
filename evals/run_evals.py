"""Score check_prose against the labelled prose pairs.

Run from the repo root:

    python -m evals.run_evals

The pairs (evals/cases/pairs.json) and the expected answers
(evals/cases/labels.json) are kept in separate files, so the texts can be read
without seeing the answers. This script joins them by id, asks check_prose
about every pair, and reports how often it agreed with the label.

"Contradiction" is the positive class: a true positive is a real contradiction
that was flagged, a false negative is a real contradiction that was missed.
For a checker, false negatives are the expensive kind -- a missed defect ships.

Nothing is skipped. A pair without a label, a label without a pair, or a pair
without a recording stops the run, because a score over fewer cases than you
think you have is a wrong score that looks right.
"""

import json
from pathlib import Path

from checker.llm_check import check_prose

CASES_DIR = Path(__file__).resolve().parent / "cases"


def _load_json(name: str):
    with (CASES_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def _check_ids_match(pairs: list[dict], labels: dict) -> None:
    """Raise unless every pair has a label and every label has a pair."""
    pair_ids = {pair["id"] for pair in pairs}
    label_ids = set(labels)
    unlabelled = sorted(pair_ids - label_ids)
    orphaned = sorted(label_ids - pair_ids)
    if unlabelled or orphaned:
        raise ValueError(
            "pairs.json and labels.json do not cover the same cases\n"
            f"  pairs with no label: {', '.join(unlabelled) or 'none'}\n"
            f"  labels with no pair: {', '.join(orphaned) or 'none'}"
        )


def _ratio(numerator: int, denominator: int) -> str:
    """A ratio to 2 decimals, or n/a when it is undefined."""
    # n/a rather than 0.00: with nothing flagged, precision is not zero, it
    # does not exist, and printing 0.00 would claim a result that was not had.
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.2f}"


def main() -> None:
    pairs = _load_json("pairs.json")
    labels = _load_json("labels.json")
    _check_ids_match(pairs, labels)

    tp = fp = fn = tn = 0
    wrong = []
    for pair in pairs:
        expected = labels[pair["id"]]["expected_contradiction"]
        verdict = check_prose(pair["left"], pair["right"])
        given = verdict.contradiction

        if expected and given:
            tp += 1
        elif not expected and given:
            fp += 1
        elif expected and not given:
            fn += 1
        else:
            tn += 1

        if expected != given:
            wrong.append((pair["id"], expected, given, verdict.reason))

    total = tp + fp + fn + tn
    print(f"cases: {total}")
    print(f"TP {tp}  FP {fp}  FN {fn}  TN {tn}")
    print()
    print(f"precision  {_ratio(tp, tp + fp)}")
    print(f"recall     {_ratio(tp, tp + fn)}")
    print(f"accuracy   {_ratio(tp + tn, total)}")
    print()

    if not wrong:
        print("No wrong cases.")
        return

    # Column width follows the longest id, so the table stays aligned when
    # cases are added. The reason is the last column and is never cut short.
    id_width = max(len("id"), *(len(case_id) for case_id, _, _, _ in wrong))
    print(f"{'id':<{id_width}}  {'expected':<8}  {'given':<5}  reason")
    print(f"{'-' * id_width}  {'-' * 8}  {'-' * 5}  {'-' * 6}")
    for case_id, expected, given, reason in wrong:
        print(f"{case_id:<{id_width}}  {str(expected):<8}  {str(given):<5}  {reason}")


if __name__ == "__main__":
    main()
