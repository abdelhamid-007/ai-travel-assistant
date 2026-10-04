# 1. RAG Chatbot

A Python travel assistant that answers customer questions **only from live offers in PostgreSQL**, with a Streamlit chat page.

## What makes it reliable

- **Hybrid search:** pgvector ranks trips by meaning ("a relaxing spa weekend near the sea" finds the thalasso package), and SQL filters by budget, month, seats left and sale status.
- **Live facts:** only trip descriptions are embedded. Price, dates and seats are read from the database at question time, so a sold-out trip disappears immediately.
- **Answer checking:** the answer model (`llama3.2:3b`) must cite its sources; a second model (`mistral`) checks the answer against them before the customer sees it.
- **Honest fallback:** questions outside the data get *"I don't know, please contact us"*.
- **Transparent:** each answer in the chat page has a *"How this answer was made"* panel with the filters, sources and any blocked draft.

## Results

[`evaluate.py`](evaluate.py) asks 12 questions (meaning search, filters, sold-out trips, agency rules, out-of-scope, French) and scores them: **11 / 12 correct**. The one failure is a data conflict that the checker blocked instead of answering wrongly.

## Files

| File | Purpose |
|---|---|
| [`assistant.py`](assistant.py) | Filter reading, hybrid search, answer, answer check |
| [`app.py`](app.py) | Streamlit chat page |
| [`evaluate.py`](evaluate.py) | Automatic test suite with a score |
| [`ingest.py`](ingest.py) | Embeds the offers and the FAQ into pgvector |
| [`db.py`](db.py) | Database connection and embeddings |

## Run

From this folder, after the [database setup](../README.md#setup):

```bash
pip install -r requirements.txt
cp .env.example .env      # put your DATABASE_URL here
python ingest.py          # builds the vectors (run again when offers change)
python evaluate.py        # runs the 12 tests
streamlit run app.py      # opens the chat page
```
