"""PDF Parser for horse racing data files"""
import logging
import re
from typing import List, Dict, Optional
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)

class RacingPDFParser:
    """Parse PDF racing data files by converting to text first"""
    
    def __init__(self):
        # Common patterns for parsing racing data from text
        self.patterns = {
            'race_header': re.compile(r'RACE\s+(\d+)', re.IGNORECASE),
            'track': re.compile(r'(?:Track|Racetrack):\s*([^\n]+)', re.IGNORECASE),
            'date': re.compile(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(\w+\s+\d{1,2},?\s+\d{4})'),
            'distance': re.compile(r'(\d+(?:\.\d+)?)\s*(furlongs?|f|yards?|y|miles?|m)', re.IGNORECASE),
            'purse': re.compile(r'\$\s*(\d{1,3}(?:,\d{3})*)', re.IGNORECASE),
            'horse_entry': re.compile(r'^\s*(\d+)\s+([A-Za-z\s\'-]+?)\s+(\d+(?:\.\d+)?)', re.MULTILINE),
        }
    
    def parse_pdf_file(self, pdf_path: str) -> List[Dict]:
        """Parse PDF file and extract racing data"""
        races = []
        
        try:
            # Convert PDF to text
            text = self._pdf_to_text(pdf_path)
            if not text:
                logger.error("Could not extract text from PDF")
                return races
            
            # Try to parse as structured racing data
            races = self._parse_racing_text(text)
            
            if not races:
                # If no structured data found, try basic extraction
                races = self._parse_basic_text(text)
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}", exc_info=True)
        
        return races
    
    def _pdf_to_text(self, pdf_path: str) -> str:
        """Convert PDF to text using available tools"""
        text = ""
        
        # Try different methods to extract text
        methods = [
            self._try_pdftotext,
            self._try_python_pdfplumber,
            self._try_python_pypdf2,
        ]
        
        for method in methods:
            try:
                text = method(pdf_path)
                if text and len(text.strip()) > 100:  # Ensure we got meaningful text
                    break
            except Exception as e:
                logger.debug(f"Method {method.__name__} failed: {e}")
                continue
        
        return text
    
    def _try_pdftotext(self, pdf_path: str) -> str:
        """Try using pdftotext command line tool"""
        try:
            result = subprocess.run(
                ['pdftotext', '-layout', pdf_path, '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return ""
    
    def _try_python_pdfplumber(self, pdf_path: str) -> str:
        """Try using pdfplumber library"""
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except ImportError:
            logger.debug("pdfplumber not installed")
        except Exception as e:
            logger.debug(f"pdfplumber error: {e}")
        return ""
    
    def _try_python_pypdf2(self, pdf_path: str) -> str:
        """Try using PyPDF2 library"""
        try:
            import PyPDF2
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except ImportError:
            logger.debug("PyPDF2 not installed")
        except Exception as e:
            logger.debug(f"PyPDF2 error: {e}")
        return ""
    
    def _parse_racing_text(self, text: str) -> List[Dict]:
        """Parse structured racing data from text"""
        races = []
        
        # Split text into potential race sections
        race_sections = re.split(r'RACE\s+\d+', text, flags=re.IGNORECASE)
        
        for i, section in enumerate(race_sections[1:], 1):  # Skip first empty section
            race = self._parse_race_section(section, i)
            if race and race.get('entries'):
                races.append(race)
        
        return races
    
    def _parse_race_section(self, section: str, race_num: int) -> Dict:
        """Parse a single race section"""
        race = {
            'race_number': race_num,
            'entries': []
        }
        
        # Extract basic race info
        lines = section.split('\n')
        for line in lines[:20]:  # Check first 20 lines for race info
            # Track
            track_match = self.patterns['track'].search(line)
            if track_match and 'track' not in race:
                race['track'] = track_match.group(1).strip()
            
            # Distance
            dist_match = self.patterns['distance'].search(line)
            if dist_match and 'distance' not in race:
                race['distance'] = dist_match.group(1)
                race['dist_unit'] = dist_match.group(2)[0].upper()
            
            # Purse
            purse_match = self.patterns['purse'].search(line)
            if purse_match and 'purse' not in race:
                race['purse'] = purse_match.group(1).replace(',', '')
        
        # Extract horse entries
        # Look for patterns like: "1  Horse Name  5-2"
        entry_pattern = re.compile(r'^\s*(\d+)\s+([A-Za-z][A-Za-z\s\'-]{2,30})\s+(\d+-\d+|\d+(?:\.\d+)?)', re.MULTILINE)
        
        for match in entry_pattern.finditer(section):
            entry = {
                'program_number': match.group(1),
                'horse_name': match.group(2).strip(),
                'morning_line_odds': match.group(3)
            }
            race['entries'].append(entry)
        
        return race if race['entries'] else None
    
    def _parse_basic_text(self, text: str) -> List[Dict]:
        """Fallback parser for basic text extraction"""
        races = []
        
        # Try to find any date in the document
        date_match = self.patterns['date'].search(text)
        race_date = date_match.group(0) if date_match else None
        
        # Create a single race with basic info
        race = {
            'race_number': 1,
            'race_date': race_date,
            'track': 'Unknown Track',
            'entries': []
        }
        
        # Look for anything that might be a horse name with a number
        lines = text.split('\n')
        for line in lines:
            # Simple pattern: number followed by name
            match = re.match(r'^\s*(\d+)\s+([A-Za-z][A-Za-z\s]{2,30})', line)
            if match:
                entry = {
                    'program_number': match.group(1),
                    'horse_name': match.group(2).strip()
                }
                race['entries'].append(entry)
        
        if race['entries']:
            races.append(race)
        
        return races