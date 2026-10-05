"""Data tools for the voice agent: search live trips and agency rules in PostgreSQL + pgvector.

Embeddings come from Ollama (nomic-embed-text) running on this PC, so Ollama must be running.
"""
import os
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from pgvector.psycopg import register_vector

load_dotenv(Path(__file__).parent / ".env")

ollama = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

_conn = None


def _connect():
    # prepare_threshold=None: Neon's pooler does not support prepared statements
    # autocommit=True: every statement is saved immediately (no hidden transaction rolled back at exit)
    conn = psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None, autocommit=True)
    register_vector(conn)
    return conn


def run(sql, params=None):
    """Run a query, reconnecting once if Neon closed the connection while it was idle.

    Neon drops idle connections (and suspends its compute after a few minutes without queries), so a
    connection opened when the server started is usually dead by the time a call comes in.
    """
    global _conn
    for attempt in (1, 2):
        try:
            if _conn is None or _conn.closed:
                _conn = _connect()
            return _conn.execute(sql, params)
        except (psycopg.OperationalError, psycopg.InterfaceError):
            _conn = None
            if attempt == 2:
                raise


def embed(text):
    r = ollama.embeddings.create(model="nomic-embed-text", input=[f"search_query: {text}"])
    return np.array(r.data[0].embedding)


def search_offers(request, max_price=None, month=None, limit=3):
    """Trips on sale now (published, seats left, not departed), best match first."""
    rows = run("""
        SELECT o.title, d.city, d.country, o.duration, o."startDate"::date, o.price, o."availableSeats"
        FROM rag_chunks c
        JOIN travel_offers o ON o.id = c.offer_id
        JOIN destinations d ON d.id = o."destinationId"
        WHERE o.status = 'PUBLISHED' AND o."availableSeats" > 0 AND o."startDate" > now()
          AND (%(max_price)s::float IS NULL OR o.price <= %(max_price)s)
          AND (%(month)s::int IS NULL OR extract(month FROM o."startDate") = %(month)s)
        ORDER BY c.embedding <=> %(vec)s
        LIMIT %(limit)s
    """, {"vec": embed(request), "max_price": max_price, "month": month, "limit": limit}).fetchall()
    return [{"title": t, "destination": f"{city}, {country}", "duration": dur, "start_date": str(s),
             "price_dt": p, "seats_left": seats} for t, city, country, dur, s, p, seats in rows]


def agency_policy(question):
    """The 2 FAQ entries closest to the question."""
    rows = run(
        "SELECT content FROM rag_chunks WHERE kind = 'faq' ORDER BY embedding <=> %s LIMIT 2", (embed(question),)
    ).fetchall()
    return [content for (content,) in rows]


def list_destinations():
    rows = run("""
        SELECT d.city, d.country, count(o.id), min(o.price)
        FROM destinations d JOIN travel_offers o ON o."destinationId" = d.id
        WHERE o.status = 'PUBLISHED' AND o."availableSeats" > 0 AND o."startDate" > now()
        GROUP BY d.city, d.country ORDER BY d.country, d.city
    """).fetchall()
    return [{"destination": f"{c}, {k}", "trips_on_sale": n, "from_price_dt": p} for c, k, n, p in rows]
