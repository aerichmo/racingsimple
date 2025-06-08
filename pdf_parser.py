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
        
        # Try multiple ways to split races
        race_patterns = [
            (r'(\d+)\$2 Exacta', 2),  # Original pattern
            (r'Race\s+(\d+)', 1),      # "Race X" pattern
            (r'(\d+)(?:st|nd|rd|th)\s+Race', 1),  # "1st Race" pattern
            (r'RACE\s+(\d+)', 1),      # "RACE X" pattern
        ]
        
        race_splits = None
        race_nums = []
        
        # Try each pattern
        for pattern, group_offset in race_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                logger.info(f"Found {len(matches)} races using pattern: {pattern}")
                # Extract race sections
                race_splits = []
                for i, match in enumerate(matches):
                    race_num = match.group(1)
                    start = match.start()
                    end = matches[i+1].start() if i+1 < len(matches) else len(text)
                    race_text = text[start:end]
                    race_nums.append(race_num)
                    race_splits.append(race_text)
                break
        
        # If no race markers found, treat entire text as one race
        if not race_splits:
            logger.warning("No race markers found, treating as single race")
            race_nums = ['1']
            race_splits = [text]
        
        # Parse each race
        for race_num, race_text in zip(race_nums, race_splits):
                
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
        for line in lines:
            # Skip header lines
            if any(word in line for word in ['PgmPost', 'HorseClass', 'Jockey', 'Copyright', 'Equibase Speed']):
                continue
                
            # Try multiple patterns to parse entries
            entry = self._try_parse_entry_line(line)
            if entry:
                race['entries'].append(entry)
                continue
                
            # Original parsing method as fallback
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                try:
                    # Find where the numeric data starts after horse name
                    # Look for the class rating (first number after horse name)
                    horse_name_parts = []
                    class_idx = -1
                    
                    for i in range(3, len(parts)):
                        if parts[i].isdigit() or parts[i] == 'NA':
                            class_idx = i
                            break
                        horse_name_parts.append(parts[i])
                    
                    if class_idx == -1 or not horse_name_parts:
                        continue
                    
                    entry = {
                        'program_number': int(parts[0]),
                        'post_position': int(parts[1]),
                        'win_pct': self._parse_percentage(parts[2]),
                        'horse_name': ' '.join(horse_name_parts),
                        'class_rating': self._parse_int(parts[class_idx]) if class_idx < len(parts) else None,
                        'last_speed': self._parse_int(parts[class_idx + 1]) if class_idx + 1 < len(parts) else None,
                        'avg_speed': self._parse_int(parts[class_idx + 2]) if class_idx + 2 < len(parts) else None,
                        'best_speed': self._parse_int(parts[class_idx + 3]) if class_idx + 3 < len(parts) else None
                    }
                    
                    # Find the slash that separates jockey and trainer
                    slash_idx = -1
                    for i in range(class_idx + 4, len(parts)):
                        if parts[i] == '/':
                            slash_idx = i
                            break
                    
                    if slash_idx > -1:
                        # Extract jockey (before slash)
                        jockey_parts = []
                        for i in range(class_idx + 4, slash_idx):
                            if i < len(parts) and not parts[i].endswith('%'):
                                jockey_parts.append(parts[i])
                        entry['jockey'] = ' '.join(jockey_parts)
                        
                        # Extract trainer (after slash)
                        trainer_parts = []
                        for i in range(slash_idx + 1, len(parts)):
                            if not parts[i].endswith('%'):
                                trainer_parts.append(parts[i])
                            else:
                                break
                        entry['trainer'] = ' '.join(trainer_parts)
                    
                    # Extract J/T percentages from end of line
                    pct_matches = re.findall(r'(\d+)%', line)
                    if len(pct_matches) >= 3:
                        # Skip the win% and get the last 3 percentages
                        entry['jockey_win_pct'] = int(pct_matches[-3])
                        entry['trainer_win_pct'] = int(pct_matches[-2])
                        entry['jt_combo_pct'] = int(pct_matches[-1])
                    
                    # Only add if we have a valid horse name
                    if entry['horse_name'] and not any(skip in entry['horse_name'].lower() 
                                                      for skip in ['copyright', 'equibase', 'page']):
                        race['entries'].append(entry)
                        
                except (IndexError, ValueError) as e:
                    logger.debug(f"Failed to parse line: {line}, error: {e}")
                    continue
        
        return race
    
    def _try_parse_entry_line(self, line: str) -> Optional[Dict]:
        """Try multiple patterns to parse an entry line"""
        line = line.strip()
        if not line:
            return None
            
        # Pattern 1: Standard format with program number at start
        match = re.match(r'^(\d{1,2})\s+(\d{1,2})?\s*\(?([\d.]+)%?\)?\s+([A-Z][A-Z\s\']+?)\s+(\d+|NA)', line)
        if match:
            return {
                'program_number': int(match.group(1)),
                'post_position': int(match.group(2)) if match.group(2) else int(match.group(1)),
                'win_pct': float(match.group(3)) if match.group(3) else None,
                'horse_name': match.group(4).strip(),
                'class_rating': self._parse_int(match.group(5))
            }
            
        # Pattern 2: Simple format - just number and horse name
        match = re.match(r'^(\d{1,2})\s+([A-Z][A-Z0-9\s\'\-]+)', line)
        if match:
            # Make sure it's not all numbers after the program number
            horse_name = match.group(2).strip()
            if not horse_name.replace(' ', '').isdigit():
                return {
                    'program_number': int(match.group(1)),
                    'post_position': int(match.group(1)),
                    'horse_name': horse_name
                }
                
        # Pattern 3: Line starting with number and containing uppercase words
        if re.match(r'^\d{1,2}\s+', line):
            parts = line.split(None, 1)
            if len(parts) == 2:
                pgm = int(parts[0])
                rest = parts[1]
                
                # Look for consecutive uppercase words (likely horse name)
                horse_match = re.search(r'([A-Z]{2,}(?:\s+[A-Z][A-Z0-9\'\-]*)*)', rest)
                if horse_match:
                    return {
                        'program_number': pgm,
                        'post_position': pgm,
                        'horse_name': horse_match.group(1).strip()
                    }
                    
        return None
    
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