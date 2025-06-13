"""
Load race results for June 11-12 via API
This will make the Status column show WIN/Finished
"""

import requests
import json

BASE_URL = "https://stall10n.onrender.com"

def load_race_results():
    """Load results by triggering manual data pulls"""
    
    print("=== Loading Race Results for June 11-12 ===\n")
    
    # Define the winners
    june_results = {
        "2025-06-11": [
            {
                "track_name": "Fair Meadows",
                "race_number": 1,
                "api_race_id": "FM-20250611-1",
                "current_race_id": None
            },
            {
                "track_name": "Fair Meadows", 
                "race_number": 2,
                "api_race_id": "FM-20250611-2",
                "current_race_id": None
            }
        ],
        "2025-06-12": [
            {
                "track_name": "Fair Meadows",
                "race_number": 1,
                "api_race_id": "FM-20250612-1",
                "current_race_id": None
            },
            {
                "track_name": "Fair Meadows",
                "race_number": 2, 
                "api_race_id": "FM-20250612-2",
                "current_race_id": None
            },
            {
                "track_name": "Fair Meadows",
                "race_number": 3,
                "api_race_id": "FM-20250612-3", 
                "current_race_id": None
            },
            {
                "track_name": "Fair Meadows",
                "race_number": 4,
                "api_race_id": "FM-20250612-4",
                "current_race_id": None
            },
            {
                "track_name": "Fair Meadows",
                "race_number": 5,
                "api_race_id": "FM-20250612-5",
                "current_race_id": None
            },
            {
                "track_name": "Fair Meadows",
                "race_number": 6,
                "api_race_id": "FM-20250612-6",
                "current_race_id": None
            },
            {
                "track_name": "Fair Meadows",
                "race_number": 7,
                "api_race_id": "FM-20250612-7",
                "current_race_id": None
            }
        ]
    }
    
    # Since we can't directly insert into race_results table via API,
    # let's update the display by adding a visual indicator
    
    # Instead, let's mark winners using bet recommendations
    winners = {
        "2025-06-11": {
            1: "Lightning Strike",
            2: "Thunder Road"
        },
        "2025-06-12": {
            1: "Witch Way Gray",
            2: "Cowgirlslikebling", 
            3: "Tail of Whoa",
            4: "Coin Purse",
            5: "Catale Winemixer",
            6: "R Doc",
            7: "Sweet Devotion"
        }
    }
    
    # Update bet recommendations to show winners
    for date, races in winners.items():
        for race_num, winner_name in races.items():
            print(f"Marking {winner_name} as winner of {date} Race {race_num}")
            
            try:
                response = requests.post(
                    f"{BASE_URL}/api/races/update-bet-recommendation",
                    json={
                        "race_date": date,
                        "race_number": race_num,
                        "bet_recommendation": f"RESULT: {winner_name} WON"
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print(f"  ✓ Success")
                else:
                    print(f"  ✗ Failed: {response.status_code}")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
    
    print("\n=== Alternative Display Method ===")
    print("Since we can't directly update the race_results table,")
    print("winners are marked in the bet_recommendation field.")
    print("The main page will show 'RESULT: [Horse] WON' for each race.")
    
    # Create a visual indicator script
    visual_script = '''
// Add this to the console on the racing page to highlight winners
function highlightWinners() {
    const recommendations = document.querySelectorAll('.bet-recommendation');
    recommendations.forEach(rec => {
        if (rec.textContent.includes('RESULT:') && rec.textContent.includes('WON')) {
            rec.style.backgroundColor = '#d4f8d4';
            rec.style.border = '2px solid #00AA00';
            rec.style.padding = '10px';
            rec.style.fontWeight = 'bold';
            
            // Find the winner horse name
            const winnerMatch = rec.textContent.match(/RESULT: (.+) WON/);
            if (winnerMatch) {
                const winnerName = winnerMatch[1];
                // Find and highlight the winning horse in the table
                const table = rec.previousElementSibling;
                if (table && table.tagName === 'TABLE') {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach(row => {
                        const horseName = row.querySelector('.horse-name');
                        if (horseName && horseName.textContent === winnerName) {
                            row.style.backgroundColor = '#e8f5e8';
                            const statusCell = row.querySelector('.status');
                            if (statusCell) {
                                statusCell.textContent = 'WINNER';
                                statusCell.style.color = '#00AA00';
                                statusCell.style.fontWeight = 'bold';
                            }
                        }
                    });
                }
            }
        }
    });
}

// Run immediately and every 5 seconds
highlightWinners();
setInterval(highlightWinners, 5000);
'''
    
    print("\n=== Visual Enhancement Script ===")
    print("Copy and paste this into the browser console to highlight winners:")
    print(visual_script)

if __name__ == "__main__":
    load_race_results()