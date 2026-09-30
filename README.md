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
checker/extract.py    HTML -> raw strings. Finds text, never interprets it.
checker/rules.py      The deterministic comparisons.
checker/llm_check.py  The one semantic question, and the seam an API client would replace.
evals/                15 labelled prose pairs, the recorded answers, and the scoring script.
fixtures/             Two hand-built pages with five planted differences.
```

## Evaluating the model

The model is given one question and its answers are scored against a labelled set, because a
feature that cannot be measured cannot be trusted.

`evals/cases/pairs.json` holds 15 German/English prose pairs. `evals/cases/labels.json` holds the
expected answers **in a separate file**, so the answers cannot reach the model while it is
answering — the blindness is enforced by the file layout rather than by good intentions.

Current result (`python -m evals.run_evals`):

```
precision  1.00
recall     0.71
accuracy   0.87
```

Across 7 real contradictions and 8 clean pairs: **5 caught, 2 missed, 0 false alarms.**

The two misses are not random. Both are the same kind of case:

| case | what the model said |
|---|---|
| `wifi-scope` | "WiFi in common areas" vs "WiFi throughout the property" — *adds scope rather than conflicting* |
| `meals-half-board` | "Halbpension" vs "breakfast included" — *less complete, but does not state anything the German contradicts* |

That is a reasoned disagreement, not a failure to understand. The model draws the line between
**contradicting** and **saying less** in a different place than the labels do — and the spec never
defined that line. Measuring it is what made the ambiguity visible.

The labels stand, with the rule now stated: *a difference in scope or completeness that would
mislead a customer counts as a contradiction.* A reader of the English page would book expecting
WiFi in their room and breakfast rather than half board. That is a product decision, not a
technicality, and closing the gap belongs in the prompt rather than in the label set.

Precision 1.00 with recall 0.71 is the right shape for this tool, and the deliberate one: a
checker that never cries wolf but misses some things stays in use, while one that flags clean
pages gets switched off within a week.

**The recordings are real model output**, produced by Claude Code answering the 15 pairs blind and
saved to `evals/recorded/`. They are not hand-written fixtures, and the numbers above are measured,
not asserted.

## Status

Done and verified: `extract.py`, `rules.py`, `llm_check.py`, the eval set and its score. The
deterministic rules are tested against the fixtures plus the edge cases the fixtures cannot reach —
thousands separators, decimal commas, impossible dates, unsupported month names, missing values.

Next:

- a small React page over the findings
- German month names in the date table (a real German page writes "12. Mai 2027", which the
  checker currently calls unreadable)
- a fixture variant using written-out German months, so that gap cannot silently return
- a prompt that states the scope-and-completeness rule, and a re-run to see whether recall moves

Built with Claude Code. The code is reviewed and owned by me.
