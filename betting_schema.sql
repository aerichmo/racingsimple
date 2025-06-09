-- Schema for betting analysis data

-- Drop existing tables if they exist
DROP TABLE IF EXISTS betting_recommendations CASCADE;
DROP TABLE IF EXISTS race_entries CASCADE;
DROP TABLE IF EXISTS races CASCADE;
DROP TABLE IF EXISTS analysis_sessions CASCADE;

-- Analysis sessions table
CREATE TABLE analysis_sessions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bankroll DECIMAL(10, 2) DEFAULT 1000,
    total_races INTEGER DEFAULT 0,
    total_bets INTEGER DEFAULT 0,
    total_stake DECIMAL(10, 2) DEFAULT 0,
    expected_value DECIMAL(10, 2) DEFAULT 0,
    expected_roi DECIMAL(5, 2) DEFAULT 0,
    risk_score DECIMAL(5, 2) DEFAULT 0
);

-- Races table
CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    race_number INTEGER,
    post_time VARCHAR(20),
    track_name VARCHAR(100) DEFAULT 'Unknown',
    distance DECIMAL(4, 2),
    dist_unit CHAR(1) DEFAULT 'F',
    surface CHAR(1) DEFAULT 'D',
    purse INTEGER,
    class_rating INTEGER,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Race metrics
    total_probability DECIMAL(5, 2),
    favorite_probability DECIMAL(5, 2),
    avg_edge DECIMAL(5, 2),
    max_edge DECIMAL(5, 2),
    positive_edges INTEGER,
    field_size INTEGER,
    competitiveness DECIMAL(5, 2)
);

-- Race entries table
CREATE TABLE race_entries (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
    program_number INTEGER NOT NULL,
    horse_name VARCHAR(100) NOT NULL,
    win_probability DECIMAL(5, 2) NOT NULL,
    ml_odds VARCHAR(10),
    decimal_odds DECIMAL(6, 2),
    implied_probability DECIMAL(5, 2),
    edge DECIMAL(5, 2),
    expected_value DECIMAL(5, 2),
    angles_matched INTEGER DEFAULT 0,
    value_rating DECIMAL(6, 2),
    
    UNIQUE(race_id, program_number)
);

-- Betting recommendations table
CREATE TABLE betting_recommendations (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id) ON DELETE CASCADE,
    entry_id INTEGER REFERENCES race_entries(id) ON DELETE CASCADE,
    bet_type VARCHAR(20) DEFAULT 'win',
    stake DECIMAL(10, 2) NOT NULL,
    expected_return DECIMAL(10, 2),
    confidence_score DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_races_session ON races(session_id);
CREATE INDEX idx_entries_race ON race_entries(race_id);
CREATE INDEX idx_entries_value ON race_entries(value_rating DESC);
CREATE INDEX idx_recommendations_race ON betting_recommendations(race_id);

-- View for easy querying of recommendations
CREATE VIEW betting_summary AS
SELECT 
    s.id as session_id,
    s.created_at as session_date,
    r.race_number,
    r.post_time,
    e.program_number,
    e.horse_name,
    e.win_probability,
    e.ml_odds,
    e.edge,
    e.value_rating,
    b.stake,
    b.expected_return,
    b.confidence_score
FROM analysis_sessions s
JOIN races r ON r.session_id = s.id
JOIN race_entries e ON e.race_id = r.id
JOIN betting_recommendations b ON b.entry_id = e.id
ORDER BY s.created_at DESC, r.race_number, e.value_rating DESC;