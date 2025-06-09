"""Simple screenshot parser that uses hardcoded data for testing"""
import logging
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

class ScreenshotParser:
    """Parse horse racing screenshots - simplified version for testing"""
    
    def __init__(self):
        self.parse_count = 0  # Counter to ensure different data for each image
        # Only real data from the screenshots provided
        self.sample_data = {
            "race4": {
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
            "race5": {
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
            },
            "race6": {
                "race_number": 6,
                "post_time": "8:20 PM",
                "entries": [
                    {"program_number": 1, "horse_name": "Eura Happy Hippie", "win_probability": 5.7, "ml_odds": "12/1", "angles_matched": 0},
                    {"program_number": 2, "horse_name": "Da Chief", "win_probability": 8.0, "ml_odds": "3/1", "angles_matched": 0},
                    {"program_number": 3, "horse_name": "Gospel Don", "win_probability": 2.4, "ml_odds": "20/1", "angles_matched": 1},
                    {"program_number": 4, "horse_name": "Son of Preacherman", "win_probability": 6.1, "ml_odds": "6/1", "angles_matched": 0},
                    {"program_number": 5, "horse_name": "Devious Dennis", "win_probability": 61.4, "ml_odds": "1/1", "angles_matched": 1},
                    {"program_number": 6, "horse_name": "Midnight Talker", "win_probability": 16.4, "ml_odds": "7/2", "angles_matched": 0}
                ]
            },
            "race7": {
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
            "race8": {
                "race_number": 8,
                "post_time": "9:16 PM",
                "entries": [
                    {"program_number": 1, "horse_name": "Momma Wink", "win_probability": 4.0, "ml_odds": "20/1", "angles_matched": 0},
                    {"program_number": 2, "horse_name": "Woman's Intuition", "win_probability": 41.7, "ml_odds": "3/5", "angles_matched": 1},
                    {"program_number": 3, "horse_name": "Patient Emilie", "win_probability": 10.3, "ml_odds": "8/1", "angles_matched": 1},
                    {"program_number": 4, "horse_name": "Sunshine Sister", "win_probability": 8.8, "ml_odds": "8/1", "angles_matched": 0},
                    {"program_number": 5, "horse_name": "Majestic Irons", "win_probability": 16.8, "ml_odds": "5/1", "angles_matched": 0},
                    {"program_number": 6, "horse_name": "Kamikaze Ozie", "win_probability": 4.9, "ml_odds": "20/1", "angles_matched": 1},
                    {"program_number": 7, "horse_name": "Call Darla", "win_probability": 13.7, "ml_odds": "6/1", "angles_matched": 0}
                ]
            }
        }
    
    def parse_screenshot(self, image_path: str) -> Dict:
        """Parse a single screenshot and extract race data"""
        try:
            # For testing, we'll rotate through the sample data
            # In production, this would use OCR to extract real data
            
            # Use counter to cycle through sample data
            data_keys = list(self.sample_data.keys())
            data_key = data_keys[self.parse_count % len(data_keys)]
            self.parse_count += 1
            
            # Deep copy the data to avoid reference issues
            import copy
            data = copy.deepcopy(self.sample_data[data_key])
            data['image_path'] = image_path
            
            # Ensure we have the required fields
            if 'entries' not in data:
                data['entries'] = []
            
            logger.info(f"Using sample data: Race {data.get('race_number', 'Unknown')} with {len(data.get('entries', []))} entries for {os.path.basename(image_path)}")
            
            # Debug: Log the actual data structure
            logger.debug(f"Data structure: race_number={data.get('race_number')}, entries count={len(data.get('entries', []))}")
            if data.get('entries'):
                logger.debug(f"First entry: {data['entries'][0]}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing screenshot {image_path}: {e}")
            return {"image_path": image_path, "entries": []}
    
    def parse_multiple_screenshots(self, image_paths: List[str]) -> List[Dict]:
        """Parse multiple screenshots and return all race data"""
        all_races = []
        
        logger.info(f"parse_multiple_screenshots called with {len(image_paths)} paths")
        
        for path in image_paths:
            logger.info(f"Processing screenshot: {path}")
            race_data = self.parse_screenshot(path)
            
            if race_data:
                logger.info(f"Race data returned: {race_data.get('race_number', 'None')}, entries: {len(race_data.get('entries', []))}")
                if race_data.get('entries'):
                    all_races.append(race_data)
                    logger.info(f"Added race {race_data.get('race_number', 'Unknown')} with {len(race_data['entries'])} entries")
                else:
                    logger.warning(f"Race data has no entries for {path}")
            else:
                logger.warning(f"No race data returned for {path}")
        
        logger.info(f"Returning {len(all_races)} races total")
        return all_races