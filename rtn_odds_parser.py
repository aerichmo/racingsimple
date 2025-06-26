#!/usr/bin/env python3
"""
RTN Odds Parser - Enhanced OCR and parsing for RTN odds displays
Handles multiple odds formats and display styles
"""

import re
import cv2
import numpy as np
import pytesseract
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RTNOddsParser:
    def __init__(self):
        # Common OCR corrections for racing data
        self.ocr_corrections = {
            'O': '0',  # Letter O to number 0
            'l': '1',  # Lowercase L to 1
            'I': '1',  # Capital I to 1
            'S': '5',  # S to 5 in certain contexts
            'Z': '2',  # Z to 2
        }
        
        # Regex patterns for different odds formats
        self.patterns = {
            'odds_fractional': r'(\d+)/(\d+)',  # 5/2, 7/1, etc
            'odds_decimal': r'(\d+\.?\d*)-(\d+)',  # 5-2, 7-1, etc
            'program_horse': r'^(\d{1,2})\s+(.+?)\s+(\d+[-/]\d+)',  # 1 HORSE NAME 5/2
            'win_place_show': r'(\d+)\s+(\d+)\s+(\d+)',  # Win Place Show amounts
            'pool_amount': r'\$?([\d,]+)',  # Pool amounts
        }
    
    def preprocess_for_ocr(self, image, region_type='odds'):
        """Preprocess image for better OCR results based on region type"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        if region_type == 'odds':
            # For odds board - typically white text on dark background
            # Invert if needed
            mean_val = np.mean(gray)
            if mean_val < 128:  # Dark background
                gray = cv2.bitwise_not(gray)
            
            # Apply adaptive threshold
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
            
            # Slight dilation to connect broken characters
            kernel = np.ones((1,1), np.uint8)
            processed = cv2.dilate(denoised, kernel, iterations=1)
            
        elif region_type == 'tote':
            # For tote board - usually has different contrast
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Binary threshold
            _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
        else:
            # Default processing
            _, processed = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        return processed
    
    def extract_text_with_confidence(self, image, region_type='odds'):
        """Extract text with confidence scores"""
        # Preprocess image
        processed = self.preprocess_for_ocr(image, region_type)
        
        # Get detailed OCR data
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
        
        # Filter by confidence
        n_boxes = len(data['text'])
        text_items = []
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 60:  # Confidence threshold
                text = data['text'][i].strip()
                if text:
                    text_items.append({
                        'text': text,
                        'conf': data['conf'][i],
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'w': data['width'][i],
                        'h': data['height'][i]
                    })
        
        return text_items
    
    def parse_odds_board(self, image):
        """Parse odds board image to extract horse odds"""
        text_items = self.extract_text_with_confidence(image, 'odds')
        
        # Group text items by line (y-coordinate)
        lines = self._group_by_lines(text_items)
        
        odds_data = []
        
        for line in lines:
            # Try to parse as horse entry with odds
            parsed = self._parse_horse_line(line)
            if parsed:
                odds_data.append(parsed)
        
        return odds_data
    
    def _group_by_lines(self, text_items, y_threshold=10):
        """Group text items that appear on the same line"""
        if not text_items:
            return []
        
        # Sort by y-coordinate
        sorted_items = sorted(text_items, key=lambda x: x['y'])
        
        lines = []
        current_line = [sorted_items[0]]
        current_y = sorted_items[0]['y']
        
        for item in sorted_items[1:]:
            if abs(item['y'] - current_y) <= y_threshold:
                current_line.append(item)
            else:
                # Sort current line by x-coordinate
                current_line.sort(key=lambda x: x['x'])
                lines.append(current_line)
                current_line = [item]
                current_y = item['y']
        
        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda x: x['x'])
            lines.append(current_line)
        
        return lines
    
    def _parse_horse_line(self, line_items):
        """Parse a line of text items into horse data"""
        if not line_items:
            return None
        
        # Concatenate text items
        full_text = ' '.join([item['text'] for item in line_items])
        
        # Apply OCR corrections
        corrected_text = self._apply_corrections(full_text)
        
        # Try to match patterns
        # Pattern 1: Program number, horse name, odds
        match = re.search(r'^(\d{1,2})\s+(.+?)\s+(\d+[-/]\d+)$', corrected_text)
        if match:
            return {
                'program_number': int(match.group(1)),
                'horse_name': match.group(2).strip(),
                'odds': match.group(3),
                'confidence': min([item['conf'] for item in line_items])
            }
        
        # Pattern 2: Just program and odds (name might be on different line)
        match = re.search(r'^(\d{1,2})\s+.*?(\d+[-/]\d+)$', corrected_text)
        if match:
            # Extract middle part as name
            name_part = corrected_text[len(match.group(1)):-(len(match.group(2)))].strip()
            return {
                'program_number': int(match.group(1)),
                'horse_name': name_part,
                'odds': match.group(2),
                'confidence': min([item['conf'] for item in line_items])
            }
        
        return None
    
    def _apply_corrections(self, text):
        """Apply common OCR corrections"""
        corrected = text
        
        # Apply character corrections in number contexts
        for wrong, right in self.ocr_corrections.items():
            # Only replace in number contexts
            corrected = re.sub(f'(?<=\d){wrong}(?=\d)', right, corrected)
            corrected = re.sub(f'(?<=\s){wrong}(?=\d)', right, corrected)
            corrected = re.sub(f'(?<=\d){wrong}(?=\s)', right, corrected)
        
        return corrected
    
    def parse_tote_board(self, image):
        """Parse tote board for pool information"""
        text_items = self.extract_text_with_confidence(image, 'tote')
        
        # Look for pool amounts
        pools = {}
        full_text = ' '.join([item['text'] for item in text_items])
        
        # Common pool types
        pool_types = ['WIN', 'PLACE', 'SHOW', 'EXACTA', 'TRIFECTA', 'SUPERFECTA']
        
        for pool_type in pool_types:
            # Look for pool type followed by amount
            pattern = f'{pool_type}.*?\$?([\d,]+)'
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                pools[pool_type] = int(amount)
        
        return pools
    
    def parse_race_info(self, image):
        """Parse race information header"""
        text_items = self.extract_text_with_confidence(image, 'info')
        full_text = ' '.join([item['text'] for item in text_items])
        
        info = {}
        
        # Extract race number
        race_match = re.search(r'RACE\s*(\d+)', full_text, re.IGNORECASE)
        if race_match:
            info['race_number'] = int(race_match.group(1))
        
        # Extract distance
        dist_match = re.search(r'(\d+\.?\d*)\s*(FURLONGS?|YARDS?|MILES?)', full_text, re.IGNORECASE)
        if dist_match:
            info['distance'] = f"{dist_match.group(1)} {dist_match.group(2)}"
        
        # Extract post time or MTP (minutes to post)
        mtp_match = re.search(r'(\d+)\s*MTP', full_text)
        if mtp_match:
            info['minutes_to_post'] = int(mtp_match.group(1))
        
        return info


# Testing function
def test_parser():
    """Test the parser with a sample image"""
    parser = RTNOddsParser()
    
    # Load test image (you'll need to provide this)
    # image = cv2.imread('test_odds_board.png')
    
    # Test with synthetic data for now
    print("RTN Odds Parser initialized")
    print("Ready to parse odds boards, tote boards, and race info")
    
    # Example of how to use:
    # odds = parser.parse_odds_board(odds_image)
    # pools = parser.parse_tote_board(tote_image)
    # info = parser.parse_race_info(info_image)


if __name__ == "__main__":
    test_parser()