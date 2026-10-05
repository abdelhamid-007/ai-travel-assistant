# 4. AI Voice Agent (Vapi)

**Salma** answers phone calls for the travel agency. She searches live trips in PostgreSQL + pgvector, explains agency rules, and saves callback requests for a human agent.

🎬 **Demo:** [`demo/voice_agent_demo.mp4`](demo/voice_agent_demo.mp4) — a real call, agent audio only, with the caller's question as a caption.

```
Caller → Vapi (speech-to-text → GPT-4o-mini → text-to-speech)
              │ tool call (HTTPS + shared secret)
              ▼
   ngrok → server.py (FastAPI) → tools.py → PostgreSQL + pgvector, Ollama embeddings
```

## Tools

| Tool | What it does |
|---|---|
| `search_offers(request, max_price, month)` | Trips on sale now, best match first, with optional budget and month |
| `agency_policy(question)` | Deposit, payment, visa, children, cancellation rules |
| `list_destinations()` | Destinations with trips on sale and the cheapest price |
| `request_callback(name, phone, interest)` | Saves the caller in `callback_requests` for a human callback |

Answers are short plain sentences, because they are spoken.

## Results

Tested in real calls (Vapi web calls):

- One 5-minute call: **18 caller questions, 8 live database lookups**, all 3 lookup tools used
- Tool response time: **0.4–0.6 s** (about 6 s on the first call after the database sleeps)
- Prices and dates always come from the database

## Reliability fixes found by testing

Testing real calls found two problems that a demo would have hidden:

| Problem | Fix |
|---|---|
| The server opened one database connection at start. Neon closes idle connections, so after a few minutes **every tool failed**. | `tools.run()` reconnects once when the connection was closed. |
| GPT-4o-mini **invented a month** the caller never said (`month: 1`), so "Tunisia under 2000 dinars" returned no trips. | The prompt and tool schema say to send a month or budget only if the caller said it, **and** the server retries without the month instead of answering "nothing". |

## Security

- Every tool call must carry the `X-Vapi-Secret` header; anything else gets **401**.
- Tools are read-only except `request_callback`, which only inserts a row.
- The agent is told never to take card numbers or passwords by phone.
- Keys stay in `.env` (never committed).

## Files

| File | Purpose |
|---|---|
| [`server.py`](server.py) | Receives Vapi tool calls, checks the secret, answers in spoken sentences |
| [`tools.py`](tools.py) | Database search: trips (vector + SQL filters), rules, destinations; auto-reconnect |
| [`create_assistant.py`](create_assistant.py) | Creates or updates the Vapi assistant: prompt, voice, tools, server URL |
| [`demo/make_video.py`](demo/make_video.py) | Builds the demo video from an agent-only recording (title, captions, waveform) |

## Run

Complete the [database setup](../README.md#setup) first (the `callback_requests` table is in `data/schema.sql`). Ollama must be running with `nomic-embed-text`.

```bash
cd voice-agent
pip install -r requirements.txt
cp .env.example .env                                   # fill in DATABASE_URL, VAPI_API_KEY, VAPI_SECRET

python -m uvicorn server:app --port 8000 --reload      # terminal 1
ngrok http 8000                                        # terminal 2
python create_assistant.py                             # terminal 3 (again after the ngrok URL changes)
```

Then: dashboard.vapi.ai → Assistants → **Travel Agency Receptionist** → **Talk to Assistant**.
