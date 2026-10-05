"""Creates (or updates) the Vapi assistant and points its tools at our server through ngrok.

Run after starting the server and ngrok:  python create_assistant.py
Needs VAPI_API_KEY in .env next to this file (your Vapi *private* key, from dashboard.vapi.ai -> API Keys).
"""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv, set_key

ENV = Path(__file__).parent / ".env"
load_dotenv(ENV)
API = "https://api.vapi.ai"
HEADERS = {"Authorization": f"Bearer {os.environ['VAPI_API_KEY']}"}

# ngrok's local API tells us the public https address of the tunnel
tunnels = httpx.get("http://127.0.0.1:4040/api/tunnels").json()["tunnels"]
public_url = next(t["public_url"] for t in tunnels if t["public_url"].startswith("https"))
server = {"url": f"{public_url}/vapi/tools"}
if os.environ.get("VAPI_SECRET"):
    server["secret"] = os.environ["VAPI_SECRET"]

PROMPT = """You are Salma, the phone assistant of a Tunisian travel agency.
Speak in short, friendly sentences: this is a phone call, not a chat.

Rules:
- For trips, prices, dates or seats, ALWAYS call search_offers first. Never invent a trip, price or date.
- Pass max_price ONLY if the caller said a budget, and month ONLY if the caller named a month.
  If they did not, leave those fields out completely. Never guess them.
- For deposits, payment, visas, children, cancellation or passports, call agency_policy.
- Mention at most 2 trips at a time, with price and dates. Say prices as "780 dinars".
- If you cannot answer, or the caller wants to book, offer a callback: ask their name and
  phone number, repeat the number back to confirm, then call request_callback.
- Never take card numbers or passwords over the phone."""


def tool(name, description, properties, required):
    return {
        "type": "function",
        "function": {"name": name, "description": description,
                     "parameters": {"type": "object", "properties": properties, "required": required}},
        "server": server,
    }


TOOLS = [
    tool("search_offers", "Find trips on sale now, best match first.",
         {"request": {"type": "string", "description": "What the caller wants, in their words"},
          "max_price": {"type": "number", "description": "Highest price per person in dinars. "
                                                         "Only if the caller said a budget; otherwise omit."},
          "month": {"type": "integer", "description": "Departure month 1-12. "
                                                      "Only if the caller named a month; otherwise omit."}},
         ["request"]),
    tool("agency_policy", "Agency rules: deposit, payment, cancellation, children, visas, passport, insurance.",
         {"question": {"type": "string"}}, ["question"]),
    tool("list_destinations", "All destinations with trips on sale and the cheapest price.", {}, []),
    tool("request_callback", "Save the caller's details so a human agent calls them back.",
         {"name": {"type": "string"}, "phone": {"type": "string"},
          "interest": {"type": "string", "description": "Trip or question they are interested in"}},
         ["name", "phone"]),
]

assistant = {
    "name": "Travel Agency Receptionist",
    "firstMessage": "Hello, thank you for calling. I'm Salma, the travel assistant. Where would you like to go?",
    "model": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.3,
              "messages": [{"role": "system", "content": PROMPT}], "tools": TOOLS},
}

assistant_id = os.environ.get("VAPI_ASSISTANT_ID")
if assistant_id:  # ngrok's address changes every restart, so update the existing assistant
    r = httpx.patch(f"{API}/assistant/{assistant_id}", headers=HEADERS, json=assistant)
else:
    r = httpx.post(f"{API}/assistant", headers=HEADERS, json=assistant)
r.raise_for_status()
assistant_id = r.json()["id"]
set_key(str(ENV), "VAPI_ASSISTANT_ID", assistant_id)
print(f"Assistant ready: {assistant_id}\nTools URL: {server['url']}")
print("Test it: dashboard.vapi.ai -> Assistants -> Travel Agency Receptionist -> Talk to Assistant")
