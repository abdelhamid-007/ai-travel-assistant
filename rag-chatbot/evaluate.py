"""Scores the assistant. must_contain: words a correct answer needs. None: must say "I don't know".
must_not_contain: words that would mean a wrong answer (a full, past or archived trip)."""
from assistant import ask

tests = [
    # meaning search: no exact words from the offers
    ("I want a relaxing spa weekend near the sea", ["thalasso"], []),
    ("Something adventurous in the desert", ["tozeur"], ["new year"]),  # New Year trip is SOLD_OUT
    ("We want to do Umrah, what do you have?", ["umrah"], []),
    # hard filters handled by SQL
    ("Trips under 1000 DT?", ["djerba"], ["istanbul", "umrah", "dubai"]),
    ("What can I do in November?", ["november"], ["umrah"]),
    ("Can I go to the Tabarka jazz festival?", None, []),  # ARCHIVED offer: must not be sold
    # FAQ rules
    ("How much deposit do I pay?", ["30%"], []),
    ("Do I need a visa for Istanbul?", ["no"], []),
    ("My daughter is 5, does she pay full price?", ["25%"], []),
    # not in the data
    ("Do you have trips to Japan?", None, ["japan"]),
    ("Can I bring my cat?", None, []),
    # French
    ("Combien coûte le voyage à Marrakech ?", ["2600"], []),
]


def is_correct(answer, must, must_not):
    text = answer.lower().replace(",", "").replace(" dt", "")
    said_dont_know = text.startswith("i don't know")
    if any(word in text for word in must_not):
        return False
    if must is None:
        return said_dont_know
    return not said_dont_know and all(word in text for word in must)


score = 0
for i, (question, must, must_not) in enumerate(tests, start=1):
    r = ask(question)
    ok = is_correct(r["answer"], must, must_not)
    score += ok
    print(f"{'PASS' if ok else 'FAIL'}  {i}. {question}\n      {r['answer']}\n"
          f"      [{r['status']}] filters={r['filters']} sources={list(r['cited'])}\n")

print(f"Score: {score}/{len(tests)}")
