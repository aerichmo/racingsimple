# STALL10N - Smart Betting Analysis

STALL10N is a sophisticated horse racing betting analysis application that uses screenshot analysis and AI-powered recommendations to identify profitable betting opportunities.

## Features

- **Screenshot Analysis**: Upload up to 5 race screenshots showing Win Probability and M/L odds
- **OCR Processing**: Automatically extracts data from screenshots (with fallback for testing)
- **Sophisticated Betting Algorithm**: Uses Kelly Criterion and value betting principles
- **Risk Management**: Balances profitability with risk through advanced calculations
- **Database Storage**: Tracks all betting sessions, races, and recommendations
- **Real-time Analysis**: Instant betting recommendations based on edge calculations
- **Web Interface**: Modern drag-and-drop interface with detailed results display

## Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL
- **OCR**: Tesseract with pytesseract
- **Image Processing**: OpenCV and PIL
- **Analysis**: Kelly Criterion betting algorithm
- **Deployment**: Render.com

## File Structure

```
STALL10N/
├── app.py                    # Main Flask application
├── screenshot_parser.py      # OCR-based screenshot parser
├── screenshot_parser_simple.py # Fallback parser for testing
├── betting_analyzer.py       # Advanced betting analysis logic
├── database.py              # Database operations
├── betting_schema.sql       # Database schema for betting data
├── apply_betting_schema.py  # Script to apply database schema
├── requirements.txt         # Python dependencies
├── render.yaml             # Render deployment config
└── templates/              # HTML templates
```

## Database Schema

The application uses a betting-focused schema that stores:
- Analysis sessions with bankroll tracking
- Race information with statistical metrics
- Horse entries with win probabilities and odds
- Betting recommendations with stake amounts
- Expected ROI and risk calculations

## Usage

1. Navigate to the application homepage
2. Set your bankroll amount
3. Upload 1-5 screenshots of races showing Win Probability and M/L odds
4. View betting recommendations with suggested stake amounts
5. Track expected ROI and risk scores

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
createdb racingsimple

# Apply the betting schema
python apply_betting_schema.py

# Install tesseract for OCR (optional)
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr

# Run the application
python app.py
```

## Database Setup

**Important**: After deploying or setting up locally, you must apply the database schema:

```bash
# Set DATABASE_URL if needed
export DATABASE_URL="your-database-url"

# Apply the schema
python apply_betting_schema.py
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Flask secret key
- `PORT`: Server port (default: 5000)