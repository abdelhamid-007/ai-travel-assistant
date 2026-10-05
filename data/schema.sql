-- Tables used by the assistant. Run once on an empty PostgreSQL database with pgvector available
-- (Neon, Supabase, or the pgvector/pgvector Docker image), then run seed.sql and `python ingest.py`.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE "OfferStatus" AS ENUM ('DRAFT', 'PUBLISHED', 'SOLD_OUT', 'ARCHIVED');

CREATE TABLE destinations (
  id          text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name        text NOT NULL,
  country     text NOT NULL,
  city        text NOT NULL,
  description text NOT NULL
);

CREATE TABLE travel_offers (
  id                text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  title             text NOT NULL,
  description       text NOT NULL,
  "destinationId"   text NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
  price             double precision NOT NULL,
  currency          text NOT NULL DEFAULT 'DT',
  duration          text NOT NULL,
  "startDate"       timestamp NOT NULL,
  "endDate"         timestamp NOT NULL,
  "maxParticipants" integer NOT NULL,
  "availableSeats"  integer NOT NULL,
  status            "OfferStatus" NOT NULL DEFAULT 'PUBLISHED'
);

-- One row per searchable text: an offer description or one FAQ answer
CREATE TABLE rag_chunks (
  id        text PRIMARY KEY,
  kind      text NOT NULL,            -- 'offer' or 'faq'
  offer_id  text REFERENCES travel_offers(id) ON DELETE CASCADE,
  content   text NOT NULL,
  embedding vector(768) NOT NULL      -- nomic-embed-text makes 768 numbers per text
);

-- Callers who asked the voice agent for a human to call them back
CREATE TABLE callback_requests (
  id         serial PRIMARY KEY,
  name       text NOT NULL,
  phone      text NOT NULL,
  interest   text,
  created_at timestamptz NOT NULL DEFAULT now()
);
