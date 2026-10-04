# n8n Workflow: Travel Assistant (RAG)

The RAG chatbot rebuilt as an n8n workflow. Every step is a node that can be opened, tested and edited without writing Python.

```
When chat message received ─┐
                            ├─► Read filters ─► Embed question ─► Hybrid search ─► Build prompt ─► Write answer ─► Reply
Test button ─► Test question┘                   (Ollama)          (pgvector)                      (Ollama)
```

| Node | Type | What it does |
|---|---|---|
| Read filters | Code | Finds a budget ("under 1000") and a month in the question |
| Embed question | HTTP Request | Gets the question's vector from Ollama (`nomic-embed-text`) |
| Hybrid search | Postgres | Ranks offers by meaning, keeps only trips on sale that match the filters, adds the 2 closest FAQ answers |
| Build prompt | Code | Labels the results `[O1]`, `[F1]` and adds the answer rules |
| Write answer | HTTP Request | Asks `llama3.2:3b` for the answer |
| Reply | Code | Sends the answer to the chat window |

## Import

1. Run n8n (for example `docker run -p 5678:5678 docker.n8n.io/n8nio/n8n`).
2. In n8n: **Workflows → Import from file** → `travel_assistant.json`.
3. Open **Hybrid search (pgvector)** and create a **Postgres** credential for your database, with **SSL: Require** for Neon.
4. If n8n runs in Docker, Ollama is reached at `http://host.docker.internal:11434` (already set). Otherwise change it to `http://localhost:11434` in both HTTP Request nodes.
5. Click **Open chat** and ask *"Trips under 1000 DT?"*, or click **Execute workflow** to run the test question.

The database must already contain the tables and vectors: see the main [README](../README.md#setup).
