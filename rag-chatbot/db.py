import os
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from pgvector.psycopg import register_vector

load_dotenv(Path(__file__).parent / ".env")  # works from any folder, e.g. when Claude starts the MCP server

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
EMBED_MODEL = "nomic-embed-text"


def connect():
    # prepare_threshold=None: Neon's pooler does not support prepared statements
    # autocommit=True: each statement saves immediately, and `with conn.transaction()` is a real
    # transaction. Without it, psycopg opens a hidden transaction that is rolled back at exit.
    conn = psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None, autocommit=True)
    register_vector(conn)  # lets Python send and read the vector type
    return conn


def embed(texts, kind):
    """kind is 'search_document' when storing and 'search_query' when searching (nomic needs it)."""
    r = client.embeddings.create(model=EMBED_MODEL, input=[f"{kind}: {t}" for t in texts])
    return [np.array(d.embedding) for d in r.data]
