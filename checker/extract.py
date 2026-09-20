"""Turn one local HTML page into a Page of raw strings.

This is the parse layer and nothing more. It answers "what does the page say
here?", never "is that right?". Comparing 899 against 949 is rules.py's job;
deciding whether two paragraphs mean the same thing is llm_check.py's.

Two things to know before writing rules against these values:

1. Whitespace is collapsed. The source HTML wraps paragraphs across lines, so
   the text arrives with a newline and indentation inside a sentence. Runs of
   whitespace become a single space and the ends are trimmed. That is the only
   transformation in this file and it touches whitespace only -- 899, EUR and
   en-dash characters, "max.", "8 Tage / 7 Naechte" all pass through as they
   are.

2. HTML entities are decoded by the parser before this module sees the text:
   &euro; arrives as the character EUR, &ndash; as an en-dash, &uuml; as u
   with an umlaut. So price is "ab 899 <euro sign>", never "ab 899 &euro;",
   and rules must be written against real Unicode characters.

A missing element and an element that exists but is empty are the same thing
here: None for the single values, absent from the list for the repeated ones.
There is exactly one "no value" state for callers to test.
"""

from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass
class Page:
    """The parts of a landing page the checker compares, as raw strings."""

    lang: str | None
    price: str | None
    dates: str | None
    duration: str | None
    group: str | None
    inclusions: list[str]
    cta_text: str | None
    cta_href: str | None
    prose: list[str]


def _clean(text: str) -> str:
    """Collapse runs of whitespace into single spaces and trim the ends.

    Callers pass get_text(" ") so that inline markup cannot fuse two words
    into one -- "<strong>10</strong>Stunden" has to come out as "10 Stunden",
    not "10Stunden". The extra spaces that separator introduces are collapsed
    back out here, so the pair cannot produce double spaces.
    """
    return " ".join(text.split())


def _one(soup: BeautifulSoup, selector: str) -> str | None:
    """Text of the first element matching selector, or None if there is none."""
    # select_one takes the FIRST match and ignores any others. That is
    # deliberate, not an oversight: if a page carries two .hero__price
    # elements then the page is broken, and guessing which one is
    # authoritative is not this module's call to make.
    element = soup.select_one(selector)
    if element is None:
        return None
    # An element that exists but is empty counts as no value, the same as a
    # missing one, so that rules.py has a single absence to check for.
    return _clean(element.get_text(" ")) or None


def _many(soup: BeautifulSoup, selector: str) -> list[str]:
    """Text of every element matching selector, in document order."""
    # Entries that clean to empty are dropped rather than kept as blanks, for
    # the same reason _one returns None instead of "".
    return [text for element in soup.select(selector)
            if (text := _clean(element.get_text(" ")))]


def _attr(element: Tag | None, name: str) -> str | None:
    """Value of an attribute on element, with missing and empty treated alike.

    The str | None annotation holds only for single-valued attributes, which
    is all this module asks for (href, lang). BeautifulSoup returns a LIST for
    multi-valued attributes such as class or rel, so a caller reaching for one
    of those has to handle the list itself.
    """
    if element is None:
        return None
    # Taken verbatim -- collapsing whitespace inside a URL would be meddling
    # rather than tidying -- but "" becomes None so that attributes have the
    # same single absence state as everything else.
    return element.get(name) or None


def extract(path: str) -> Page:
    """Parse the HTML file at path into a Page."""
    # The encoding is explicit because open() defaults to the system codepage
    # on Windows, which would mangle any literal accented character.
    with open(path, encoding="utf-8") as handle:
        soup = BeautifulSoup(handle.read(), "html.parser")

    # The CTA's text and href come from the same element, so it is fetched
    # once rather than selected twice for the two halves of one tag. The two
    # fields stay independent: a CTA with a destination and no label reports
    # as cta_text=None with cta_href set, because that is a real defect and
    # flattening it to "no CTA" would hide it.
    cta = soup.select_one("a.cta")
    cta_text = None
    if cta is not None:
        cta_text = _clean(cta.get_text(" ")) or None

    return Page(
        lang=_attr(soup.find("html"), "lang"),
        price=_one(soup, ".hero__price"),
        dates=_one(soup, ".trip-dates"),
        duration=_one(soup, ".trip-duration"),
        group=_one(soup, ".trip-group"),
        inclusions=_many(soup, "ul.inclusions li"),
        cta_text=cta_text,
        cta_href=_attr(cta, "href"),
        prose=_many(soup, ".details p"),
    )
