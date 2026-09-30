"""Check two language variants of a page and report every disagreement.

This is where the pieces join, in the order CLAUDE.md sets:

  1. extract.py reads both pages into Pages of raw strings.
  2. rules.py settles everything a machine can settle without a model.
  3. llm_check.py is asked about prose only -- the one thing rules cannot decide.

ASSUMPTION: prose is paired by index. The first paragraph on the left is
compared with the first on the right, and so on. That holds only if translators
keep the paragraphs in the same order and number. When the counts differ, no
pair is sent to the model at all: once the paragraphs are out of step, every
pair after the gap is two unrelated texts, and asking whether they contradict
each other produces confident nonsense.

Same rule as everywhere else: a check that did not run is reported, never
silently passed. A count mismatch and a missing recording each become a
finding of their own.
"""

from checker.extract import extract
from checker.llm_check import MissingRecordingError, check_prose
from checker.rules import Finding, compare


def _check_prose_pairs(left: list[str], right: list[str]) -> list[Finding]:
    """Findings for the prose, paired by index. See the module docstring."""
    if len(left) != len(right):
        # Left/right carry the counts, the same as the inclusions rule in
        # rules.py -- there is no single pair of texts to show.
        return [Finding("prose", "error",
                        f"{len(left)} prose paragraphs on the left, {len(right)} on the right"
                        " -- prose not checked",
                        str(len(left)), str(len(right)))]

    findings = []
    for left_text, right_text in zip(left, right):
        try:
            verdict = check_prose(left_text, right_text)
        except MissingRecordingError:
            # Only a missing answer is caught. A malformed recording raises
            # ValueError from check_prose and is left to stop the run: that is
            # a broken recording, not an unanswered question.
            findings.append(Finding("prose", "error",
                                    "prose not checked — no recorded answer",
                                    left_text, right_text))
            continue
        if verdict.contradiction:
            findings.append(Finding("prose", "error", verdict.reason,
                                    left_text, right_text))
    return findings


def check_pages(left_path: str, right_path: str) -> list[Finding]:
    """Every disagreement between the pages at left_path and right_path.

    Rule findings come first, in rules.py's fixed order, then prose findings in
    paragraph order. An empty list means both pages agree on everything this
    checker is able to check.
    """
    left = extract(left_path)
    right = extract(right_path)
    return compare(left, right) + _check_prose_pairs(left.prose, right.prose)
