# page-parity — working rules for Claude Code

Read this before doing anything in this repo.

## What this is
A consistency checker for multilingual landing pages. Two language variants of the same page go in;
it reports where they disagree — prices, dates, CTAs, missing sections, semantic drift in prose.

It is also a portfolio artifact. Its purpose is to show that I can direct AI tooling **and** own the
result. That purpose sets the rules below. Please hold me to them.

## Architecture rule — this is the point of the project, not a detail
1. Deterministic checks run FIRST (`checker/rules.py`). A price of 899 vs 999 is a rule, not a
   judgement call. Cheap, testable, no model involved.
2. The LLM runs ONLY on what rules cannot decide (`checker/llm_check.py`) — two blocks of prose,
   one question: do these say the same thing? Structured JSON back.
3. Every LLM output is scored against labelled cases (`evals/`).

Never move work from step 1 into step 2 because it is easier to prompt than to code.

## The LLM is in recorded mode
I have no API key. `llm_check.py` reads responses from `evals/recorded/`. The interface must be written
so a real API client can be dropped in later without changing callers. Don't add an SDK dependency.

## How I want you to work with me
- **Do not write code I can't explain.** If a piece needs an abstraction I haven't used before, say so
  and explain it before writing it, or propose a simpler version.
- One file at a time. Show me the plan for a file before writing it.
- Ask before adding any dependency. Current allowed set is in `requirements.txt`.
- Prefer boring, readable Python over clever Python. This will be read by a hiring manager.
- When you are uncertain or guessing (a selector, an edge case, an API shape), say so in the moment
  rather than presenting a guess as settled. I need to know which parts are load-bearing guesses.

## Out of scope — do not add
Database, auth, Docker, CI, deployment, more than two languages, component libraries, state management
libraries, styling systems. A small finished repo beats a large half-finished one.

## Never
- No employer or client content. Fixtures are written by me, from scratch.
- No real API keys, tokens or `.env` files committed, at any point, even temporarily.
