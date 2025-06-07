# Racing Simple - Python Version

Automated horse racing data scraper for Equibase entries with odds tracking.

## Features

- Scrapes race data from Equibase daily at 8am (Wed-Sat only)
- Captures Morning Line (M/L) odds at 8am on race day
- Captures Live odds 5 minutes before post time
- Stores all data in PostgreSQL database with historical tracking
- Stops automatically after July 20, 2025
- Comprehensive SQL queries for data analysis

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create PostgreSQL database and run schema:
   ```bash
   python database.py  # Creates tables
   ```

3. Set environment variable:
   ```bash
   export DATABASE_URL=postgresql://user:password@localhost:5432/racingsimple
   ```

4. Test scraper:
   ```bash
   python scraper.py
   ```

## Deployment on Render

1. Push code to GitHub
2. Create new project on Render
3. Select "Blueprint" and connect your repo
4. Render will automatically:
   - Create a PostgreSQL database
   - Set up a cron job to run at 8am daily
   - Configure all environment variables

## Important Notes

**The scraper CSS selectors need to be updated!** 
- Visit https://www.equibase.com/static/entry/FMT060725USA-EQB.html
- Inspect the HTML structure
- Update selectors in `scraper.py` `parse_race_data()` method

## Analysis Queries

See `analysis_queries.sql` for pre-built queries including:
- Daily race summaries
- Jockey/trainer statistics
- Track analysis
- Horse history tracking

## Manual Usage

```python
from scraper import EquibaseScraper
from database import Database

# Run scraper
scraper = EquibaseScraper(os.environ['DATABASE_URL'])
scraper.run_daily_sync()

# Query data
db = Database()
races = db.get_races_by_date('2025-06-07')
jockey_stats = db.get_jockey_statistics()
```