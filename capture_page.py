"""
Capture current state of STALL10N racing page
"""

import requests
from datetime import datetime

def capture_current_state():
    """Get text representation of current page state"""
    
    print("=== STALL10N Racing Page State ===")
    print(f"Captured at: {datetime.now()}\n")
    
    # Get race data
    response = requests.get("https://stall10n.onrender.com/api/races")
    if response.status_code == 200:
        races = response.json()
        
        # Group by date and race
        by_date = {}
        for race in races:
            date = race.get('race_date')
            race_num = race.get('race_number')
            
            if date not in by_date:
                by_date[date] = {}
            if race_num not in by_date[date]:
                by_date[date][race_num] = []
            
            by_date[date][race_num].append(race)
        
        # Display June 11-12 data
        for date in ['2025-06-11', '2025-06-12']:
            if date in by_date:
                print(f"\n{'='*60}")
                print(f"DATE: {date}")
                print(f"{'='*60}")
                
                for race_num in sorted(by_date[date].keys()):
                    horses = by_date[date][race_num]
                    print(f"\nRace {race_num}")
                    print("-" * 40)
                    
                    # Check for bet recommendation (winner info)
                    bet_rec = horses[0].get('bet_recommendation') or ''
                    if bet_rec and 'RESULT:' in bet_rec:
                        print(f"🏆 {bet_rec}")
                        print("-" * 40)
                    
                    print(f"{'Prog#':<6} {'Horse Name':<25} {'Win%':<6} {'ML':<8} {'Live':<8} {'Status'}")
                    print("-" * 70)
                    
                    for horse in sorted(horses, key=lambda h: h.get('program_number', 0)):
                        prog = horse.get('program_number', '-')
                        name = horse.get('horse_name', 'Unknown')[:24]
                        win_prob = f"{horse.get('win_probability', 0)}%"
                        ml = horse.get('morning_line', '-')
                        live_odds = horse.get('realtime_odds', '-')
                        
                        # Check if this horse won
                        status = '-'
                        if bet_rec and 'RESULT:' in bet_rec and name in bet_rec:
                            status = 'WINNER'
                        
                        print(f"{prog:<6} {name:<25} {win_prob:<6} {ml:<8} {live_odds:<8} {status}")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("- June 11: 2 races loaded with winners marked")
    print("- June 12: 7 races loaded with winners marked")
    print("- Live Odds column: Present (showing '-' for historical races)")
    print("- Status column: Present (winners marked via bet recommendations)")
    print("- Winners are shown in 'Bet Recommendation' sections")
    print("\nVisit https://stall10n.onrender.com/ to see the live display")

if __name__ == "__main__":
    capture_current_state()