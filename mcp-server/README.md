# 2. MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets AI assistants (Claude Desktop, Claude Code, and other MCP clients) search the travel agency's **live PostgreSQL database**.

With MCP, the AI is in charge: it reads the tool descriptions, decides when to call each tool and with which arguments, and writes the answer itself. The server only returns correct, live data.

## Tools

All tools are **read-only** (`readOnlyHint`), so the AI can use them safely.

| Tool | What it does |
|---|---|
| `search_offers(request, max_price, month, limit)` | Trips on sale now, ranked by meaning, filtered by budget and departure month |
| `agency_policy(question)` | The 2 most relevant agency rules (deposit, payment, visas, children, cancellation…) |
| `list_destinations()` | Every destination with the number of trips on sale and the lowest price |

Example: asked *"Which trips under 2000 DT do you have in November?"*, Claude calls `search_offers(max_price=2000, month=11)` and answers with the real offers, dates and seats left.

## Files

| File | Purpose |
|---|---|
| [`mcp_server.py`](mcp_server.py) | The server and its 3 tools |
| [`test_mcp.py`](test_mcp.py) | Starts the server and calls every tool over the real MCP protocol |
| [`db.py`](db.py) | Database connection and embeddings |

## Run

This server reads the vectors built by the RAG chatbot's `ingest.py`, so complete the [database setup](../README.md#setup) first. Then, from this folder:

```bash
pip install -r requirements.txt
cp .env.example .env      # same DATABASE_URL as the chatbot
python test_mcp.py        # checks that all 3 tools work
```

Connect it to Claude Code:

```bash
claude mcp add travel-agency -- python /full/path/to/mcp-server/mcp_server.py
```

Or to Claude Desktop (`claude_desktop_config.json`, with Claude Desktop fully closed while editing):

```json
{
  "mcpServers": {
    "travel-agency": {
      "command": "python",
      "args": ["/full/path/to/mcp-server/mcp_server.py"]
    }
  }
}
```

Ollama must be running: the server uses `nomic-embed-text` to embed the search request.
