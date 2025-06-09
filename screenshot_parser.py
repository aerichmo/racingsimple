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
            
            # Extract text using OCR with custom config for better table recognition
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Log the extracted text for debugging
            logger.debug(f"OCR extracted text from {image_path}:\n{text[:500]}...")
            
            # Parse the extracted text
            race_data = self._parse_race_data(text, image_path)
            
            # If no entries found, try alternative OCR settings
            if not race_data.get('entries'):
                logger.info("No entries found with default OCR, trying alternative settings")
                # Try with different page segmentation mode
                text = pytesseract.image_to_string(image, config='--psm 4')
                race_data = self._parse_race_data(text, image_path)
            
            return race_data
            
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
        
        # Try to find race number from the large number at top left (e.g., "7", "8", "4")
        lines = text.split('\n')
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            # Look for standalone single/double digit number
            if re.match(r'^\s*(\d{1,2})\s*$', line.strip()):
                race_data['race_number'] = int(line.strip())
                break
        
        # Extract post time
        time_match = self.patterns['post_time'].search(text)
        if time_match:
            race_data['post_time'] = time_match.group(1)
        
        # Extract purse
        purse_match = self.patterns['purse'].search(text)
        if purse_match:
            race_data['purse'] = purse_match.group(1).replace(',', '')
        
        # Extract distance (e.g., "6 Furlongs", "1 Mile")
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
        
        # Log debug info
        logger.info(f"Parsed race {race_data.get('race_number', 'Unknown')} from {image_path}")
        logger.debug(f"Found {len(race_data['entries'])} entries")
        
        return race_data
    
    def _parse_entries_from_table(self, text: str) -> List[Dict]:
        """Parse horse entries from the table in the screenshot"""
        entries = []
        
        # Split text into lines
        lines = text.split('\n')
        
        # Look for table data
        in_table = False
        for i, line in enumerate(lines):
            # Check if we're in the horse entries table - look for header
            if ('Program' in line or 'Horse' in line) and ('Win Probability' in line or 'Odds' in line or 'M/L' in line):
                in_table = True
                logger.debug(f"Found table header at line {i}: {line}")
                continue
            
            if not in_table:
                continue
            
            # Stop at end of table
            if 'VIEW MATCHED HORSES' in line or 'PRINT ANGLES' in line:
                break
            
            # Skip empty lines but stay in table
            if not line.strip():
                continue
            
            # Parse entry line
            entry = self._parse_entry_line(line)
            if entry:
                entries.append(entry)
                logger.debug(f"Parsed entry: {entry}")
        
        return entries
    
    def _parse_entry_line(self, line: str) -> Optional[Dict]:
        """Parse a single entry line from the table"""
        # Clean the line
        line = line.strip()
        if not line or len(line) < 5:
            return None
        
        # Skip lines that don't start with a number (program number)
        if not re.match(r'^\d', line):
            return None
        
        # Try to extract the key components
        # Looking for: program_number, horse_name, win_probability%, odds (M/L)
        
        # First, try to find the win probability percentage
        prob_match = re.search(r'(\d+\.?\d*)%', line)
        if not prob_match:
            return None
        
        win_prob = float(prob_match.group(1))
        
        # Find M/L odds (format: 3/1, 20/1, etc.)
        odds_match = re.search(r'(\d+/\d+)', line)
        ml_odds = odds_match.group(1) if odds_match else 'N/A'
        
        # Extract program number (first number in line)
        prog_match = re.match(r'^(\d+)', line)
        if not prog_match:
            return None
        
        program_number = int(prog_match.group(1))
        
        # Extract horse name - between program number and win probability
        # Find positions
        prog_end = prog_match.end()
        prob_start = line.find(prob_match.group(0))  # Find the actual position of the probability match
        
        # Extract text between program number and probability
        horse_name_area = line[prog_end:prob_start].strip()
        
        # Clean up horse name - remove extra spaces, dashes, etc.
        horse_name = re.sub(r'\s+', ' ', horse_name_area)
        horse_name = horse_name.replace(' - ', ' ').strip()
        
        # Remove any trailing numbers or special characters
        horse_name = re.sub(r'\s+\d+\s*$', '', horse_name)
        horse_name = re.sub(r'\s*-\s*$', '', horse_name)
        
        if not horse_name or len(horse_name) < 2:
            return None
        
        # Extract angles matched if present (usually last number in line)
        angles = 0
        angles_match = re.search(r'(\d+)\s*$', line[prob_match.end():])
        if angles_match and odds_match:
            # Make sure this number comes after the odds
            if line.rfind(angles_match.group(1)) > line.rfind(odds_match.group(1)):
                angles = int(angles_match.group(1))
        
        return {
            'program_number': program_number,
            'horse_name': horse_name,
            'win_probability': win_prob,
            'ml_odds': ml_odds,
            'angles_matched': angles
        }
    
    def parse_multiple_screenshots(self, image_paths: List[str]) -> List[Dict]:
        """Parse multiple screenshots and return all race data"""
        all_races = []
        
        for path in image_paths:
            race_data = self.parse_screenshot(path)
            if race_data and race_data.get('entries'):
                all_races.append(race_data)
                logger.info(f"Parsed race {race_data.get('race_number', 'Unknown')} with {len(race_data['entries'])} entries")
        
        return all_races