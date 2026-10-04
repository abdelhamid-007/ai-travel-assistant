"""Loads every travel offer and the agency FAQ into the rag_chunks table. Run it again after offers change."""
import re
from pathlib import Path

from db import connect, embed

FAQ_FILE = Path(__file__).parent.parent / "data" / "agency_faq.txt"  # shared by all three projects

conn = connect()

# 1. Offers: embed only what describes the trip. Price, dates and seats change, so they are
#    read live from travel_offers at question time instead of being frozen in the vector text.
offers = conn.execute("""
    SELECT o.id, o.title, o.description, o.duration, d.name, d.city, d.country, d.description
    FROM travel_offers o JOIN destinations d ON d.id = o."destinationId"
""").fetchall()

offer_rows = []
for offer_id, title, descr, duration, dest, city, country, dest_descr in offers:
    text = f"{title}. Trip to {city}, {country} ({dest}). {duration}. {descr} About the destination: {dest_descr}"
    offer_rows.append((f"offer-{offer_id}", "offer", offer_id, text))

# 2. FAQ: one chunk per question + answer, so an answer is never cut away from its question
faq = FAQ_FILE.read_text(encoding="utf-8").strip()
faq_rows = []
for part in re.split(r"\n(?=Q\d+:)", faq):
    section = re.match(r"(Q\d+):", part).group(1)
    faq_rows.append((f"faq-{section}", "faq", None, part.strip()))

rows = offer_rows + faq_rows
vectors = embed([r[3] for r in rows], "search_document")

with conn.transaction():
    conn.execute("DELETE FROM rag_chunks")  # rebuild from scratch so deleted offers disappear too
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO rag_chunks (id, kind, offer_id, content, embedding) VALUES (%s, %s, %s, %s, %s)",
            [(*row, vec) for row, vec in zip(rows, vectors, strict=True)],
        )

print(f"Stored {len(offer_rows)} offers and {len(faq_rows)} FAQ chunks")
