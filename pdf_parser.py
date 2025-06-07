"""
PDF Parser for Equibase Chart Files
Extracts race data including entries, morning line odds, and race details
"""
import os
import re
import logging
from datetime import datetime, date, time
from typing import List, Dict, Optional, Tuple
import pdfplumber
import PyPDF2
from tabula import read_pdf
import pandas as pd

logger = logging.getLogger(__name__)


class EquibasePDFParser:
    """Parse Equibase PDF chart files to extract race data"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.track_patterns = {
            'FMT': 'Fonner Park',
            'GP': 'Gulfstream Park',
            'SA': 'Santa Anita',
            'CD': 'Churchill Downs',
            'BEL': 'Belmont Park',
            'AQU': 'Aqueduct',
            'KEE': 'Keeneland',
            'DMR': 'Del Mar',
            'SAR': 'Saratoga'
        }
    
    def parse_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Parse a single PDF file and return list of races"""
        logger.info(f"Parsing PDF file: {pdf_path}")
        
        races = []
        
        # Try multiple parsing methods
        try:
            # Method 1: pdfplumber (best for text extraction)
            races = self._parse_with_pdfplumber(pdf_path)
            
            if not races:
                # Method 2: tabula-py (best for tables)
                races = self._parse_with_tabula(pdf_path)
            
            if not races:
                # Method 3: PyPDF2 (fallback)
                races = self._parse_with_pypdf2(pdf_path)
                
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {e}")
            
        return races
    
    def _parse_with_pdfplumber(self, pdf_path: str) -> List[Dict]:
        """Parse PDF using pdfplumber library"""
        races = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    tables = page.extract_tables()
                    
                    # Extract race date from filename or header
                    race_date = self._extract_date(pdf_path, text)
                    
                    # Parse races from text
                    page_races = self._parse_text_content(text, race_date)
                    races.extend(page_races)
                    
                    # Parse races from tables
                    for table in tables:
                        table_races = self._parse_table_content(table, race_date)
                        races.extend(table_races)
                        
        except Exception as e:
            logger.error(f"pdfplumber error: {e}")
            
        return races
    
    def _parse_with_tabula(self, pdf_path: str) -> List[Dict]:
        """Parse PDF using tabula-py for table extraction"""
        races = []
        
        try:
            # Read all tables from PDF
            tables = read_pdf(pdf_path, pages='all', multiple_tables=True)
            
            # Extract date from filename
            race_date = self._extract_date_from_filename(pdf_path)
            
            for df in tables:
                if df.empty:
                    continue
                    
                # Try to identify if this is a race entries table
                if self._is_entries_table(df):
                    race = self._parse_entries_dataframe(df, race_date)
                    if race:
                        races.append(race)
                        
        except Exception as e:
            logger.error(f"tabula-py error: {e}")
            
        return races
    
    def _parse_with_pypdf2(self, pdf_path: str) -> List[Dict]:
        """Parse PDF using PyPDF2 as fallback"""
        races = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                full_text = ""
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    full_text += page.extract_text()
                
                # Extract date and parse content
                race_date = self._extract_date(pdf_path, full_text)
                races = self._parse_text_content(full_text, race_date)
                
        except Exception as e:
            logger.error(f"PyPDF2 error: {e}")
            
        return races
    
    def _parse_text_content(self, text: str, race_date: date) -> List[Dict]:
        """Parse race data from text content"""
        races = []
        
        # Split by race markers
        race_sections = self._split_by_races(text)
        
        for section in race_sections:
            race = self._parse_race_section(section, race_date)
            if race and race.get('horses'):
                races.append(race)
                
        return races
    
    def _split_by_races(self, text: str) -> List[str]:
        """Split text into individual race sections"""
        sections = []
        
        # Common race markers
        markers = [
            r'RACE\s+(\d+)',
            r'(\d+)(?:ST|ND|RD|TH)\s+RACE',
            r'Race\s+(\d+)',
            r'RACE NUMBER\s+(\d+)'
        ]
        
        # Find all race markers
        positions = []
        for marker in markers:
            for match in re.finditer(marker, text, re.IGNORECASE):
                positions.append((match.start(), match.group(1)))
        
        # Sort by position
        positions.sort(key=lambda x: x[0])
        
        # Extract sections
        for i, (pos, race_num) in enumerate(positions):
            end_pos = positions[i+1][0] if i+1 < len(positions) else len(text)
            section = text[pos:end_pos]
            sections.append(section)
            
        return sections
    
    def _parse_race_section(self, section: str, race_date: date) -> Dict:
        """Parse a single race section"""
        race = {
            'date': race_date,
            'horses': []
        }
        
        # Extract race number
        race_num_match = re.search(r'RACE\s+(\d+)', section, re.IGNORECASE)
        if race_num_match:
            race['race_number'] = int(race_num_match.group(1))
        
        # Extract track name
        race['track_name'] = self._extract_track_name(section)
        
        # Extract post time
        post_time = self._extract_post_time(section)
        if post_time:
            race['post_time'] = post_time
        
        # Extract distance
        distance = self._extract_distance(section)
        if distance:
            race['distance'] = distance
        
        # Extract purse
        purse = self._extract_purse(section)
        if purse:
            race['purse'] = purse
        
        # Extract race type
        race_type = self._extract_race_type(section)
        if race_type:
            race['race_type'] = race_type
        
        # Extract horses
        horses = self._extract_horses(section)
        race['horses'] = horses
        
        return race
    
    def _extract_horses(self, text: str) -> List[Dict]:
        """Extract horse entries from race text"""
        horses = []
        
        # Pattern for horse entries (multiple variations)
        patterns = [
            # Pattern 1: Program# Horse Name M/L Jockey Trainer
            r'(\d+)\s+([A-Z][A-Za-z\s\']+?)(?:\s+\(L\))?\s+(\d+(?:-\d+)?)\s+([A-Z][A-Za-z\s\.]+?)\s+([A-Z][A-Za-z\s\.]+?)(?:\s+\d+)?$',
            # Pattern 2: Number. Horse Name - Jockey/Trainer ML
            r'(\d+)\.\s*([A-Z][A-Za-z\s\']+?)\s*[-–]\s*([A-Za-z\s\.]+?)/([A-Za-z\s\.]+?)\s+(\d+-\d+)',
            # Pattern 3: Simple format
            r'(\d+)\s+([A-Z][A-Za-z\s\']+?)\s+(\d+-\d+)',
        ]
        
        # Try each pattern
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                horse = self._create_horse_entry(match, pattern)
                if horse and self._is_valid_horse(horse):
                    horses.append(horse)
            
            if horses:
                break
        
        # If no horses found, try line-by-line parsing
        if not horses:
            horses = self._parse_horses_by_lines(text)
        
        return horses
    
    def _create_horse_entry(self, match: re.Match, pattern: str) -> Dict:
        """Create horse entry from regex match"""
        groups = match.groups()
        
        horse = {}
        
        # Determine format based on number of groups
        if len(groups) == 5:
            # Full format with all details
            horse = {
                'program_number': int(groups[0]),
                'horse_name': groups[1].strip(),
                'morning_line_odds': groups[2],
                'jockey': groups[3].strip(),
                'trainer': groups[4].strip()
            }
        elif len(groups) == 4:
            # Format without ML odds in expected position
            horse = {
                'program_number': int(groups[0]),
                'horse_name': groups[1].strip(),
                'jockey': groups[2].strip(),
                'trainer': groups[3].strip()
            }
        elif len(groups) == 3:
            # Simple format
            horse = {
                'program_number': int(groups[0]),
                'horse_name': groups[1].strip(),
                'morning_line_odds': groups[2]
            }
            
        return horse
    
    def _parse_horses_by_lines(self, text: str) -> List[Dict]:
        """Parse horses line by line when regex fails"""
        horses = []
        lines = text.split('\n')
        
        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or 'HORSE' in line.upper() or 'JOCKEY' in line.upper():
                continue
            
            # Look for lines starting with a number (program number)
            if re.match(r'^\d+\s', line):
                horse = self._parse_horse_line(line)
                if horse and self._is_valid_horse(horse):
                    horses.append(horse)
                    
        return horses
    
    def _parse_horse_line(self, line: str) -> Optional[Dict]:
        """Parse a single line containing horse data"""
        # Remove extra spaces and split
        parts = re.split(r'\s{2,}', line.strip())
        
        if len(parts) < 2:
            return None
        
        try:
            horse = {
                'program_number': int(parts[0]),
                'horse_name': parts[1]
            }
            
            # Try to identify other fields
            for part in parts[2:]:
                if re.match(r'\d+-\d+', part):
                    horse['morning_line_odds'] = part
                elif '.' in part and part.count('.') >= 2:
                    # Likely a jockey name (e.g., J. Smith)
                    horse['jockey'] = part
                elif part.isupper() or (part[0].isupper() and ' ' in part):
                    # Likely a trainer name
                    if 'trainer' not in horse:
                        horse['trainer'] = part
                        
            return horse
            
        except (ValueError, IndexError):
            return None
    
    def _is_valid_horse(self, horse: Dict) -> bool:
        """Check if horse entry is valid"""
        # Must have at least program number and name
        if not horse.get('program_number') or not horse.get('horse_name'):
            return False
        
        # Name shouldn't be a header or invalid entry
        invalid_names = ['horse', 'name', 'scratch', 'entry', 'program', 'number']
        if horse['horse_name'].lower() in invalid_names:
            return False
        
        # Program number should be reasonable (1-20)
        if horse['program_number'] < 1 or horse['program_number'] > 20:
            return False
        
        return True
    
    def _extract_date(self, filename: str, text: str) -> date:
        """Extract race date from filename or text"""
        # Try filename first
        date_from_filename = self._extract_date_from_filename(filename)
        if date_from_filename:
            return date_from_filename
        
        # Try text content
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            r'(\w+)\s+(\d{1,2}),\s+(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Parse based on pattern
                    if '/' in pattern or '-' in pattern:
                        return datetime.strptime(match.group(0), '%m/%d/%Y').date()
                    else:
                        return datetime.strptime(match.group(0), '%B %d, %Y').date()
                except:
                    continue
        
        # Default to today
        return datetime.now().date()
    
    def _extract_date_from_filename(self, filename: str) -> Optional[date]:
        """Extract date from filename like FMT060725USA-EQB.pdf"""
        # Pattern: FMT060725 -> 06/07/25
        match = re.search(r'(\d{6})', filename)
        if match:
            date_str = match.group(1)
            try:
                # Assume MMDDYY format
                month = int(date_str[0:2])
                day = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
                return date(year, month, day)
            except:
                pass
        return None
    
    def _extract_track_name(self, text: str) -> str:
        """Extract track name from text"""
        # Check for track codes
        for code, name in self.track_patterns.items():
            if code in text.upper():
                return name
        
        # Look for explicit track names
        track_match = re.search(r'(?:at|@)\s+([A-Z][A-Za-z\s]+(?:Park|Downs|Track))', text)
        if track_match:
            return track_match.group(1).strip()
        
        return "Fonner Park"  # Default
    
    def _extract_post_time(self, text: str) -> Optional[time]:
        """Extract post time from text"""
        patterns = [
            r'Post\s*Time:?\s*(\d{1,2}):(\d{2})\s*(PM|AM)?',
            r'Post:?\s*(\d{1,2}):(\d{2})\s*(PM|AM)?',
            r'(\d{1,2}):(\d{2})\s*(PM|AM)\s*Post'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                meridiem = match.group(3).upper() if match.group(3) else 'PM'
                
                if meridiem == 'PM' and hour != 12:
                    hour += 12
                elif meridiem == 'AM' and hour == 12:
                    hour = 0
                    
                return time(hour, minute)
        
        return None
    
    def _extract_distance(self, text: str) -> Optional[str]:
        """Extract race distance from text"""
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(Miles?|Furlongs?|Yards?|f)',
            r'Distance:?\s*(\d+(?:\.\d+)?)\s*(Miles?|Furlongs?|Yards?|f)',
            r'(\d+)\s*YDS',
            r'(\d+)F'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    def _extract_purse(self, text: str) -> Optional[int]:
        """Extract purse amount from text"""
        patterns = [
            r'\$(\d{1,3}(?:,\d{3})*)',
            r'Purse:?\s*\$?(\d{1,3}(?:,\d{3})*)',
            r'PURSE\s*\$?(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Remove commas and convert to int
                purse_str = match.group(1).replace(',', '')
                try:
                    return int(purse_str)
                except:
                    pass
        
        return None
    
    def _extract_race_type(self, text: str) -> Optional[str]:
        """Extract race type from text"""
        race_types = [
            'MAIDEN', 'CLAIMING', 'ALLOWANCE', 'STAKES',
            'HANDICAP', 'STARTER', 'TRIAL', 'OPTIONAL CLAIMING'
        ]
        
        for race_type in race_types:
            if race_type in text.upper():
                return race_type.title()
        
        return None
    
    def _parse_table_content(self, table: List[List], race_date: date) -> List[Dict]:
        """Parse race data from extracted table"""
        races = []
        
        # Convert table to DataFrame for easier handling
        if not table or len(table) < 2:
            return races
        
        try:
            df = pd.DataFrame(table[1:], columns=table[0])
            
            # Clean column names
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            # Look for horse entries table
            if self._is_entries_table(df):
                race = self._parse_entries_dataframe(df, race_date)
                if race:
                    races.append(race)
                    
        except Exception as e:
            logger.error(f"Table parsing error: {e}")
            
        return races
    
    def _is_entries_table(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame contains race entries"""
        # Check for common column patterns
        columns = [str(col).upper() for col in df.columns]
        
        entry_indicators = ['HORSE', 'JOCKEY', 'TRAINER', 'PP', 'ML', 'ODDS']
        matches = sum(1 for indicator in entry_indicators if any(indicator in col for col in columns))
        
        return matches >= 2
    
    def _parse_entries_dataframe(self, df: pd.DataFrame, race_date: date) -> Optional[Dict]:
        """Parse entries from DataFrame"""
        race = {
            'date': race_date,
            'track_name': 'Fonner Park',
            'horses': []
        }
        
        # Map columns
        column_mapping = {
            'PP': 'program_number',
            'PROGRAM': 'program_number',
            'HORSE': 'horse_name',
            'HORSE NAME': 'horse_name',
            'JOCKEY': 'jockey',
            'TRAINER': 'trainer',
            'ML': 'morning_line_odds',
            'M/L': 'morning_line_odds',
            'MORNING LINE': 'morning_line_odds',
            'WT': 'weight',
            'WEIGHT': 'weight'
        }
        
        # Iterate through rows
        for _, row in df.iterrows():
            horse = {}
            
            for col in df.columns:
                col_upper = str(col).upper()
                for key, field in column_mapping.items():
                    if key in col_upper:
                        value = row[col]
                        if pd.notna(value) and str(value).strip():
                            if field == 'program_number':
                                try:
                                    horse[field] = int(value)
                                except:
                                    pass
                            else:
                                horse[field] = str(value).strip()
            
            if self._is_valid_horse(horse):
                race['horses'].append(horse)
        
        return race if race['horses'] else None
    
    def save_parsed_races(self, races: List[Dict]):
        """Save parsed races to database"""
        from database import Database
        db = Database(self.db_url)
        
        with db.get_cursor() as cur:
            for race in races:
                # Insert race
                cur.execute("""
                    INSERT INTO races (date, race_number, track_name, post_time, 
                                     purse, distance, surface, race_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, race_number, track_name) 
                    DO UPDATE SET 
                        post_time = EXCLUDED.post_time,
                        purse = EXCLUDED.purse,
                        distance = EXCLUDED.distance,
                        surface = EXCLUDED.surface,
                        race_type = EXCLUDED.race_type
                    RETURNING id
                """, (
                    race['date'], 
                    race.get('race_number', 1),
                    race['track_name'],
                    race.get('post_time'),
                    race.get('purse'),
                    race.get('distance'),
                    race.get('surface', 'Dirt'),
                    race.get('race_type')
                ))
                
                race_id = cur.fetchone()[0]
                
                # Delete existing horses
                cur.execute("DELETE FROM horses WHERE race_id = %s", (race_id,))
                
                # Insert horses
                for horse in race.get('horses', []):
                    cur.execute("""
                        INSERT INTO horses (race_id, program_number, horse_name, 
                                          jockey, trainer, morning_line_odds, weight)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        race_id,
                        horse.get('program_number'),
                        horse['horse_name'],
                        horse.get('jockey'),
                        horse.get('trainer'),
                        horse.get('morning_line_odds'),
                        horse.get('weight')
                    ))
                    
                    # If we have morning line odds, save to odds history
                    if horse.get('morning_line_odds'):
                        cur.execute("""
                            INSERT INTO odds_history (race_id, horse_id, odds_type, 
                                                    odds_value, captured_at, minutes_to_post)
                            SELECT %s, h.id, 'morning_line', %s, NOW(), NULL
                            FROM horses h
                            WHERE h.race_id = %s AND h.program_number = %s
                        """, (
                            race_id,
                            horse['morning_line_odds'],
                            race_id,
                            horse['program_number']
                        ))


def parse_pdf_file(pdf_path: str, db_url: str) -> Tuple[bool, str]:
    """Parse a PDF file and save to database"""
    try:
        parser = EquibasePDFParser(db_url)
        races = parser.parse_pdf_file(pdf_path)
        
        if races:
            parser.save_parsed_races(races)
            return True, f"Successfully parsed {len(races)} races from PDF"
        else:
            return False, "No races found in PDF"
            
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        return False, f"Error parsing PDF: {str(e)}"