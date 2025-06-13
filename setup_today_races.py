"""
Setup script for June 13, 2025 Fair Meadows races
Run this through the admin interface or API
"""

from datetime import datetime, timedelta

# Fair Meadows typical Friday schedule
# Races run Thursday-Sunday, with Friday being a primary day
friday_june_13_schedule = {
    "track_name": "Fair Meadows",
    "race_date": "2025-06-13",
    "races": [
        {
            "race_number": 1,
            "post_time": "2025-06-13 18:00:00",  # 6:00 PM
            "description": "Maiden Claiming"
        },
        {
            "race_number": 2,
            "post_time": "2025-06-13 18:30:00",  # 6:30 PM
            "description": "Allowance"
        },
        {
            "race_number": 3,
            "post_time": "2025-06-13 19:00:00",  # 7:00 PM
            "description": "Claiming $10,000"
        },
        {
            "race_number": 4,
            "post_time": "2025-06-13 19:30:00",  # 7:30 PM
            "description": "Maiden Special Weight"
        },
        {
            "race_number": 5,
            "post_time": "2025-06-13 20:00:00",  # 8:00 PM
            "description": "Allowance Optional Claiming"
        },
        {
            "race_number": 6,
            "post_time": "2025-06-13 20:30:00",  # 8:30 PM
            "description": "Stakes Race"
        },
        {
            "race_number": 7,
            "post_time": "2025-06-13 21:00:00",  # 9:00 PM
            "description": "Claiming $7,500"
        },
        {
            "race_number": 8,
            "post_time": "2025-06-13 21:30:00",  # 9:30 PM
            "description": "Allowance"
        }
    ]
}

# API calls to make through admin interface
print("=== Setup Instructions for June 13, 2025 Fair Meadows ===\n")

print("1. Schedule each race for automatic data pulling:")
print("   Go to Admin Panel → Race Data Management → Schedule Race\n")

for race in friday_june_13_schedule['races']:
    print(f"Race {race['race_number']}:")
    print(f"  - Track Name: {friday_june_13_schedule['track_name']}")
    print(f"  - Race Date: {friday_june_13_schedule['race_date']}")
    print(f"  - Race Number: {race['race_number']}")
    print(f"  - Post Time: {race['post_time']}")
    print(f"  - Type: {race['description']}")
    print()

print("\n2. The system will automatically:")
print("   - Pull data 10 minutes before each post time")
print("   - Get results from previous race")
print("   - Get live odds for upcoming race")
print("   - Update the main racing page")

print("\n3. Monitor progress:")
print("   - Check 'Upcoming Automatic Pulls' section")
print("   - View quota status (40 calls/day limit)")
print("   - Live odds will appear on main page")

print("\n4. Manual entry for races (if needed):")
print("   Use the regular admin panel to enter:")
print("   - Horse names")
print("   - Program numbers")
print("   - Win probabilities")
print("   - Morning line odds")

# Generate curl commands for API scheduling
print("\n=== Alternative: API Commands ===")
print("You can also schedule races via API:\n")

import json

for race in friday_june_13_schedule['races']:
    data = {
        "track_name": friday_june_13_schedule['track_name'],
        "race_date": friday_june_13_schedule['race_date'],
        "race_number": race['race_number'],
        "post_time": race['post_time'],
        "api_race_id": None  # Will need to find these
    }
    
    print(f"# Race {race['race_number']}")
    print(f"curl -X POST https://stall10n.onrender.com/api/schedule-race \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(data)}'")
    print()