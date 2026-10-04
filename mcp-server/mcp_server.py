"""MCP server: lets AI assistants (Claude Desktop, Claude Code, ChatGPT...) search the agency's live offers.

The AI decides when to call these tools and writes the answer itself. Our job is only to return
correct, live data. Never print() here: stdout is the channel the AI reads messages from.
"""
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from db import connect, embed

server = MCPServer(
    name="travel-agency",
    instructions=(
        "Tools for a Tunisian travel agency. Use search_offers for trips, prices, dates and seats, "
        "and agency_policy for rules (deposit, visa, children, cancellation). Only recommend offers "
        "returned by search_offers: they are the only trips on sale. Prices are in Tunisian dinars (DT)."
    ),
)
conn = connect()
READ_ONLY = ToolAnnotations(readOnlyHint=True)


@server.tool(annotations=READ_ONLY)
def search_offers(request: str, max_price: float | None = None, month: int | None = None, limit: int = 5) -> list[dict]:
    """Find trips that are on sale now, best match first.

    Args:
        request: what the customer wants, in their words, e.g. "relaxing beach holiday with kids".
        max_price: highest price per person in DT, if the customer gave a budget.
        month: departure month 1-12, if the customer gave one.
        limit: how many offers to return (1-10).
    """
    vec = embed([request], "search_query")[0]
    rows = conn.execute("""
        SELECT o.title, d.city, d.country, o.duration, o."startDate"::date, o."endDate"::date,
               o.price, o."availableSeats", o.description, 1 - (c.embedding <=> %(vec)s) AS match
        FROM rag_chunks c
        JOIN travel_offers o ON o.id = c.offer_id
        JOIN destinations d ON d.id = o."destinationId"
        WHERE o.status = 'PUBLISHED' AND o."availableSeats" > 0 AND o."startDate" > now()
          AND (%(max_price)s::float IS NULL OR o.price <= %(max_price)s)
          AND (%(month)s::int IS NULL OR extract(month FROM o."startDate") = %(month)s)
        ORDER BY c.embedding <=> %(vec)s
        LIMIT %(limit)s
    """, {"vec": vec, "max_price": max_price, "month": month, "limit": max(1, min(limit, 10))}).fetchall()
    return [
        {"title": t, "destination": f"{city}, {country}", "duration": dur, "start_date": str(s),
         "end_date": str(e), "price_dt": p, "seats_left": seats, "description": descr, "match": round(m, 3)}
        for t, city, country, dur, s, e, p, seats, descr, m in rows
    ]


@server.tool(annotations=READ_ONLY)
def agency_policy(question: str) -> list[str]:
    """Look up agency rules: booking, deposit, payment, cancellation, children, visas, passport,
    single rooms, insurance, groups, airports, contact. Returns the 2 most relevant FAQ answers."""
    vec = embed([question], "search_query")[0]
    rows = conn.execute(
        "SELECT content FROM rag_chunks WHERE kind = 'faq' ORDER BY embedding <=> %s LIMIT 2", (vec,)
    ).fetchall()
    return [content for (content,) in rows]


@server.tool(annotations=READ_ONLY)
def list_destinations() -> list[dict]:
    """List every destination with the number of trips on sale and the cheapest price."""
    rows = conn.execute("""
        SELECT d.city, d.country, count(o.id), min(o.price)
        FROM destinations d
        JOIN travel_offers o ON o."destinationId" = d.id
        WHERE o.status = 'PUBLISHED' AND o."availableSeats" > 0 AND o."startDate" > now()
        GROUP BY d.city, d.country ORDER BY d.country, d.city
    """).fetchall()
    return [{"destination": f"{c}, {k}", "trips_on_sale": n, "from_price_dt": p} for c, k, n, p in rows]


if __name__ == "__main__":
    server.run("stdio")
