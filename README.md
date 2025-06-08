# STALL10N - Horse Racing XML Analysis

STALL10N Simple is a horse racing analysis application that processes TrackMaster Plus XML data files to provide racing recommendations.

## Features

- **XML Data Processing**: Parses TrackMaster Plus XML files containing comprehensive race and horse data
- **ZIP File Support**: Accepts .zip files containing XML data
- **Comprehensive Analysis**: Analyzes horses based on speed, class, jockey, and trainer performance
- **Database Storage**: Stores all XML data fields including:
  - Race information (track, distance, conditions, purse)
  - Horse details (breeding, physical attributes, ownership)
  - Performance metrics (speed figures, power ratings, class ratings)
  - Statistics (horse, jockey, trainer, sire, dam)
  - Workout history
  - Past performance data
- **Web Interface**: Clean, unified interface for uploading files and viewing analysis

## Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL
- **Parser**: XML (ElementTree)
- **Analysis**: Custom scoring algorithm
- **Deployment**: Render.com

## File Structure

```
STALL10N/
├── app.py              # Main Flask application
├── xml_parser.py       # XML parser for TrackMaster Plus format
├── database.py         # Database operations
├── analyzer.py         # Race analysis logic
├── schema.sql          # Complete database schema
├── requirements.txt    # Python dependencies
├── render.yaml         # Render deployment config
├── templates/          # HTML templates
└── static/            # Static assets
```

## Database Schema

The application uses a comprehensive schema that stores:
- Races with all track and condition details
- Entries with 100+ fields per horse
- Horse, jockey, and trainer statistics
- Sire and dam breeding statistics
- Workout history
- Complete past performance data

## Usage

1. Navigate to `/stall10nsimple`
2. Select a date for the races
3. Upload an XML or ZIP file containing TrackMaster Plus data
4. View analysis results with recommendations

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
createdb racingsimple

# Run the application
python app.py
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Flask secret key
- `PORT`: Server port (default: 5000)