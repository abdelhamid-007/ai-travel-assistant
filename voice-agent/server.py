"""Tool server for the Vapi phone agent.

During a call, Vapi's AI decides to use a tool (e.g. search_offers), sends the request here,
and reads our answer out loud. Answers are short plain sentences because they will be spoken.
Run: python -m uvicorn server:app --port 8000
"""
import json
import os

from fastapi import FastAPI, Header, HTTPException, Request
from tools import agency_policy, list_destinations, run, search_offers  # also loads .env

SECRET = os.environ.get("VAPI_SECRET")  # Vapi sends it back in the X-Vapi-Secret header

app = FastAPI()


def say_offers(args):
    request, max_price, month = args.get("request", ""), args.get("max_price"), args.get("month")
    offers = search_offers(request, max_price, month, limit=3)
    note = ""
    # The model sometimes adds a month the caller never said. Never answer "nothing" because of a month alone.
    if not offers and month:
        offers = search_offers(request, max_price, None, limit=3)
        note = "Nothing leaves in that month, but here are other dates. " if offers else ""
    if not offers:
        return "No trips match that right now."
    return note + " ".join(
        f"{o['title']} in {o['destination']}, {o['duration']}, leaving {o['start_date']}, "
        f"{o['price_dt']:g} dinars per person, {o['seats_left']} seats left."
        for o in offers
    )


def say_policy(args):
    # Keep only the answer lines ("A4: ...") so the agent doesn't read the questions aloud
    answers = [line.split(":", 1)[1].strip() for faq in agency_policy(args.get("question", ""))
               for line in faq.splitlines() if line.startswith("A")]
    return " ".join(answers)


def say_destinations(args):
    return " ".join(f"{d['destination']}: {d['trips_on_sale']} trips from {d['from_price_dt']:g} dinars."
                    for d in list_destinations())


def save_callback(args):
    run(
        "INSERT INTO callback_requests (name, phone, interest) VALUES (%s, %s, %s)",
        (args["name"], args["phone"], args.get("interest")),
    )
    return "Saved. An agent will call back during opening hours."


TOOLS = {
    "search_offers": say_offers,
    "agency_policy": say_policy,
    "list_destinations": say_destinations,
    "request_callback": save_callback,
}


@app.get("/")
def health():
    return {"ok": True, "tools": list(TOOLS)}


@app.post("/vapi/tools")
async def tool_calls(request: Request, x_vapi_secret: str | None = Header(default=None)):
    if SECRET and x_vapi_secret != SECRET:
        raise HTTPException(status_code=401, detail="bad secret")

    message = (await request.json()).get("message", {})
    results = []
    for call in message.get("toolCallList", []):
        fn = call.get("function", {})
        args = fn.get("arguments") or {}
        if isinstance(args, str):  # some versions send arguments as a JSON string
            args = json.loads(args or "{}")
        handler = TOOLS.get(fn.get("name"))
        try:
            result = handler(args) if handler else f"Unknown tool {fn.get('name')}."
        except Exception as e:  # never crash a live call; tell the agent instead
            result = f"The tool failed: {e}. Offer a callback instead."
        results.append({"toolCallId": call.get("id"), "result": result})
    return {"results": results}
