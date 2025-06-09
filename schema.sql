-- Simplified schema for betting analysis
-- Only tracking: race number, horse name, probability of win, and M/L odds

-- Drop existing indexes
DROP INDEX IF EXISTS idx_races_session;
DROP INDEX IF EXISTS idx_entries_race;

-- Drop existing tables
DROP TABLE IF EXISTS race_entries CASCADE;
DROP TABLE IF EXISTS races CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;

-- Simple sessions table
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Simple races table
CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    race_number INTEGER NOT NULL
);

-- Simple entries table - only essential fields
CREATE TABLE race_entries (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
    horse_name VARCHAR(100) NOT NULL,
    win_probability DECIMAL(5, 2) NOT NULL,
    ml_odds VARCHAR(10) NOT NULL
);

-- Basic indexes
CREATE INDEX idx_races_session ON races(session_id);
CREATE INDEX idx_entries_race ON race_entries(race_id);