"""Enhanced PDF Parser for Equibase Speed Figure PDFs"""
import re
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
import PyPDF2

logger = logging.getLogger(__name__)

class EquibasePDFParser:
    """Parse Equibase Speed Figure Analysis PDFs"""
    
    def parse_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Parse PDF and return list of races with entries"""
        races = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                full_text = ""
                for page in pdf_reader.pages:
                    full_text += page.extract_text() + "\n"
                
                # Parse the text
                races = self._parse_races_from_text(full_text)
                
                # Extract date from text
                race_date = self._extract_date(full_text)
                for race in races:
                    race['race_date'] = race_date
                    
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            
        return races
    
    def _parse_races_from_text(self, text: str) -> List[Dict]:
        """Parse races from extracted text"""
        races = []
        
        # Split text by race markers
        race_splits = re.split(r'(\d+)\$2 Exacta', text)
        
        for i in range(1, len(race_splits), 2):
            if i+1 < len(race_splits):
                race_num = race_splits[i].strip()
                race_text = race_splits[i+1]
                
                race = self._parse_single_race(race_num, race_text)
                if race and race.get('entries'):
                    races.append(race)
        
        return races
    
    def _parse_single_race(self, race_num: str, text: str) -> Dict:
        """Parse a single race from text"""
        race = {
            'race_number': int(race_num) if race_num.isdigit() else 0,
            'track': 'Fair Meadows',  # Default, can be extracted
            'entries': []
        }
        
        # Extract race details
        lines = text.split('\n')
        
        # Parse distance and race type from first few lines
        for line in lines[:5]:
            # Distance pattern: "350 Yards" or "6 Furlongs"
            dist_match = re.search(r'(\d+(?:\.\d+)?)\s*(Yards?|Furlongs?|Miles?)', line)
            if dist_match:
                race['distance'] = f"{dist_match.group(1)} {dist_match.group(2)}"
            
            # Race type and purse
            if 'MAIDEN' in line:
                race['race_type'] = 'MAIDEN'
            elif 'ALLOWANCE' in line:
                race['race_type'] = 'ALLOWANCE'
            elif 'CLAIMING' in line:
                race['race_type'] = 'CLAIMING'
            elif 'STAKES' in line:
                race['race_type'] = 'STAKES'
            
            # Purse
            purse_match = re.search(r'Purse:\s*\$?([\d,]+)', line)
            if purse_match:
                race['purse'] = int(purse_match.group(1).replace(',', ''))
        
        # Post time
        time_match = re.search(r'Post Time:\s*(\d{1,2}:\d{2})\s*(PM|AM)?', text)
        if time_match:
            race['post_time'] = time_match.group(1)
            if time_match.group(2) == 'PM':
                hour, minute = map(int, race['post_time'].split(':'))
                if hour != 12:
                    hour += 12
                race['post_time'] = f"{hour}:{minute:02d}"
        
        # Parse entries - look for lines with program numbers
        entry_pattern = r'^(\d+)\s+(\d+)\s+\((\d+)%\)\s+([A-Za-z\s]+?)\s+(\d+|NA)\s+(\d+|NA)\s+(\d+|NA)\s+(\d+|NA)'
        
        for line in lines:
            # Skip header lines
            if any(word in line for word in ['PgmPost', 'HorseClass', 'Jockey', 'Copyright']):
                continue
                
            # Try to parse entry
            parts = line.split()
            if len(parts) >= 10 and parts[0].isdigit() and parts[1].isdigit():
                try:
                    entry = {
                        'program_number': int(parts[0]),
                        'post_position': int(parts[1]),
                        'win_pct': self._parse_percentage(parts[2]) if len(parts[2]) > 2 else None,
                        'horse_name': ' '.join(parts[3:]).split(' ', 1)[0] if len(parts) > 3 else 'Unknown',
                        'class_rating': self._parse_int(parts[4]) if len(parts) > 4 else None,
                        'last_speed': self._parse_int(parts[5]) if len(parts) > 5 else None,
                        'avg_speed': self._parse_int(parts[6]) if len(parts) > 6 else None,
                        'best_speed': self._parse_int(parts[7]) if len(parts) > 7 else None
                    }
                    
                    # Extract jockey/trainer from remaining text
                    remaining = ' '.join(parts[8:]) if len(parts) > 8 else ''
                    jt_parts = remaining.split('/')
                    if len(jt_parts) >= 2:
                        entry['jockey'] = jt_parts[0].strip()
                        trainer_part = jt_parts[1].strip()
                        # Extract trainer name before percentages
                        trainer_match = re.match(r'([A-Za-z\s]+)', trainer_part)
                        if trainer_match:
                            entry['trainer'] = trainer_match.group(1).strip()
                    
                    # Extract J/T percentages if present
                    pct_match = re.findall(r'(\d+)%', remaining)
                    if len(pct_match) >= 3:
                        entry['jockey_win_pct'] = int(pct_match[0])
                        entry['trainer_win_pct'] = int(pct_match[1])
                        entry['jt_combo_pct'] = int(pct_match[2])
                    
                    # Only add if we have a valid horse name
                    if entry['horse_name'] and not any(skip in entry['horse_name'].lower() 
                                                      for skip in ['copyright', 'equibase', 'page']):
                        race['entries'].append(entry)
                        
                except (IndexError, ValueError) as e:
                    continue
        
        return race
    
    def _extract_date(self, text: str) -> date:
        """Extract race date from PDF text"""
        # Look for date patterns
        date_patterns = [
            r'(\w+),\s+(\w+)\s+(\d{1,2}),\s+(\d{4})',  # Saturday, June 07, 2025
            r'(\d{2})/(\d{2})/(\d{4})',  # 06/07/2025
            r'(\d{4})-(\d{2})-(\d{2})'   # 2025-06-07
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if 'June' in match.group(0):
                        return datetime.strptime(match.group(0), '%A, %B %d, %Y').date()
                    elif '/' in match.group(0):
                        return datetime.strptime(match.group(0), '%m/%d/%Y').date()
                    elif '-' in match.group(0):
                        return datetime.strptime(match.group(0), '%Y-%m-%d').date()
                except:
                    continue
        
        # Default to today
        return datetime.now().date()
    
    def _parse_percentage(self, text: str) -> Optional[float]:
        """Parse percentage from text like '(16%)'"""
        match = re.search(r'(\d+)%', text)
        if match:
            return float(match.group(1))
        return None
    
    def _parse_int(self, text: str) -> Optional[int]:
        """Parse integer, return None for 'NA'"""
        if text == 'NA' or not text.isdigit():
            return None
        return int(text)