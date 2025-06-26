#!/bin/bash
# ST0CK Automation Startup Script

# Change to project directory
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Export environment variables
export DATABASE_URL="${DATABASE_URL:-postgresql://localhost/stock_db}"
export RACE_API_KEY="${RACE_API_KEY:-your_api_key_here}"
export RACE_API_URL="${RACE_API_URL:-https://api.horseracing.com/v1}"

# Start automation with restart on failure
while true; do
    echo "Starting ST0CK automation at $(date)"
    python3 automation_runner.py
    
    # If the script exits, wait 60 seconds and restart
    echo "Automation stopped at $(date). Restarting in 60 seconds..."
    sleep 60
done