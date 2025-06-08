"""World-Class PDF Parser for Horse Racing Data
Handles multiple formats, edge cases, and provides confidence scoring
"""
import re
import logging
import json
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from collections import defaultdict

logger = logging.getLogger(__name__)

class ExtractionMethod(Enum):
    """PDF extraction methods"""
    PYPDF2 = "pypdf2"
    PDFPLUMBER = "pdfplumber"
    PYMUPDF = "pymupdf"

@dataclass
class ParsedEntry:
    """Structured entry data with confidence scores"""
    program_number: int
    post_position: Optional[int] = None
    horse_name: str = ""
    jockey: Optional[str] = None
    trainer: Optional[str] = None
    win_pct: Optional[float] = None
    class_rating: Optional[int] = None
    last_speed: Optional[int] = None
    avg_speed: Optional[int] = None
    best_speed: Optional[int] = None
    jockey_win_pct: Optional[float] = None
    trainer_win_pct: Optional[float] = None
    jt_combo_pct: Optional[float] = None
    morning_line_odds: Optional[str] = None
    weight: Optional[int] = None
    medication: Optional[str] = None
    equipment: Optional[str] = None
    confidence: float = 0.0
    extraction_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for compatibility"""
        return {k: v for k, v in self.__dict__.items() 
                if not k.startswith('_') and k not in ['confidence', 'extraction_notes']}

@dataclass
class ParsedRace:
    """Structured race data with metadata"""
    race_number: int
    track: str = "Fair Meadows"
    distance: Optional[str] = None
    race_type: Optional[str] = None
    purse: Optional[int] = None
    post_time: Optional[str] = None
    surface: str = "Dirt"
    race_date: Optional[date] = None
    conditions: Optional[str] = None
    claiming_price: Optional[int] = None
    entries: List[ParsedEntry] = field(default_factory=list)
    confidence: float = 0.0
    extraction_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for compatibility"""
        result = {k: v for k, v in self.__dict__.items() 
                 if not k.startswith('_') and k not in ['confidence', 'extraction_notes', 'entries']}
        result['entries'] = [e.to_dict() for e in self.entries]
        if self.race_date:
            result['race_date'] = self.race_date.isoformat()
        return result

class AdvancedPDFParser:
    """World-class PDF parser with multiple strategies and error recovery"""
    
    def __init__(self):
        # Common patterns
        self.patterns = {
            'date': [
                (r'(\w+),\s+(\w+)\s+(\d{1,2}),\s+(\d{4})', '%A, %B %d, %Y'),
                (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
                (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
                (r'(\w{3})\s+(\d{1,2}),\s+(\d{4})', '%b %d, %Y')
            ],
            'distance': r'(\d+(?:\s+\d+/\d+)?)\s*(Yards?|Furlongs?|Miles?)',
            'purse': r'Purse[:\s]+\$?([\d,]+)',
            'post_time': r'Post\s*Time[:\s]+(\d{1,2}:\d{2})\s*(PM|AM|[AP])?',
            'race_type': r'(MAIDEN|CLAIMING|ALLOWANCE|STAKES|HANDICAP)',
            'claiming_price': r'Claiming\s*Price[:\s]+\$?([\d,]+)',
            'track_condition': r'Track[:\s]+(Fast|Good|Muddy|Sloppy|Firm|Soft|Heavy)',
            'odds': r'(\d+[-/]\d+|\d+\.\d+|EVEN|EVN)',
            'weight': r'(\d{2,3})\s*(?:lbs?)?',
            'medication': r'(L|B|BL|LB)',
            'equipment': r'(b|f|x|bf|bx)'
        }
        
        # Column headers to identify table structures
        self.column_headers = {
            'entry': ['Pgm', 'PP', 'Horse', 'Jockey', 'Trainer', 'Wt', 'M/L'],
            'stats': ['Win%', 'Class', 'Speed', 'Last', 'Avg', 'Best'],
            'jockey_trainer': ['Jky%', 'Tr%', 'J/T%', 'JT%']
        }
        
        # Track name variations
        self.track_names = {
            'FMT': 'Fair Meadows Tulsa',
            'Fair Meadows': 'Fair Meadows Tulsa',
            'Remington': 'Remington Park',
            'RP': 'Remington Park'
        }
        
    def parse_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Parse PDF using multiple strategies with fallback"""
        logger.info(f"Starting advanced PDF parsing for: {pdf_path}")
        
        # Try multiple extraction methods
        all_extractions = []
        
        # Method 1: PyPDF2
        try:
            text_pypdf2 = self._extract_text_pypdf2(pdf_path)
            if text_pypdf2:
                races = self._parse_with_confidence(text_pypdf2, ExtractionMethod.PYPDF2)
                if races:
                    all_extractions.append((races, self._calculate_extraction_confidence(races)))
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")
        
        # Method 2: pdfplumber (better for tables)
        try:
            text_plumber, tables = self._extract_text_pdfplumber(pdf_path)
            if text_plumber or tables:
                races = self._parse_with_tables(text_plumber, tables, ExtractionMethod.PDFPLUMBER)
                if races:
                    all_extractions.append((races, self._calculate_extraction_confidence(races)))
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Method 3: PyMuPDF (handles complex layouts)
        try:
            text_mupdf, blocks = self._extract_text_pymupdf(pdf_path)
            if text_mupdf:
                races = self._parse_with_blocks(text_mupdf, blocks, ExtractionMethod.PYMUPDF)
                if races:
                    all_extractions.append((races, self._calculate_extraction_confidence(races)))
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
        
        # Choose best extraction based on confidence
        if all_extractions:
            best_races, best_confidence = max(all_extractions, key=lambda x: x[1])
            logger.info(f"Selected extraction with confidence: {best_confidence:.2f}")
            
            # Convert to dictionary format
            return [race.to_dict() for race in best_races]
        
        logger.error("All extraction methods failed")
        return []
    
    def _extract_text_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2"""
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def _extract_text_pdfplumber(self, pdf_path: str) -> Tuple[str, List[Any]]:
        """Extract text and tables using pdfplumber"""
        text = ""
        all_tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
        
        return text, all_tables
    
    def _extract_text_pymupdf(self, pdf_path: str) -> Tuple[str, List[Any]]:
        """Extract text and layout blocks using PyMuPDF"""
        text = ""
        all_blocks = []
        
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text() + "\n"
            blocks = page.get_text("blocks")
            all_blocks.extend(blocks)
        doc.close()
        
        return text, all_blocks
    
    def _parse_with_confidence(self, text: str, method: ExtractionMethod) -> List[ParsedRace]:
        """Parse text with confidence scoring"""
        races = []
        
        # Extract global date
        race_date = self._extract_date(text)
        
        # Try multiple race splitting strategies
        race_texts = self._split_races(text)
        
        for race_num, race_text in race_texts:
            race = self._parse_single_race(race_num, race_text, race_date)
            if race and race.entries:
                race.extraction_notes.append(f"Extracted via {method.value}")
                races.append(race)
        
        return races
    
    def _parse_with_tables(self, text: str, tables: List[Any], method: ExtractionMethod) -> List[ParsedRace]:
        """Parse using table data"""
        races = []
        race_date = self._extract_date(text)
        
        # Group tables by race
        race_tables = self._group_tables_by_race(text, tables)
        
        for race_num, table_data in race_tables.items():
            race = ParsedRace(race_number=race_num, race_date=race_date)
            
            # Extract race details from text
            race_text = table_data.get('text', '')
            self._extract_race_details(race, race_text)
            
            # Parse entries from table
            if 'table' in table_data:
                entries = self._parse_table_entries(table_data['table'])
                race.entries = entries
                
            if race.entries:
                race.extraction_notes.append(f"Extracted via {method.value} with tables")
                races.append(race)
        
        return races
    
    def _parse_with_blocks(self, text: str, blocks: List[Any], method: ExtractionMethod) -> List[ParsedRace]:
        """Parse using layout blocks"""
        races = []
        race_date = self._extract_date(text)
        
        # Organize blocks by position
        organized_blocks = self._organize_blocks(blocks)
        
        # Parse races from organized blocks
        for race_data in organized_blocks:
            race = self._parse_from_blocks(race_data, race_date)
            if race and race.entries:
                race.extraction_notes.append(f"Extracted via {method.value} with layout analysis")
                races.append(race)
        
        return races
    
    def _split_races(self, text: str) -> List[Tuple[int, str]]:
        """Split text into individual races using multiple strategies"""
        races = []
        
        # Strategy 1: Split by race markers
        patterns = [
            r'Race\s+(\d+)\s*[\r\n]',
            r'(\d+)(?:st|nd|rd|th)\s+Race',
            r'RACE\s+(\d+)',
            r'(\d+)\s*\$2\s*Exacta',
            r'Race\s*#\s*(\d+)'
        ]
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if len(matches) > 1:
                for i in range(len(matches)):
                    start = matches[i].start()
                    end = matches[i+1].start() if i+1 < len(matches) else len(text)
                    race_num = int(matches[i].group(1))
                    race_text = text[start:end]
                    races.append((race_num, race_text))
                break
        
        # Strategy 2: If no clear markers, look for entry patterns
        if not races:
            # Look for repeating patterns of entries
            entry_pattern = r'^\s*(\d{1,2})\s+(\d{1,2})\s+\(?\d+%?\)?'
            lines = text.split('\n')
            current_race = 1
            current_text = []
            
            for line in lines:
                if re.match(entry_pattern, line):
                    current_text.append(line)
                elif current_text and len(current_text) > 2:
                    races.append((current_race, '\n'.join(current_text)))
                    current_race += 1
                    current_text = []
        
        return races
    
    def _parse_single_race(self, race_num: int, text: str, race_date: date) -> ParsedRace:
        """Parse a single race with comprehensive extraction"""
        race = ParsedRace(race_number=race_num, race_date=race_date)
        
        # Extract race details
        self._extract_race_details(race, text)
        
        # Parse entries using multiple strategies
        entries = self._parse_entries_comprehensive(text)
        race.entries = entries
        
        # Calculate confidence
        race.confidence = self._calculate_race_confidence(race)
        
        return race
    
    def _extract_race_details(self, race: ParsedRace, text: str):
        """Extract comprehensive race details"""
        lines = text[:1000].split('\n')  # Focus on header area
        
        for line in lines:
            # Distance
            if not race.distance:
                match = re.search(self.patterns['distance'], line)
                if match:
                    race.distance = f"{match.group(1)} {match.group(2)}"
            
            # Race type
            if not race.race_type:
                match = re.search(self.patterns['race_type'], line, re.IGNORECASE)
                if match:
                    race.race_type = match.group(1).upper()
            
            # Purse
            if not race.purse:
                match = re.search(self.patterns['purse'], line, re.IGNORECASE)
                if match:
                    race.purse = int(match.group(1).replace(',', ''))
            
            # Post time
            if not race.post_time:
                match = re.search(self.patterns['post_time'], line, re.IGNORECASE)
                if match:
                    time = match.group(1)
                    period = match.group(2)
                    if period and period.upper() in ['PM', 'P']:
                        hour, minute = map(int, time.split(':'))
                        if hour != 12:
                            hour += 12
                        race.post_time = f"{hour}:{minute:02d}"
                    else:
                        race.post_time = time
            
            # Claiming price
            if 'CLAIMING' in race.race_type and not race.claiming_price:
                match = re.search(self.patterns['claiming_price'], line, re.IGNORECASE)
                if match:
                    race.claiming_price = int(match.group(1).replace(',', ''))
            
            # Track condition
            match = re.search(self.patterns['track_condition'], line, re.IGNORECASE)
            if match:
                race.conditions = match.group(1)
            
            # Track name
            for abbrev, full_name in self.track_names.items():
                if abbrev in line:
                    race.track = full_name
                    break
    
    def _parse_entries_comprehensive(self, text: str) -> List[ParsedEntry]:
        """Parse entries using multiple strategies"""
        entries = []
        
        # Strategy 1: Line-by-line parsing
        line_entries = self._parse_entries_by_line(text)
        
        # Strategy 2: Column-based parsing
        column_entries = self._parse_entries_by_columns(text)
        
        # Strategy 3: Pattern matching
        pattern_entries = self._parse_entries_by_pattern(text)
        
        # Merge and deduplicate entries
        all_entries = self._merge_entries(line_entries, column_entries, pattern_entries)
        
        return all_entries
    
    def _parse_entries_by_line(self, text: str) -> List[ParsedEntry]:
        """Parse entries line by line"""
        entries = []
        lines = text.split('\n')
        
        for line in lines:
            # Skip headers and empty lines
            if not line.strip() or any(header in line for header in ['Pgm', 'Horse', 'Jockey', 'Copyright']):
                continue
            
            # Try to parse entry
            entry = self._parse_entry_line(line)
            if entry and entry.horse_name:
                entries.append(entry)
        
        return entries
    
    def _parse_entry_line(self, line: str) -> Optional[ParsedEntry]:
        """Parse a single entry line"""
        # Remove extra spaces and normalize
        line = ' '.join(line.split())
        
        # Pattern for entry line
        # Example: 1 1 (16%) SMACKZILLA 0 78 78 78 Silva A / 12% 13% 17%
        match = re.match(r'^(\d{1,2})\s+(\d{1,2})\s+\(?([\d.]+)%?\)?\s+([A-Z][A-Z\s\']+?)(?:\s+(\d+|NA)\s+(\d+|NA)\s+(\d+|NA)\s+(\d+|NA))?\s*(.*)$', line)
        
        if not match:
            return None
        
        entry = ParsedEntry(
            program_number=int(match.group(1)),
            post_position=int(match.group(2)),
            win_pct=float(match.group(3)) if match.group(3) else None,
            horse_name=match.group(4).strip()
        )
        
        # Parse speed figures if present
        if match.group(5):
            entry.class_rating = self._parse_int_or_na(match.group(5))
            entry.last_speed = self._parse_int_or_na(match.group(6))
            entry.avg_speed = self._parse_int_or_na(match.group(7))
            entry.best_speed = self._parse_int_or_na(match.group(8))
        
        # Parse jockey/trainer info
        if match.group(9):
            self._parse_jockey_trainer(entry, match.group(9))
        
        return entry
    
    def _parse_jockey_trainer(self, entry: ParsedEntry, text: str):
        """Parse jockey and trainer information"""
        # Look for slash separator
        if '/' in text:
            parts = text.split('/')
            jockey_part = parts[0].strip()
            trainer_part = parts[1].strip() if len(parts) > 1 else ""
            
            # Extract jockey
            jockey_match = re.match(r'^([A-Za-z\s]+?)(?:\s+(\d+)%)?', jockey_part)
            if jockey_match:
                entry.jockey = jockey_match.group(1).strip()
                if jockey_match.group(2):
                    entry.jockey_win_pct = float(jockey_match.group(2))
            
            # Extract trainer and percentages
            pct_matches = re.findall(r'(\d+)%', trainer_part)
            if pct_matches:
                if len(pct_matches) >= 2:
                    entry.trainer_win_pct = float(pct_matches[0])
                    entry.jt_combo_pct = float(pct_matches[1])
                elif len(pct_matches) == 1:
                    entry.trainer_win_pct = float(pct_matches[0])
            
            # Extract trainer name (text before percentages)
            trainer_match = re.match(r'^([A-Za-z\s]+?)(?:\s+\d+%)', trainer_part)
            if trainer_match:
                entry.trainer = trainer_match.group(1).strip()
    
    def _parse_entries_by_columns(self, text: str) -> List[ParsedEntry]:
        """Parse entries by detecting column structure"""
        entries = []
        lines = text.split('\n')
        
        # Find header line
        header_idx = -1
        for i, line in enumerate(lines):
            if 'Pgm' in line and ('Horse' in line or 'PP' in line):
                header_idx = i
                break
        
        if header_idx == -1:
            return entries
        
        # Detect column positions
        header = lines[header_idx]
        columns = self._detect_columns(header)
        
        # Parse data lines
        for i in range(header_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            
            entry = self._parse_by_columns(line, columns)
            if entry and entry.horse_name:
                entries.append(entry)
        
        return entries
    
    def _detect_columns(self, header: str) -> Dict[str, Tuple[int, int]]:
        """Detect column positions from header"""
        columns = {}
        
        # Common column names and their variations
        column_patterns = {
            'pgm': r'Pgm|PGM|Program',
            'pp': r'PP|Post',
            'horse': r'Horse|HORSE|Name',
            'jockey': r'Jockey|Jky|JOCKEY',
            'trainer': r'Trainer|Tr|TRAINER',
            'ml': r'M/?L|ML|Morning',
            'weight': r'Wt|Weight|WT'
        }
        
        for col_name, pattern in column_patterns.items():
            match = re.search(pattern, header, re.IGNORECASE)
            if match:
                start = match.start()
                # Find end by looking for next column or end of line
                end = len(header)
                for other_pattern in column_patterns.values():
                    if other_pattern != pattern:
                        other_match = re.search(other_pattern, header[start+1:], re.IGNORECASE)
                        if other_match:
                            end = min(end, start + 1 + other_match.start())
                columns[col_name] = (start, end)
        
        return columns
    
    def _parse_by_columns(self, line: str, columns: Dict[str, Tuple[int, int]]) -> Optional[ParsedEntry]:
        """Parse entry using column positions"""
        if len(line) < 20:  # Too short to be a valid entry
            return None
        
        entry = ParsedEntry(program_number=0)
        
        # Extract by column positions
        for col_name, (start, end) in columns.items():
            if start < len(line):
                value = line[start:min(end, len(line))].strip()
                
                if col_name == 'pgm' and value.isdigit():
                    entry.program_number = int(value)
                elif col_name == 'pp' and value.isdigit():
                    entry.post_position = int(value)
                elif col_name == 'horse':
                    entry.horse_name = value
                elif col_name == 'jockey':
                    entry.jockey = value
                elif col_name == 'trainer':
                    entry.trainer = value
                elif col_name == 'ml':
                    entry.morning_line_odds = value
                elif col_name == 'weight' and value.isdigit():
                    entry.weight = int(value)
        
        return entry if entry.program_number > 0 else None
    
    def _parse_entries_by_pattern(self, text: str) -> List[ParsedEntry]:
        """Parse entries using regex patterns"""
        entries = []
        
        # Comprehensive entry pattern
        entry_pattern = re.compile(
            r'^(\d{1,2})\s+'  # Program number
            r'(\d{1,2})?\s*'  # Post position (optional)
            r'\(?([\d.]+)%?\)?\s*'  # Win percentage
            r'([A-Z][A-Z\s\']+?)\s+'  # Horse name
            r'(?:(\d+|NA)\s+)?'  # Class rating
            r'(?:(\d+|NA)\s+)?'  # Last speed
            r'(?:(\d+|NA)\s+)?'  # Avg speed
            r'(?:(\d+|NA)\s+)?'  # Best speed
            r'(.+)?$',  # Remaining text (jockey/trainer/percentages)
            re.MULTILINE
        )
        
        for match in entry_pattern.finditer(text):
            entry = ParsedEntry(
                program_number=int(match.group(1)),
                post_position=int(match.group(2)) if match.group(2) else None,
                win_pct=float(match.group(3)) if match.group(3) else None,
                horse_name=match.group(4).strip()
            )
            
            if match.group(5):
                entry.class_rating = self._parse_int_or_na(match.group(5))
            if match.group(6):
                entry.last_speed = self._parse_int_or_na(match.group(6))
            if match.group(7):
                entry.avg_speed = self._parse_int_or_na(match.group(7))
            if match.group(8):
                entry.best_speed = self._parse_int_or_na(match.group(8))
            
            if match.group(9):
                self._parse_jockey_trainer(entry, match.group(9))
            
            entries.append(entry)
        
        return entries
    
    def _parse_table_entries(self, table: List[List[str]]) -> List[ParsedEntry]:
        """Parse entries from table data"""
        entries = []
        
        if not table or len(table) < 2:
            return entries
        
        # Find header row
        header_row = None
        header_idx = 0
        for i, row in enumerate(table):
            if any('pgm' in str(cell).lower() or 'horse' in str(cell).lower() for cell in row):
                header_row = [str(cell).lower() for cell in row]
                header_idx = i
                break
        
        if not header_row:
            return entries
        
        # Map column indices
        col_map = {}
        for i, cell in enumerate(header_row):
            if 'pgm' in cell or 'program' in cell:
                col_map['pgm'] = i
            elif 'pp' in cell or 'post' in cell:
                col_map['pp'] = i
            elif 'horse' in cell or 'name' in cell:
                col_map['horse'] = i
            elif 'jockey' in cell or 'jky' in cell:
                col_map['jockey'] = i
            elif 'trainer' in cell or 'tr' in cell:
                col_map['trainer'] = i
            elif 'win' in cell and '%' in cell:
                col_map['win_pct'] = i
            elif 'class' in cell:
                col_map['class'] = i
            elif 'last' in cell:
                col_map['last'] = i
            elif 'avg' in cell:
                col_map['avg'] = i
            elif 'best' in cell:
                col_map['best'] = i
        
        # Parse data rows
        for row in table[header_idx + 1:]:
            if len(row) < 3:  # Skip invalid rows
                continue
            
            entry = ParsedEntry(program_number=0)
            
            # Extract values
            if 'pgm' in col_map and col_map['pgm'] < len(row):
                val = str(row[col_map['pgm']]).strip()
                if val.isdigit():
                    entry.program_number = int(val)
            
            if 'pp' in col_map and col_map['pp'] < len(row):
                val = str(row[col_map['pp']]).strip()
                if val.isdigit():
                    entry.post_position = int(val)
            
            if 'horse' in col_map and col_map['horse'] < len(row):
                entry.horse_name = str(row[col_map['horse']]).strip()
            
            if 'jockey' in col_map and col_map['jockey'] < len(row):
                entry.jockey = str(row[col_map['jockey']]).strip()
            
            if 'trainer' in col_map and col_map['trainer'] < len(row):
                entry.trainer = str(row[col_map['trainer']]).strip()
            
            if entry.program_number > 0 and entry.horse_name:
                entries.append(entry)
        
        return entries
    
    def _group_tables_by_race(self, text: str, tables: List[Any]) -> Dict[int, Dict]:
        """Group tables by race number"""
        race_tables = defaultdict(dict)
        
        # Split text by races
        race_texts = self._split_races(text)
        
        # Try to associate tables with races
        for table in tables:
            # Look for race indicators near table
            best_race = 1
            race_tables[best_race]['table'] = table
        
        # Add race text
        for race_num, race_text in race_texts:
            if race_num in race_tables:
                race_tables[race_num]['text'] = race_text
            else:
                race_tables[race_num] = {'text': race_text}
        
        return dict(race_tables)
    
    def _organize_blocks(self, blocks: List[Any]) -> List[Dict]:
        """Organize text blocks by spatial layout"""
        # Group blocks by vertical position (y-coordinate)
        organized = []
        
        # Sort blocks by position
        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))  # Sort by y, then x
        
        # Group into races (simplified)
        current_race = {'blocks': []}
        for block in sorted_blocks:
            text = block[4] if len(block) > 4 else ""
            if re.search(r'Race\s+\d+', text, re.IGNORECASE):
                if current_race['blocks']:
                    organized.append(current_race)
                current_race = {'blocks': [block]}
            else:
                current_race['blocks'].append(block)
        
        if current_race['blocks']:
            organized.append(current_race)
        
        return organized
    
    def _parse_from_blocks(self, race_data: Dict, race_date: date) -> Optional[ParsedRace]:
        """Parse race from organized blocks"""
        if not race_data.get('blocks'):
            return None
        
        # Combine block text
        text = '\n'.join(block[4] for block in race_data['blocks'] if len(block) > 4)
        
        # Extract race number
        race_num_match = re.search(r'Race\s+(\d+)', text, re.IGNORECASE)
        if not race_num_match:
            return None
        
        race_num = int(race_num_match.group(1))
        return self._parse_single_race(race_num, text, race_date)
    
    def _merge_entries(self, *entry_lists) -> List[ParsedEntry]:
        """Merge and deduplicate entries from multiple sources"""
        merged = {}
        
        for entries in entry_lists:
            for entry in entries:
                key = (entry.program_number, entry.horse_name.upper())
                
                if key not in merged:
                    merged[key] = entry
                else:
                    # Merge data from multiple sources
                    existing = merged[key]
                    for field in ['post_position', 'jockey', 'trainer', 'win_pct', 
                                 'class_rating', 'last_speed', 'avg_speed', 'best_speed',
                                 'jockey_win_pct', 'trainer_win_pct', 'jt_combo_pct',
                                 'morning_line_odds', 'weight']:
                        if not getattr(existing, field) and getattr(entry, field):
                            setattr(existing, field, getattr(entry, field))
        
        # Sort by program number
        return sorted(merged.values(), key=lambda e: e.program_number)
    
    def _extract_date(self, text: str) -> date:
        """Extract race date with multiple patterns"""
        for pattern, date_format in self.patterns['date']:
            match = re.search(pattern, text[:500], re.IGNORECASE)  # Check first 500 chars
            if match:
                try:
                    if '%A' in date_format or '%B' in date_format:
                        # Handle named months
                        date_str = match.group(0)
                        return datetime.strptime(date_str, date_format).date()
                    else:
                        # Handle numeric dates
                        return datetime.strptime(match.group(0), date_format).date()
                except:
                    continue
        
        # Default to today
        logger.warning("Could not extract date, using today")
        return datetime.now().date()
    
    def _parse_int_or_na(self, value: str) -> Optional[int]:
        """Parse integer or return None for NA"""
        if not value or value.upper() == 'NA':
            return None
        try:
            return int(value)
        except:
            return None
    
    def _calculate_extraction_confidence(self, races: List[ParsedRace]) -> float:
        """Calculate overall extraction confidence"""
        if not races:
            return 0.0
        
        total_confidence = 0.0
        total_entries = 0
        
        for race in races:
            race_confidence = self._calculate_race_confidence(race)
            total_confidence += race_confidence * len(race.entries)
            total_entries += len(race.entries)
        
        return total_confidence / total_entries if total_entries > 0 else 0.0
    
    def _calculate_race_confidence(self, race: ParsedRace) -> float:
        """Calculate confidence score for a race"""
        score = 0.0
        max_score = 0.0
        
        # Race details
        if race.distance:
            score += 10
        max_score += 10
        
        if race.race_type:
            score += 10
        max_score += 10
        
        if race.purse:
            score += 5
        max_score += 5
        
        if race.post_time:
            score += 5
        max_score += 5
        
        # Entry quality
        for entry in race.entries:
            entry_score = 0.0
            entry_max = 0.0
            
            # Required fields
            if entry.horse_name:
                entry_score += 20
            entry_max += 20
            
            if entry.program_number > 0:
                entry_score += 10
            entry_max += 10
            
            # Optional fields
            optional_fields = [
                'jockey', 'trainer', 'win_pct', 'class_rating',
                'last_speed', 'avg_speed', 'best_speed'
            ]
            
            for field in optional_fields:
                if getattr(entry, field):
                    entry_score += 5
                entry_max += 5
            
            entry.confidence = entry_score / entry_max if entry_max > 0 else 0.0
            score += entry_score
            max_score += entry_max
        
        race.confidence = score / max_score if max_score > 0 else 0.0
        return race.confidence


# Backwards compatibility wrapper
class EquibasePDFParser:
    """Wrapper for backwards compatibility"""
    
    def __init__(self):
        self.parser = AdvancedPDFParser()
    
    def parse_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Parse PDF file using advanced parser"""
        return self.parser.parse_pdf_file(pdf_path)