"""Ask whether two blocks of prose say the same thing.

This is the only place a model is involved, and it gets one narrow question:
given the same paragraph in two languages, does one contradict the other?
Everything a machine can settle without a model -- prices, dates, counts --
has already been settled by rules.py and never reaches this file.

The model is in RECORDED MODE. There is no API key, so answers are read from
evals/recorded/<key>.json, where the key is a hash of the two texts. The rule
is the same as in rules.py: nothing silently passes. A pair with no recording
raises MissingRecordingError. It never comes back as "no contradiction",
because a missing answer that looks like a clean answer is the worst possible
failure for a checker.

One known limit of the key: it hashes the two texts only, not a prompt or a
model name. Recorded mode has neither, so that is fine today. Once a real client
exists, changing its prompt would NOT invalidate old recordings -- they would
still match and be reused.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

# Found relative to this file, not the working directory, so the answer does
# not depend on where the checker is run from.
RECORDED_DIR = Path(__file__).resolve().parent.parent / "evals" / "recorded"


@dataclass
class ProseVerdict:
    """The model's answer for one pair of prose blocks."""

    contradiction: bool
    reason: str


class MissingRecordingError(Exception):
    """No recorded answer exists for this pair of texts."""


def recording_key(left: str, right: str) -> str:
    """The file name a recording for this pair is stored under.

    Public because anything that records or looks up answers must use exactly
    this recipe; a second copy of it elsewhere would drift.
    """
    return hashlib.sha256(f"{left}\n---\n{right}".encode("utf-8")).hexdigest()[:16]


def _preview(text: str) -> str:
    """The start of a text, short enough to fit in an error message."""
    return text if len(text) <= 60 else text[:60] + "..."


# --- the seam -------------------------------------------------------------
#
# This is the one function a real API client replaces. The contract:
# take the two texts, return a dict with "contradiction" and "reason".
# Nothing else in the codebase knows where the answer comes from, so swapping
# this body for an HTTP call changes no callers. The answer is checked by
# check_prose below, not here, so a real client's output gets the same checks
# a recording does.

def _ask_model(left: str, right: str) -> dict:
    """Get the raw answer for one pair. Today: read it from a recording."""
    key = recording_key(left, right)
    path = RECORDED_DIR / f"{key}.json"
    if not path.exists():
        raise MissingRecordingError(
            f"no recording for key {key} (expected {path})\n"
            f"  left:  {_preview(left)}\n"
            f"  right: {_preview(right)}"
        )
    # A file that is not valid JSON raises JSONDecodeError here. That is
    # already a loud, specific error, so it is left to propagate.
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------

def check_prose(left: str, right: str) -> ProseVerdict:
    """Whether two blocks of prose contradict each other, with the reason."""
    answer = _ask_model(left, right)

    # Checked strictly because a loose answer can pass as a clean one: the
    # string "false" is truthy, and a missing key read with .get() is None,
    # which reads as "no contradiction". Only a real bool is accepted.
    if not isinstance(answer, dict):
        raise ValueError(f"model answer is not a JSON object: {answer!r}")
    if not isinstance(answer.get("contradiction"), bool):
        raise ValueError(f"model answer has no boolean 'contradiction': {answer!r}")
    if not isinstance(answer.get("reason"), str):
        raise ValueError(f"model answer has no string 'reason': {answer!r}")

    return ProseVerdict(contradiction=answer["contradiction"], reason=answer["reason"])
