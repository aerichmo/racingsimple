# StatPal API - Complete Available Data Documentation

## Overview
This document lists EVERY data point actually available from the StatPal Horse Racing API based on real API responses.

## API Endpoints
- **Live Races**: `/live/{country}` (uk, usa)
- **Authentication**: Query parameter `?access_key=YOUR_KEY`

## Available Data Points

### 1. Venue/Track Level Data
- `date` - Race date (format: "17.06.2025")
- `going` - Track condition (e.g., "Good to firm-good in places", "Fast")
- `id` - Venue ID
- `name` - Venue name (e.g., "Ascot", "Prairie Meadows")

### 2. Race Level Data
- `id` - Unique race identifier
- `name` - Full race name (e.g., "Race 1 Queen Anne Stakes")
- `class` - Race class (often empty for US races)
- `datetime` - Full datetime (format: "16.06.2025 13:30")
- `time` / `offat` - Post time (format: "14:30")
- `distance` - Race distance (e.g., "1m (Str)", "6f")
- `status` - Race status (usually empty for upcoming)
- `odds` - Nested odds data from multiple bookmakers (UK only)
- `results` - Race results (null for upcoming races)
- `wagers` - Wager data (null for upcoming races)

### 3. Horse/Runner Data

#### Basic Information
- `id` - Unique horse identifier
- `name` - Horse name
- `number` - Program/saddle cloth number
- `stall` - Starting gate position (UK races, empty for US)
- `age` - Horse age (UK races, empty for US)
- `gender` - Gender and breeding info (e.g., "b h Quality Road")

#### Weight Information
- `wgt` - Weight in stones-pounds format (e.g., "58" or "9-2")
- `wgt_lbs` - Weight in pounds (e.g., "128")

#### Connections
- `jockey` - Jockey name (text only)
- `jockey_id` - Jockey unique identifier
- `trainer` - Trainer name (text only)
- `trainer_id` - Trainer unique identifier

#### Performance
- `rating` - Official rating (UK races, empty for US)
- `distance` - Distance preference (usually empty)

### 4. Form Data (UK races only)

The `recent_form` object contains sections with statistical breakdowns:

#### Race Record
- **All Flat Races**: runs, wins, places, win_pct
- **Flat**: runs, wins, places, win_pct
- **Other surface types** when applicable

#### Conditions
- **Course and Distance**: runs, wins, places, win_pct
- **Course**: runs, wins, places, win_pct
- **Distance**: runs, wins, places, win_pct
- **Similar Going**: runs, wins, places, win_pct

#### Headgear
- **tv** (tongue strap): runs, wins, places, win_pct
- **visor**: runs, wins, places, win_pct
- Other equipment as applicable

#### Class Rating
- **Class 1/2/3/etc**: runs, wins, places, win_pct
- **This Handicap**: runs, wins, places, win_pct

#### Connections
- **[Jockey Name]**: runs, wins, places, win_pct
- **[Trainer Name]**: runs, wins, places, win_pct

### 5. Odds Data (UK races only)

For each horse, multiple bookmaker odds including:
- `bookmaker_id` - Bookmaker identifier
- `name` - Bookmaker name (Bet365, William Hill, etc.)
- `odd` - Current decimal odds
- `eachway` - Each way terms (e.g., "3-1/5")
- `odd_id` - Unique odds identifier

### 6. Data Differences: UK vs US

#### UK Races Have:
- Age data
- Official ratings
- Comprehensive form data with multiple sections
- Starting stall positions
- Live odds from multiple bookmakers
- Gender/breeding information

#### US Races Have:
- Basic horse/jockey/trainer names
- Program numbers
- Weight in pounds
- Limited or no form data
- No ratings
- No stall positions
- No live odds

## What's NOT Available

### Critical Missing Data:
1. **Past Performance Lines** - No individual race history
2. **Speed Figures** - No Beyer, Timeform, or other speed ratings
3. **Fractional/Sectional Times** - No pace data
4. **Workout Data** - No training information
5. **Equipment Changes** - No blinkers on/off notifications
6. **Medication** - No Lasix/Bute information
7. **Track Bias** - No rail position or bias data
8. **Weather** - No temperature or track moisture
9. **Lifetime Earnings** - No purse money data
10. **Pedigree** - Limited breeding info (UK only, partial)
11. **Days Since Last Race** - No layoff information
12. **Previous Odds** - No historical odds movements
13. **Jockey/Trainer Statistics** - Only career stats with specific horse
14. **Head-to-Head Records** - No previous meetings data
15. **Track Records** - No fastest times data

## Example API Response Structure

```json
{
  "scores": {
    "tournament": [
      {
        "date": "17.06.2025",
        "going": "Good to firm",
        "id": "2779",
        "name": "Ascot",
        "race": [
          {
            "id": "1060678",
            "name": "Race 1 Queen Anne Stakes",
            "distance": "1m (Str)",
            "time": "14:30",
            "runners": {
              "horse": [
                {
                  "id": "234933",
                  "name": "Cairo",
                  "number": "1",
                  "stall": "11",
                  "age": "5",
                  "rating": "111",
                  "jockey": "S De Sousa",
                  "trainer": "Alice Haynes",
                  "wgt": "58",
                  "recent_form": {
                    "section": [
                      {
                        "name": "race record",
                        "stat": [
                          {
                            "name": "All Flat Races",
                            "runs": "20",
                            "wins": "3",
                            "places": "10",
                            "win_pct": "15%"
                          }
                        ]
                      }
                    ]
                  }
                }
              ]
            }
          }
        ]
      }
    ]
  }
}
```

## Conclusion

StatPal provides basic race card information with some form statistics for UK races. The API is designed for displaying today's races and basic betting information, not for comprehensive handicapping analysis. US data is particularly limited, lacking even basic form statistics that UK races provide.