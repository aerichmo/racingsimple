-- Add results fields to entries table
ALTER TABLE entries 
ADD COLUMN IF NOT EXISTS finish_position INT,
ADD COLUMN IF NOT EXISTS final_odds VARCHAR(20),
ADD COLUMN IF NOT EXISTS win_payoff DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS place_payoff DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS show_payoff DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS result_scraped_at TIMESTAMP;

-- Add index for finish position queries
CREATE INDEX IF NOT EXISTS idx_entries_finish ON entries(race_id, finish_position);

-- Add results scraping status to races
ALTER TABLE races
ADD COLUMN IF NOT EXISTS results_scraped BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS results_scraped_at TIMESTAMP;