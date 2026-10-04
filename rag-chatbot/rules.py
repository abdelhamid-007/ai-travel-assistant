"""Pure logic with no database or model calls, so it can be unit-tested anywhere (including CI)."""
import re

MONTHS = {
    "january": 1, "janvier": 1, "february": 2, "fevrier": 2, "février": 2, "march": 3, "mars": 3,
    "april": 4, "avril": 4, "may": 5, "mai": 5, "june": 6, "juin": 6, "july": 7, "juillet": 7,
    "august": 8, "aout": 8, "août": 8, "september": 9, "septembre": 9, "october": 10, "octobre": 10,
    "november": 11, "novembre": 11, "december": 12, "decembre": 12, "décembre": 12,
}


def read_filters(question):
    """Read hard facts from the question with simple rules. Vectors are bad at "under 2000 DT"."""
    q = question.lower()
    price = re.search(r"(?:under|below|less than|max(?:imum)?|moins de|budget(?: of)?)\s*(\d[\d\s,.]*\d|\d)", q)
    max_price = int(re.sub(r"\D", "", price.group(1))) if price else None
    month = next((n for name, n in MONTHS.items() if re.search(rf"\b{name}\b", q)), None)
    return {"max_price": max_price, "month": month}


def find_cited(answer, blocks):
    """Labels of the context blocks an answer used: the ones it cites, like (source: O1, F2), plus any
    offer whose title appears in the answer, because small models often forget a label."""
    cited = [label for label in re.findall(r"\b([OF]\d+)\b", answer) if label in blocks]
    for label, text in blocks.items():
        title = re.match(r"Offer: (.+?) \(", text)
        if title and title.group(1).lower() in answer.lower() and label not in cited:
            cited.append(label)
    return cited
