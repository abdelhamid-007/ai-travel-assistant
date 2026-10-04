"""Unit tests for the rule-based parts of the assistant. They need no database and no model."""
import pytest
from rules import find_cited, read_filters


@pytest.mark.parametrize(
    ("question", "max_price", "month"),
    [
        ("Trips under 1000 DT?", 1000, None),
        ("Something below 2 500 DT in November", 2500, 11),
        ("Un voyage à moins de 1,800 DT en juillet ?", 1800, 7),
        ("What can I do in December?", None, 12),
        ("Que faire en décembre ?", None, 12),
        ("Budget of 3000, any idea?", 3000, None),
        ("I want a relaxing spa weekend near the sea", None, None),
    ],
)
def test_read_filters(question, max_price, month):
    assert read_filters(question) == {"max_price": max_price, "month": month}


def test_month_names_are_whole_words():
    # "mayor" contains "may" and "maison" contains "mai": neither is a month
    assert read_filters("Ask the mayor about a maison near the beach")["month"] is None


BLOCKS = {
    "O1": "Offer: Hammamet Thalasso Weekend (Hammamet, Tunisia). 4 Days / 3 Nights. Price: 780 DT.",
    "O2": "Offer: Tozeur Sahara Desert Adventure (Tozeur, Tunisia). 4 Days / 3 Nights. Price: 1100 DT.",
    "F1": "Q2: How much deposit do I need to pay?\nA2: You pay a 30% deposit.",
}


def test_find_cited_reads_source_labels():
    assert find_cited("You pay a 30% deposit. (source: F1)", BLOCKS) == ["F1"]


def test_find_cited_ignores_labels_that_were_not_in_the_context():
    assert find_cited("We have a cruise. (source: O9)", BLOCKS) == []


def test_find_cited_adds_offers_named_but_not_cited():
    answer = "Try the Hammamet Thalasso Weekend or the Tozeur Sahara Desert Adventure. (source: O1)"
    assert find_cited(answer, BLOCKS) == ["O1", "O2"]


def test_find_cited_returns_nothing_for_an_answer_without_sources():
    assert find_cited("Yes, we have a restaurant on site.", BLOCKS) == []
