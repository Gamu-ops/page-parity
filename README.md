# page-parity

Compares two language variants of the same landing page and reports where they disagree —
prices, dates, list items, calls to action, and contradictions in the prose.

Work in progress. What is here works and is verified; what is not here is listed at the bottom.

## Why

Checking that a German and an English page still say the same thing after an edit is slow, easy
to get wrong, and gets skipped under deadline. Prices drift. A bullet point goes missing in one
language. A paragraph promises something the other one doesn't.

## How it is built

**Deterministic checks run first. The model only gets what rules cannot settle.**

Five kinds of difference. Four of them need no AI at all:

| Check | Needs a model? |
|---|---|
| Price — numbers and currency must match | no |
| Dates — `12.05.2027` and `12 May 2027` are the same day | no |
| Duration and group size — the numbers must match | no |
| Inclusions — six items against five | no |
| Prose — "Flug nicht inklusive" against "flights included" | **yes** |

The organising idea is **compare numbers, ignore words**. The words around a value are the
translation and are supposed to differ; the numbers are not. That single rule covers price,
duration and group size.

Two decisions that follow from it:

- **The number parser is locale-blind.** `1.299` and `1,299` both read as 1299 using the same
  rule, rather than picking a convention from the page language — otherwise two pages containing
  identical text could parse to different numbers and be reported as disagreeing.
- **Month names come from an explicit table, not `strptime`,** which reads the process locale.
  The checker has to give the same answer regardless of which machine runs it.

**A value that cannot be read produces its own finding.** Never a silent pass — a report with no
errors has to mean the pages agree, not "the pages agree on whatever I managed to check".

## Layout

```
checker/extract.py   HTML -> raw strings. Finds text, never interprets it.
checker/rules.py     The deterministic comparisons.
fixtures/            Two hand-built pages with five planted differences.
```

## Status

Done: `extract.py`, `rules.py`. Verified against the fixtures plus edge cases the fixtures
cannot reach — thousands separators, decimal commas, impossible dates, unsupported month names,
missing values.

Next:

- `llm_check.py` — the one semantic question, against recorded responses
- `evals/` — labelled cases and a precision/recall score for the model's output
- a small React page over the results
- German month names in the date table (a real German page writes "12. Mai 2027", which the
  checker currently calls unreadable)
- a fixture variant using written-out German months, so that gap cannot silently return

Built with Claude Code. The code is reviewed and owned by me.
