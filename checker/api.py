"""HTTP wrapper around check_pages, for the Vite frontend.

One endpoint:

  GET /check?left=fixtures/trip-en.html&right=fixtures/trip-de.html

returns the findings as a JSON list of objects with field, severity, message,
left and right. Run it from the repo root:

  uvicorn checker.api:app --reload

Paths are relative to the repo root and must point inside FIXTURES_DIR. Anything
outside it is rejected with 400, so a caller cannot make the server open an
arbitrary file. FIXTURES_DIR is hardcoded on purpose: that is correct for a demo
tool. A real deployment would make it configurable.
"""

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from checker.check import check_pages

# Built from this file's location, not the working directory, so it does not
# matter where uvicorn is launched from.
REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"

app = FastAPI()

# The Vite dev server runs on a different port, so without this the browser
# blocks the response. Only that one origin is allowed.
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:5173"],
                   allow_methods=["GET"])


def _fixture_path(raw: str) -> str:
    """The absolute path for raw, or an HTTP error if it is not a fixture file."""
    # Resolve first, then check containment: resolve() collapses ".." and
    # follows symlinks, so "fixtures/../checker/rules.py" is caught here.
    resolved = (REPO_ROOT / raw).resolve()
    if not resolved.is_relative_to(FIXTURES_DIR):
        raise HTTPException(400, f"{raw!r} is outside fixtures/")

    # is_file() rather than catching FileNotFoundError later: a directory also
    # gets a clean 404. The message is relative to the repo root so the server's
    # directory layout is not echoed back.
    if not resolved.is_file():
        raise HTTPException(404, f"{resolved.relative_to(REPO_ROOT).as_posix()} not found")
    return str(resolved)


@app.get("/check")
def check(left: str, right: str) -> list[dict]:
    """Every finding for the two pages. A plain def: FastAPI runs it in a thread."""
    findings = check_pages(_fixture_path(left), _fixture_path(right))
    return [asdict(finding) for finding in findings]
