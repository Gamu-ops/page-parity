"""Compare two Pages and report where they disagree.

Deterministic checks only. Everything a machine can settle without a model is
settled here; what is left for llm_check.py is one narrow question about two
blocks of prose.

The organising idea is COMPARE NUMBERS, IGNORE WORDS. The words around a value
are the translation and are supposed to differ -- "ab 899" and "from 949" are
not a language problem, they are a price problem, and the only way to see that
without speaking either language is to look past the words at the 899 and the
949. Every rule in this file is an application of that one idea:

  price      the numbers and the currency must match; "ab" vs "from" must not
  dates      parsed into real dates first, so 12.05.2027 and 12 May 2027 agree
  duration   "8 Tage / 7 Naechte" and "8 days / 7 nights" are both [8, 7]
  group      "max. 8 Teilnehmer" and "max. 8 participants" are both [8]
  inclusions counts only -- matching the items to each other needs translation
  cta        presence and href; the label is words, so it is not compared

A value that cannot be read produces its own finding. Nothing is ever compared
and quietly skipped, because a check that silently does nothing is worse than
no check at all.

Not touched here: prose (llm_check.py's question) and lang.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from checker.extract import Page


@dataclass
class Finding:
    """One disagreement between two pages, or one value that could not be read."""

    field: str
    severity: Literal["error", "info"]
    message: str
    left: str | None
    right: str | None


# --- reading values out of text -------------------------------------------

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

_CURRENCY = re.compile(r"[€$£]|\b(?:EUR|USD|GBP|CHF)\b", re.IGNORECASE)

# Deliberately tiny. An unknown symbol yields no currency at all, which the
# price rule reports as unreadable rather than waving through.
_CURRENCIES = {
    "€": "EUR", "eur": "EUR",
    "$": "USD", "usd": "USD",
    "£": "GBP", "gbp": "GBP",
    "chf": "CHF",
}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

_DATE_NUMERIC = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_DATE_WORDS = re.compile(r"\b(\d{1,2})\.?\s+([A-Za-z]+)\.?\s+(\d{4})\b")


def _to_decimal(token: str) -> Decimal | None:
    """Read one matched number token, working out the separator convention."""
    # The LAST separator decides how the whole token reads: three digits after
    # it and every separator is a thousands separator (1.299 and 1,299 are both
    # 1299); one or two digits after it and that last separator is the decimal
    # point (899,50 and 899.50 are both 899.50). This handles the German and
    # the English convention without knowing which language the page is in. It
    # is wrong only for a three-digit decimal, which is not a thing prices do.
    last = max(token.rfind("."), token.rfind(","))
    if last == -1:
        cleaned = token
    else:
        head = token[:last].replace(".", "").replace(",", "")
        tail = token[last + 1:]
        cleaned = head + tail if len(tail) == 3 else head + "." + tail

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        # A guard, not an expected path -- the regex matches only digits and
        # separators. Dropping a token changes the count, which the rules then
        # report, so this cannot turn into a silent pass.
        return None


def _numbers(text: str) -> list[Decimal]:
    """Every number in text, in the order it appears."""
    values = [_to_decimal(token) for token in _NUMBER.findall(text)]
    return [value for value in values if value is not None]


def _currencies(text: str) -> list[str]:
    """Every currency in text, normalised so the euro sign and EUR agree."""
    return [_CURRENCIES[token.lower()] for token in _CURRENCY.findall(text)]


def _month_number(word: str) -> int | None:
    """Month number for an English month name, full or three-letter."""
    # An explicit table rather than strptime("%B"), which reads the process
    # locale: on a German-locale machine "May" would stop parsing and "Mai"
    # would start, so the checker's answer would depend on who ran it.
    word = word.lower().rstrip(".")
    for name, number in _MONTHS.items():
        if word in (name, name[:3]):
            return number
    return None


def _dates(text: str) -> list[date]:
    """Every date in text as a real date, in the order it appears.

    Returning real dates is what makes a format difference a non-event:
    "12.05.2027" and "12 May 2027" are the same day, so the rule has nothing to
    report. German month names are deliberately not in the table, so
    "12. Mai 2027" is not a date here and the rule calls it unreadable.
    """
    found = []
    for match in _DATE_NUMERIC.finditer(text):
        day, month, year = match.groups()
        found.append((match.start(), int(year), int(month), int(day)))
    for match in _DATE_WORDS.finditer(text):
        day, word, year = match.groups()
        month = _month_number(word)
        if month is not None:
            found.append((match.start(), int(year), month, int(day)))

    dates = []
    # Sorted by position, so a value mixing both formats still comes back in
    # document order.
    for _, year, month, day in sorted(found):
        try:
            dates.append(date(year, month, day))
        except ValueError:
            # 31.02.2027 looks like a date and is not one. Dropping it leaves
            # the rule with nothing to compare, which it reports -- better than
            # inventing a day.
            continue
    return dates


# --- the rules ------------------------------------------------------------

def _missing(field: str, left: str | None, right: str | None) -> list[Finding]:
    """Findings for a value present on one side only.

    Empty when both sides have it and when neither does: two pages that agree
    there is no price are not disagreeing about the price.
    """
    if left is None and right is not None:
        return [Finding(field, "error", f"{field} is missing on the left", left, right)]
    if right is None and left is not None:
        return [Finding(field, "error", f"{field} is missing on the right", left, right)]
    return []


def _unreadable(left: list, right: list) -> list[str]:
    """Which sides produced nothing at all. Empty means both sides parsed."""
    return [side for side, values in (("left", left), ("right", right)) if not values]


def _check_numbers(field: str, left: str | None, right: str | None) -> list[Finding]:
    """Compare the numbers in two values and ignore the words around them."""
    if left is None or right is None:
        return _missing(field, left, right)

    left_numbers = _numbers(left)
    right_numbers = _numbers(right)

    sides = _unreadable(left_numbers, right_numbers)
    if sides:
        return [Finding(field, "error",
                        f"no number to compare on the {' and '.join(sides)}",
                        left, right)]

    if left_numbers != right_numbers:
        shown_left = ", ".join(str(number) for number in left_numbers)
        shown_right = ", ".join(str(number) for number in right_numbers)
        return [Finding(field, "error",
                        f"numbers differ: {shown_left} vs {shown_right}",
                        left, right)]
    return []


def _check_price(left: str | None, right: str | None) -> list[Finding]:
    """The price rule: the numbers must match, and so must the currency."""
    if left is None or right is None:
        return _missing("price", left, right)

    findings = _check_numbers("price", left, right)

    left_currencies = _currencies(left)
    right_currencies = _currencies(right)

    sides = _unreadable(left_currencies, right_currencies)
    if sides:
        findings.append(Finding("price", "error",
                                f"no currency to compare on the {' and '.join(sides)}",
                                left, right))
    elif left_currencies != right_currencies:
        findings.append(Finding("price", "error",
                                f"currency differs: {', '.join(left_currencies)}"
                                f" vs {', '.join(right_currencies)}",
                                left, right))
    return findings


def _check_dates(left: str | None, right: str | None) -> list[Finding]:
    """The dates rule: compare days, not the way the days are written."""
    if left is None or right is None:
        return _missing("dates", left, right)

    left_dates = _dates(left)
    right_dates = _dates(right)

    sides = _unreadable(left_dates, right_dates)
    if sides:
        return [Finding("dates", "error",
                        f"no date to compare on the {' and '.join(sides)}",
                        left, right)]

    if left_dates != right_dates:
        shown_left = ", ".join(day.isoformat() for day in left_dates)
        shown_right = ", ".join(day.isoformat() for day in right_dates)
        return [Finding("dates", "error",
                        f"dates differ: {shown_left} vs {shown_right}",
                        left, right)]
    return []


def _check_inclusions(left: list[str], right: list[str]) -> list[Finding]:
    """Compare how MANY inclusions each page lists, and nothing else.

    Deciding that "Flughafentransfer" and "Airport transfer" are the same item
    needs translation, so it belongs in llm_check.py. Matching them here with
    word similarity would be exactly the move CLAUDE.md rules out: shifting
    work into the layer where it is easier to fudge than to code.
    """
    if len(left) == len(right):
        return []
    return [Finding("inclusions", "error",
                    f"{len(left)} inclusions on the left, {len(right)} on the right",
                    str(len(left)), str(len(right)))]


def _check_cta(left: Page, right: Page) -> list[Finding]:
    """The CTA rule: it must exist on both sides and point to the same place.

    cta_text is never compared. "Jetzt buchen" and "Book now" differing is the
    translation doing its job, not a defect.
    """
    left_present = left.cta_text is not None or left.cta_href is not None
    right_present = right.cta_text is not None or right.cta_href is not None

    if not left_present and not right_present:
        return []
    if not left_present:
        return [Finding("cta", "error", "CTA is missing on the left",
                        None, right.cta_href)]
    if not right_present:
        return [Finding("cta", "error", "CTA is missing on the right",
                        left.cta_href, None)]

    if left.cta_href != right.cta_href:
        # Info rather than error: a translated page pointing at a translated
        # URL is normal. Worth showing, not worth failing over.
        return [Finding("cta", "info", "CTA points to a different href",
                        left.cta_href, right.cta_href)]
    return []


def compare(left: Page, right: Page) -> list[Finding]:
    """Every deterministic disagreement between two language variants of a page.

    Findings come back in a fixed field order, so the output is stable enough to
    diff. An empty list means the pages agree on everything this file is able to
    check -- it says nothing at all about the prose.
    """
    findings = []
    findings += _check_price(left.price, right.price)
    findings += _check_dates(left.dates, right.dates)
    findings += _check_numbers("duration", left.duration, right.duration)
    findings += _check_numbers("group", left.group, right.group)
    findings += _check_inclusions(left.inclusions, right.inclusions)
    findings += _check_cta(left, right)
    return findings
