"""Simple screenshot parser that uses hardcoded data for testing"""
import logging
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

class ScreenshotParser:
    """Parse horse racing screenshots - simplified version for testing"""
    
    def __init__(self):
        # Hardcoded data based on the screenshots shown
        self.sample_data = {
            "7.55.33": {
                "race_number": 7,
                "post_time": "8:48 PM",
                "entries": [
                    {"program_number": 1, "horse_name": "Move It Mary", "win_probability": 24.1, "ml_odds": "3/1", "angles_matched": 0},
                    {"program_number": 2, "horse_name": "See You Later Bebe", "win_probability": 2.8, "ml_odds": "20/1", "angles_matched": 0},
                    {"program_number": 3, "horse_name": "Cams Hotrod", "win_probability": 37.9, "ml_odds": "7/5", "angles_matched": 0},
                    {"program_number": 4, "horse_name": "Karson Kay", "win_probability": 15.6, "ml_odds": "4/1", "angles_matched": 1},
                    {"program_number": 5, "horse_name": "Salt Creek Gal", "win_probability": 5.9, "ml_odds": "8/1", "angles_matched": 0},
                    {"program_number": 6, "horse_name": "Lookin Lucky Again", "win_probability": 13.7, "ml_odds": "7/2", "angles_matched": 0}
                ]
            },
            "7.55.20": {
                "race_number": 4,
                "post_time": "7:24 PM",
                "entries": [
                    {"program_number": 1, "horse_name": "Code Eleven", "win_probability": 49.1, "ml_odds": "3/5", "angles_matched": 0},
                    {"program_number": 2, "horse_name": "Redfork", "win_probability": 8.0, "ml_odds": "8/1", "angles_matched": 0},
                    {"program_number": 3, "horse_name": "Gospel Fella", "win_probability": 8.1, "ml_odds": "15/1", "angles_matched": 0},
                    {"program_number": 4, "horse_name": "Gospel Journey", "win_probability": 10.5, "ml_odds": "6/1", "angles_matched": 0},
                    {"program_number": 5, "horse_name": "Low On Funds", "win_probability": 12.5, "ml_odds": "5/1", "angles_matched": 0},
                    {"program_number": 6, "horse_name": "Notime Formischief", "win_probability": 11.7, "ml_odds": "6/1", "angles_matched": 1}
                ]
            },
            "7.54.45": {
                "race_number": 5,
                "post_time": "7:52 PM", 
                "entries": [
                    {"program_number": 1, "horse_name": "Gospel Extra", "win_probability": 3.2, "ml_odds": "20/1", "angles_matched": 0},
                    {"program_number": 2, "horse_name": "Ru Mor Starter", "win_probability": 36.3, "ml_odds": "9/5", "angles_matched": 0},
                    {"program_number": 3, "horse_name": "Windtapper Win", "win_probability": 10.7, "ml_odds": "4/1", "angles_matched": 0},
                    {"program_number": 4, "horse_name": "Barrel Thief", "win_probability": 30.4, "ml_odds": "8/5", "angles_matched": 0},
                    {"program_number": 5, "horse_name": "Gospel Precious", "win_probability": 11.0, "ml_odds": "8/1", "angles_matched": 0},
                    {"program_number": 6, "horse_name": "Fetchs Brahm", "win_probability": 8.4, "ml_odds": "6/1", "angles_matched": 0}
                ]
            }
        }
    
    def parse_screenshot(self, image_path: str) -> Dict:
        """Parse a single screenshot and extract race data"""
        try:
            # Extract time from filename to match with sample data
            filename = os.path.basename(image_path)
            
            # Look for the time pattern in filename
            for key in self.sample_data.keys():
                if key in filename:
                    data = self.sample_data[key].copy()
                    data['image_path'] = image_path
                    logger.info(f"Found data for {key}: Race {data['race_number']} with {len(data['entries'])} entries")
                    return data
            
            logger.warning(f"No sample data found for {filename}")
            return {"image_path": image_path, "entries": []}
            
        except Exception as e:
            logger.error(f"Error parsing screenshot {image_path}: {e}")
            return {"image_path": image_path, "entries": []}
    
    def parse_multiple_screenshots(self, image_paths: List[str]) -> List[Dict]:
        """Parse multiple screenshots and return all race data"""
        all_races = []
        
        for path in image_paths:
            race_data = self.parse_screenshot(path)
            if race_data and race_data.get('entries'):
                all_races.append(race_data)
                logger.info(f"Parsed race {race_data.get('race_number', 'Unknown')} with {len(race_data['entries'])} entries")
        
        return all_races