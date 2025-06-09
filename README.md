# STALL10N - Race Data Logger

STALL10N is a simple horse racing data logger that extracts and stores race information from screenshots.

## Features

- **Screenshot Upload**: Upload up to 5 race screenshots at once
- **Data Extraction**: Logs race number, horse name, win probability, and M/L odds
- **Simple Storage**: Minimal database schema focused on essential data
- **Web Interface**: Clean drag-and-drop interface for easy uploads

## Data Logged

For each race, the system logs:
- Race number
- Horse name
- Probability of win (%)
- Morning Line (M/L) odds

## Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL
- **Parser**: Simple parser with hardcoded test data (OCR-ready)
- **Deployment**: Render.com

## File Structure

```
STALL10N/
├── app.py                    # Main Flask application
├── screenshot_parser.py      # OCR-based screenshot parser
├── screenshot_parser_simple.py # Fallback parser for testing
├── database.py              # Simple database operations
├── schema.sql              # Minimal database schema
├── apply_schema.py         # Script to apply database schema
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
└── templates/             # HTML templates
```

## Database Schema

The application uses a minimal schema with just 3 tables:
- `sessions` - Tracks upload sessions
- `races` - Stores race numbers
- `race_entries` - Stores horse data (name, win %, M/L odds)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
createdb racingsimple

# Apply the schema
python apply_schema.py

# Run the application
python app.py
```

## Database Setup

After deploying or setting up locally, apply the database schema:

```bash
# Set DATABASE_URL if needed
export DATABASE_URL="your-database-url"

# Apply the schema
python apply_schema.py
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Flask secret key
- `PORT`: Server port (default: 5000)