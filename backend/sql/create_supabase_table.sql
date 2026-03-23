-- Supabase SQL: create table for storing predictions
-- Run in Supabase SQL editor or psql with your Supabase DB URL

CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NULL,
    symbol TEXT NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    prediction_days INTEGER NOT NULL,
    predicted_prices JSONB NOT NULL,
    model_weights JSONB NULL,
    confidence FLOAT NULL,
    metadata JSONB NULL
);

-- Index for quick symbol lookup
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol);
