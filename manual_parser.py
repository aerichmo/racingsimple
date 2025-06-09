"""Manual parser that extracts race data from predefined regions of screenshots"""
import logging
from typing import List, Dict, Optional
from PIL import Image
import json
import os

logger = logging.getLogger(__name__)

class ManualParser:
    """Parse horse racing screenshots by reading specific regions"""
    
    def __init__(self):
        # Define regions where data typically appears in screenshots
        # These are approximate positions that work for most race screenshots
        self.regions = {
            'race_number': {'x': 20, 'y': 20, 'width': 100, 'height': 100},
            'entries_table': {'x': 20, 'y': 150, 'width': 800, 'height': 400}
        }
        
    def parse_screenshot(self, image_path: str) -> Dict:
        """Parse a single screenshot - returns empty data if can't read"""
        try:
            # For now, return empty structure that can be filled manually
            logger.info(f"Processing screenshot: {image_path}")
            
            # Extract race number from filename if possible
            filename = os.path.basename(image_path)
            race_number = self._extract_race_number(filename)
            
            return {
                'race_number': race_number,
                'image_path': image_path,
                'entries': [],
                'needs_manual_entry': True
            }
            
        except Exception as e:
            logger.error(f"Error parsing screenshot {image_path}: {e}")
            return {
                'race_number': 0,
                'image_path': image_path,
                'entries': [],
                'needs_manual_entry': True
            }
    
    def _extract_race_number(self, filename: str) -> int:
        """Try to extract race number from filename"""
        # Look for patterns like "race1", "race_1", "r1", etc.
        import re
        
        patterns = [
            r'race[\s_-]?(\d+)',
            r'r[\s_-]?(\d+)',
            r'(\d+)[\s_-]?race',
            r'^(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return 0
    
    def parse_multiple_screenshots(self, image_paths: List[str]) -> List[Dict]:
        """Parse multiple screenshots and return all race data"""
        all_races = []
        
        for i, path in enumerate(image_paths):
            race_data = self.parse_screenshot(path)
            
            # If no race number found, use sequential numbering
            if race_data['race_number'] == 0:
                race_data['race_number'] = i + 1
                
            all_races.append(race_data)
            logger.info(f"Parsed race {race_data['race_number']} from {os.path.basename(path)}")
        
        return all_races