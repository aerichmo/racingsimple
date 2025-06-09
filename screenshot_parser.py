"""Screenshot parser for horse racing betting data"""
import logging
import re
from typing import List, Dict, Optional, Tuple
import pytesseract
from PIL import Image
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class ScreenshotParser:
    """Parse horse racing screenshots to extract win probability and M/L odds"""
    
    def __init__(self):
        self.patterns = {
            'race_header': re.compile(r'RACE\s*(\d+)', re.IGNORECASE),
            'post_time': re.compile(r'(\d+:\d+\s*[AP]M)'),
            'horse_entry': re.compile(r'^(\d+)\s+([A-Za-z\s\']+?)\s+([\d.]+%)\s*-?\s*([\d/]+)', re.MULTILINE),
            'win_prob': re.compile(r'([\d.]+)%'),
            'ml_odds': re.compile(r'(\d+/\d+)'),
            'purse': re.compile(r'Purse\s*\$([0-9,]+)', re.IGNORECASE),
            'distance': re.compile(r'(\d+(?:\s*1/2)?)\s*(Furlongs?|Miles?)', re.IGNORECASE),
            'class_rating': re.compile(r'Class Rating:\s*(\d+)', re.IGNORECASE)
        }
    
    def parse_screenshot(self, image_path: str) -> Dict:
        """Parse a single screenshot and extract race data"""
        try:
            # Load and preprocess image
            image = self._preprocess_image(image_path)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            
            # Parse the extracted text
            return self._parse_race_data(text, image_path)
            
        except Exception as e:
            logger.error(f"Error parsing screenshot {image_path}: {e}")
            return {}
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        # Load image
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to make text clearer
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Denoise
        denoised = cv2.fastNlDenoising(thresh)
        
        return denoised
    
    def _parse_race_data(self, text: str, image_path: str) -> Dict:
        """Parse race data from OCR text"""
        race_data = {
            'image_path': image_path,
            'entries': []
        }
        
        # Extract race number
        race_match = self.patterns['race_header'].search(text)
        if race_match:
            race_data['race_number'] = int(race_match.group(1))
        
        # Extract post time
        time_match = self.patterns['post_time'].search(text)
        if time_match:
            race_data['post_time'] = time_match.group(1)
        
        # Extract purse
        purse_match = self.patterns['purse'].search(text)
        if purse_match:
            race_data['purse'] = purse_match.group(1).replace(',', '')
        
        # Extract distance
        dist_match = self.patterns['distance'].search(text)
        if dist_match:
            race_data['distance'] = dist_match.group(1).replace(' 1/2', '.5')
            race_data['dist_unit'] = 'F' if 'Furlong' in dist_match.group(2) else 'M'
        
        # Extract class rating
        class_match = self.patterns['class_rating'].search(text)
        if class_match:
            race_data['class_rating'] = int(class_match.group(1))
        
        # Parse entries from table
        race_data['entries'] = self._parse_entries_from_table(text)
        
        return race_data
    
    def _parse_entries_from_table(self, text: str) -> List[Dict]:
        """Parse horse entries from the table in the screenshot"""
        entries = []
        
        # Split text into lines
        lines = text.split('\n')
        
        # Look for table data
        in_table = False
        for line in lines:
            # Check if we're in the horse entries table
            if 'Program Number' in line and 'Win Probability' in line:
                in_table = True
                continue
            
            if not in_table:
                continue
            
            # Stop at end of table
            if 'VIEW MATCHED HORSES' in line or not line.strip():
                in_table = False
                continue
            
            # Parse entry line
            entry = self._parse_entry_line(line)
            if entry:
                entries.append(entry)
        
        return entries
    
    def _parse_entry_line(self, line: str) -> Optional[Dict]:
        """Parse a single entry line from the table"""
        # Clean the line
        line = line.strip()
        if not line or len(line) < 10:
            return None
        
        # Try different patterns to extract data
        # Pattern 1: "1  Horse Name  24.1%  -  3/1  0"
        pattern1 = re.match(r'^(\d+)\s+([A-Za-z][A-Za-z\s\']+?)\s+([\d.]+%)\s*-?\s*([\d/]+)\s*(\d+)?$', line)
        if pattern1:
            return {
                'program_number': int(pattern1.group(1)),
                'horse_name': pattern1.group(2).strip(),
                'win_probability': float(pattern1.group(3).replace('%', '')),
                'ml_odds': pattern1.group(4),
                'angles_matched': int(pattern1.group(5)) if pattern1.group(5) else 0
            }
        
        # Pattern 2: Split by multiple spaces
        parts = re.split(r'\s{2,}', line)
        if len(parts) >= 4:
            try:
                return {
                    'program_number': int(parts[0]),
                    'horse_name': parts[1],
                    'win_probability': float(parts[2].replace('%', '')) if '%' in parts[2] else 0,
                    'ml_odds': parts[3] if '/' in parts[3] else parts[4] if len(parts) > 4 and '/' in parts[4] else 'N/A',
                    'angles_matched': 0
                }
            except (ValueError, IndexError):
                pass
        
        return None
    
    def parse_multiple_screenshots(self, image_paths: List[str]) -> List[Dict]:
        """Parse multiple screenshots and return all race data"""
        all_races = []
        
        for path in image_paths:
            race_data = self.parse_screenshot(path)
            if race_data and race_data.get('entries'):
                all_races.append(race_data)
                logger.info(f"Parsed race {race_data.get('race_number', 'Unknown')} with {len(race_data['entries'])} entries")
        
        return all_races