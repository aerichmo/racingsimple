#!/usr/bin/env python3
"""
Pull Fair Meadows (Prairie Meadows) race data from StatPal API
Designed to run at 8am on race day
"""
import os
import sys
import json
import argparse
from datetime import datetime, date
from statpal_service import StatPalService

def pull_fair_meadows_data(target_date=None):
    """
    Pull Fair Meadows race data for specified date
    
    Args:
        target_date: Date string in YYYY-MM-DD format, defaults to today
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Parse target date
    if target_date:
        try:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"❌ Invalid date format: {target_date}. Use YYYY-MM-DD")
            return False
    else:
        date_obj = date.today()
    
    # Check if trying to pull future data
    if date_obj > date.today():
        print(f"❌ Cannot pull data for future date: {date_obj}")
        print("   StatPal API only provides current day data")
        return False
    
    # Check if trying to pull past data
    if date_obj < date.today():
        print(f"⚠️  Warning: Attempting to pull past data for {date_obj}")
        print("   StatPal API only provides current day data")
    
    print(f"📅 Pulling Fair Meadows data for: {date_obj}")
    
    # Initialize service
    try:
        service = StatPalService()
    except Exception as e:
        print(f"❌ Failed to initialize StatPal service: {e}")
        return False
    
    # Get US races
    print("🔄 Fetching US racing data...")
    us_races = service.get_live_races('us')
    
    if not us_races:
        print("❌ No US races found")
        return False
    
    # Filter for Prairie Meadows (Fair Meadows)
    fair_meadows_races = []
    venues_found = set()
    
    for race in us_races:
        venue = race['venue_name']
        venues_found.add(venue)
        
        # Look for Prairie Meadows or Fair Meadows
        if 'prairie meadows' in venue.lower() or 'fair meadows' in venue.lower():
            # Get full race details
            details = service.get_race_details(race['id'], 'us')
            if details:
                race_data = {
                    "race_number": race['race_number'],
                    "post_time": race['post_time'],
                    "distance": race['distance'],
                    "race_type": race['race_name'].replace(f"Race {race['race_number']} ", ""),
                    "entries": []
                }
                
                # Add horse entries
                for horse in details['horses']:
                    horse_entry = {
                        "program_number": horse['number'],
                        "horse_name": horse['name'],
                        "jockey": horse['jockey'],
                        "trainer": horse['trainer'],
                        "morning_line": "--",  # Would need odds endpoint
                        "weight": horse.get('weight', 'N/A')
                    }
                    race_data["entries"].append(horse_entry)
                
                fair_meadows_races.append(race_data)
    
    # Check if we found Fair Meadows
    if not fair_meadows_races:
        print(f"❌ No Fair Meadows/Prairie Meadows races found")
        print(f"   Available venues: {', '.join(sorted(venues_found))}")
        return False
    
    print(f"✅ Found {len(fair_meadows_races)} Fair Meadows races")
    
    # Create data structure
    fair_meadows_data = {
        "track": "Fair Meadows",
        "location": "Tulsa, Oklahoma",
        "date": date_obj.strftime('%Y-%m-%d'),
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_races": len(fair_meadows_races),
        "races": {}
    }
    
    # Add races to data structure
    for race in fair_meadows_races:
        race_num = str(race['race_number'])
        fair_meadows_data['races'][race_num] = {
            "race_number": race['race_number'],
            "post_time": race['post_time'],
            "distance": race['distance'],
            "race_type": race['race_type'],
            "horses": []
        }
        
        # Add horses with betting format
        for entry in race['entries']:
            horse_data = {
                "program_number": int(entry['program_number']),
                "horse_name": entry['horse_name'],
                "jockey": entry['jockey'],
                "trainer": entry['trainer'],
                "morning_line": entry['morning_line'],
                "live_odds": "--",
                "true_odds": "--",
                "itm_true_odds": "--",
                "adj_true_odds": "--"
            }
            fair_meadows_data['races'][race_num]['horses'].append(horse_data)
    
    # Save JSON file
    json_filename = f"fair_meadows_{date_obj.strftime('%B').lower()}{date_obj.day}_{date_obj.year}.json"
    json_path = os.path.join(os.path.dirname(__file__), json_filename)
    
    with open(json_path, 'w') as f:
        json.dump(fair_meadows_data, f, indent=2)
    
    print(f"💾 Saved race data to: {json_filename}")
    
    # Generate HTML page
    html_content = generate_html_page(fair_meadows_data)
    html_filename = f"fair_meadows_{date_obj.strftime('%B').lower()}{date_obj.day}_{date_obj.year}.html"
    html_path = os.path.join(os.path.dirname(__file__), html_filename)
    
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    print(f"📄 Generated HTML page: {html_filename}")
    
    # Remove placeholder if it exists
    placeholder_name = f"fair_meadows_{date_obj.strftime('%B').lower()}{date_obj.day}_{date_obj.year}_placeholder.html"
    placeholder_path = os.path.join(os.path.dirname(__file__), placeholder_name)
    if os.path.exists(placeholder_path):
        os.remove(placeholder_path)
        print(f"🗑️  Removed placeholder page")
    
    return True

def generate_html_page(data):
    """Generate HTML page from race data"""
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
    date_str = date_obj.strftime('%A, %B %d, %Y')
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Fair Meadows - {date_str} | STALL10N</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background-color: #FFFFFF;
            color: #001E60;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{ 
            color: #0053E2;
            font-size: 2.5rem;
            margin-bottom: 30px;
            text-align: center;
            font-weight: 300;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        h2 {{
            color: #001E60;
            font-size: 1.8rem;
            margin: 30px 0 15px;
            font-weight: 400;
            border-bottom: 2px solid #0053E2;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #0053E2;
            font-size: 1.3rem;
            margin: 20px 0 10px;
            font-weight: 400;
        }}
        .update-time {{
            text-align: center;
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 30px;
        }}
        .race-date {{ 
            margin: 40px 0;
            background: #FFFFFF;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0, 30, 96, 0.1);
            border: 1px solid #A9DDF7;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0;
            background-color: #FFFFFF;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 3px 15px rgba(0, 30, 96, 0.1);
            border: 1px solid #A9DDF7;
        }}
        th, td {{ 
            padding: 15px;
            text-align: center;
            width: 16.66%;
        }}
        th {{ 
            background-color: #0053E2;
            color: #FFFFFF;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.9rem;
            border-bottom: 3px solid #4DBDF5;
        }}
        td {{
            background-color: #FFFFFF;
            border-bottom: 1px solid #A9DDF7;
            font-weight: 400;
            color: #001E60;
        }}
        tr:hover td {{
            background-color: #A9DDF7;
            transition: background-color 0.3s ease;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .program-number {{
            font-weight: 700;
            color: #4DBDF5;
        }}
        .horse-name {{
            font-weight: 500;
            color: #001E60;
        }}
        .probability {{
            color: #001E60;
        }}
        .adj-odds {{
            color: #0053E2;
            font-weight: 600;
        }}
        .morning-line {{
            color: #001E60;
        }}
        .live-odds {{
            color: #FF6B00;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Fair Meadows Racing</h1>
        <h2>{date_str}</h2>
        <div class="update-time">Last Updated: {data['last_updated']}</div>
"""
    
    # Add each race
    for race_num in sorted(data['races'].keys(), key=int):
        race = data['races'][race_num]
        
        html += f"""
        <div class="race-date">
            <h3>Race {race['race_number']} - {race['race_type']} - {race['distance']}</h3>
            <p style="color: #666; margin-bottom: 15px;">Post Time: {race['post_time']}</p>
            <table>
                <thead>
                    <tr>
                        <th>PGM</th>
                        <th>Horse</th>
                        <th>Jockey</th>
                        <th>Trainer</th>
                        <th>Morning Line</th>
                        <th>Live Odds</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for horse in race['horses']:
            html += f"""
                    <tr>
                        <td class="program-number">{horse['program_number']}</td>
                        <td class="horse-name">{horse['horse_name']}</td>
                        <td>{horse['jockey']}</td>
                        <td>{horse['trainer']}</td>
                        <td class="morning-line">{horse['morning_line']}</td>
                        <td class="live-odds">{horse['live_odds']}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
    
    html += """
    </div>
</body>
</html>"""
    
    return html

def main():
    parser = argparse.ArgumentParser(description='Pull Fair Meadows race data from StatPal API')
    parser.add_argument('--date', type=str, help='Target date in YYYY-MM-DD format (default: today)')
    
    args = parser.parse_args()
    
    success = pull_fair_meadows_data(args.date)
    
    if success:
        print("\n✅ Successfully pulled Fair Meadows data!")
    else:
        print("\n❌ Failed to pull Fair Meadows data")
        sys.exit(1)

if __name__ == "__main__":
    main()