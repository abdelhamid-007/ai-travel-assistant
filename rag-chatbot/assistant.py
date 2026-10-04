import re

from db import client, connect, embed

CHAT_MODEL = "llama3.2:3b"  # writes the answers
CHECK_MODEL = "mistral"     # checks them (see stage 3: llama3.2:3b can't judge)
DONT_KNOW = "I don't know. Please contact us on WhatsApp, Monday to Saturday, 9:00 to 18:00."

MONTHS = {
    "january": 1, "janvier": 1, "february": 2, "fevrier": 2, "février": 2, "march": 3, "mars": 3,
    "april": 4, "avril": 4, "may": 5, "mai": 5, "june": 6, "juin": 6, "july": 7, "juillet": 7,
    "august": 8, "aout": 8, "août": 8, "september": 9, "septembre": 9, "october": 10, "octobre": 10,
    "november": 11, "novembre": 11, "december": 12, "decembre": 12, "décembre": 12,
}

conn = connect()


# 1. Read hard facts from the question with simple rules. Vectors are bad at "under 2000 DT".
def read_filters(question):
    q = question.lower()
    price = re.search(r"(?:under|below|less than|max(?:imum)?|moins de|budget(?: of)?)\s*(\d[\d\s,.]*\d|\d)", q)
    max_price = int(re.sub(r"\D", "", price.group(1))) if price else None
    month = next((n for name, n in MONTHS.items() if re.search(rf"\b{name}\b", q)), None)
    return {"max_price": max_price, "month": month}


# 2. Hybrid search: SQL filters on live data + vector ranking by meaning
def search(question, filters):
    vec = embed([question], "search_query")[0]
    offers = conn.execute("""
        SELECT o.title, d.city, d.country, o.duration, o."startDate"::date, o."endDate"::date,
               o.price, o.currency, o."availableSeats", o.description
        FROM rag_chunks c
        JOIN travel_offers o ON o.id = c.offer_id
        JOIN destinations d ON d.id = o."destinationId"
        WHERE o.status = 'PUBLISHED' AND o."availableSeats" > 0 AND o."startDate" > now()
          AND (%(max_price)s::float IS NULL OR o.price <= %(max_price)s)
          AND (%(month)s::int IS NULL OR extract(month FROM o."startDate") = %(month)s)
        ORDER BY c.embedding <=> %(vec)s
        LIMIT 3
    """, {**filters, "vec": vec}).fetchall()
    faqs = conn.execute(
        "SELECT content FROM rag_chunks WHERE kind = 'faq' ORDER BY embedding <=> %s LIMIT 2", (vec,)
    ).fetchall()

    blocks = {}
    for i, (title, city, country, duration, start, end, price, cur, seats, descr) in enumerate(offers, 1):
        blocks[f"O{i}"] = (f"Offer: {title} ({city}, {country}). {duration}, from {start} to {end}. "
                           f"Price: {price:g} {cur} per person. Seats left: {seats}. {descr}")
    for i, (content,) in enumerate(faqs, 1):
        blocks[f"F{i}"] = content
    return blocks


def chat(system, user, model=CHAT_MODEL):
    r = client.chat.completions.create(
        model=model, temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return r.choices[0].message.content.strip()


ANSWER_RULES = (
    "You are the travel assistant of a Tunisian travel agency. Use ONLY the context. "
    "Each context block starts with its label in brackets, like [O1] for an offer or [F2] for a FAQ answer. "
    "The offers in the context are the only trips available: never mention other trips, prices or dates. "
    "If the context gives a rule (deposit, child age, visa, cancellation), apply it to the customer's situation. "
    "Answer in the customer's language, in 2 to 4 short sentences. "
    "End with the labels you used, like (source: O1, F2). "
    f"If the context does not answer the question, reply exactly: {DONT_KNOW}"
)


def is_supported(context, question, answer):
    verdict = chat(
        "You check answers for mistakes. Reply with only YES or NO.",
        f"Context:\n{context}\n\nCustomer question:\n{question}\n\nAnswer:\n{answer}\n\n"
        "Does the context support the answer? Details repeated from the customer question are fine. "
        "Reply NO only if the answer states a trip, price, date or rule that the context does not mention.",
        model=CHECK_MODEL,
    )
    return verdict.upper().startswith("YES")


# 3. Answer, then check the answer against the blocks it cites
def ask(question):
    filters = read_filters(question)
    blocks = search(question, filters)
    context = "\n\n".join(f"[{label}] {text}" for label, text in blocks.items())

    answer = draft = chat(ANSWER_RULES, f"Context:\n{context}\n\nQuestion: {question}")
    cited = [label for label in re.findall(r"\b([OF]\d+)\b", answer) if label in blocks]
    # Small models often forget a label. An offer whose title is in the answer was used, so check it too.
    for label, text in blocks.items():
        title = re.match(r"Offer: (.+?) \(", text)
        if title and title.group(1).lower() in answer.lower() and label not in cited:
            cited.append(label)

    if "don't know" in answer.lower() or "je ne sais pas" in answer.lower():
        status = "dont_know"
        answer = DONT_KNOW
    elif not cited:
        status, answer = "blocked_no_source", f"{DONT_KNOW}"
    elif not is_supported("\n\n".join(blocks[c] for c in cited), question, answer):
        status, answer = "blocked_unsupported", f"{DONT_KNOW}"
    else:
        status = "ok"

    return {"answer": answer, "draft": draft, "status": status, "filters": filters,
            "cited": {c: blocks[c] for c in cited}, "context": blocks}


if __name__ == "__main__":
    while True:
        try:
            question = input("Your question: ").strip()
        except (KeyboardInterrupt, EOFError):
            question = ""
        if not question:
            break
        result = ask(question)
        print(f"Answer: {result['answer']}\n   [{result['status']}] filters={result['filters']} "
              f"sources={list(result['cited'])}\n")
