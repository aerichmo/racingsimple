"""
Automatic HTML parser that can fix itself by trying multiple strategies
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class AutoFixParser:
    """Parser that tries multiple strategies until it finds data"""
    
    def __init__(self):
        self.strategies = [
            self.strategy_table_based,
            self.strategy_div_based,
            self.strategy_text_pattern,
            self.strategy_list_based,
            self.strategy_mixed_content
        ]
        self.successful_strategy = None
        
    def parse(self, html: str) -> Tuple[bool, List[Dict], Dict]:
        """Try all strategies until one works"""
        soup = BeautifulSoup(html, 'html.parser')
        
        for i, strategy in enumerate(self.strategies):
            logger.info(f"Trying strategy {i+1}: {strategy.__name__}")
            try:
                success, races, debug_info = strategy(soup)
                if success and races:
                    logger.info(f"✅ Strategy {strategy.__name__} succeeded!")
                    self.successful_strategy = strategy.__name__
                    return True, races, {
                        'strategy': strategy.__name__,
                        'races_found': len(races),
                        **debug_info
                    }
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        return False, [], {'error': 'All strategies failed'}
    
    def strategy_table_based(self, soup) -> Tuple[bool, List[Dict], Dict]:
        """Look for data in HTML tables"""
        races = []
        debug_info = {'tables_found': 0, 'races_extracted': 0}
        
        # Find all tables
        tables = soup.find_all('table')
        debug_info['tables_found'] = len(tables)
        
        for table in tables:
            # Check if table has racing data
            text = table.get_text().lower()
            if any(word in text for word in ['horse', 'jockey', 'trainer', 'post']):
                # Extract headers
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
                
                # Extract race data
                race = {
                    'horses': [],
                    'table_headers': headers
                }
                
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        horse = {}
                        for i, cell in enumerate(cells):
                            value = cell.get_text().strip()
                            if i < len(headers):
                                horse[headers[i]] = value
                            else:
                                horse[f'col_{i}'] = value
                        
                        if horse:
                            race['horses'].append(horse)
                
                if race['horses']:
                    races.append(race)
                    debug_info['races_extracted'] += 1
        
        return len(races) > 0, races, debug_info
    
    def strategy_div_based(self, soup) -> Tuple[bool, List[Dict], Dict]:
        """Look for data in div structures"""
        races = []
        debug_info = {'divs_analyzed': 0, 'race_patterns_found': 0}
        
        # Find divs that might contain race data
        race_divs = []
        for div in soup.find_all('div'):
            text = div.get_text()
            if re.search(r'race\s+\d+', text, re.I) and len(text) > 100:
                race_divs.append(div)
        
        debug_info['divs_analyzed'] = len(race_divs)
        
        for div in race_divs:
            race = self._extract_race_from_container(div)
            if race and race.get('horses'):
                races.append(race)
                debug_info['race_patterns_found'] += 1
        
        return len(races) > 0, races, debug_info
    
    def strategy_text_pattern(self, soup) -> Tuple[bool, List[Dict], Dict]:
        """Extract data using text patterns"""
        races = []
        debug_info = {'patterns_found': {}}
        
        text = soup.get_text()
        
        # Common patterns in racing data
        patterns = {
            'race_header': r'Race\s+(\d+)[:\s-]+([^\n]+)',
            'horse_line': r'(\d+)\s+([A-Z][A-Za-z\s]+)\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)',
            'odds': r'(\d+-\d+|\d+/\d+|\d+\.\d+)',
            'post_time': r'Post:\s*(\d+:\d+\s*[APM]+)',
        }
        
        # Find all race headers
        race_matches = re.finditer(patterns['race_header'], text, re.I)
        
        for match in race_matches:
            race_num = match.group(1)
            race_info = match.group(2)
            
            race = {
                'race_number': int(race_num),
                'info': race_info,
                'horses': []
            }
            
            # Find horses after this race header
            start_pos = match.end()
            next_race = re.search(r'Race\s+\d+', text[start_pos:], re.I)
            end_pos = start_pos + next_race.start() if next_race else len(text)
            
            race_text = text[start_pos:end_pos]
            
            # Extract horses
            horse_matches = re.finditer(patterns['horse_line'], race_text)
            for horse_match in horse_matches:
                horse = {
                    'program_number': horse_match.group(1),
                    'horse_name': horse_match.group(2).strip(),
                    'jockey': horse_match.group(3),
                    'trainer': horse_match.group(4)
                }
                race['horses'].append(horse)
            
            if race['horses']:
                races.append(race)
        
        debug_info['patterns_found'] = {
            'races': len(races),
            'total_horses': sum(len(r['horses']) for r in races)
        }
        
        return len(races) > 0, races, debug_info
    
    def strategy_list_based(self, soup) -> Tuple[bool, List[Dict], Dict]:
        """Look for data in list structures (ul/ol)"""
        races = []
        debug_info = {'lists_found': 0}
        
        # Find lists that might contain race data
        for list_tag in ['ul', 'ol']:
            lists = soup.find_all(list_tag)
            debug_info['lists_found'] += len(lists)
            
            for lst in lists:
                items = lst.find_all('li')
                if len(items) > 3:  # Likely to be horses
                    race = {'horses': []}
                    
                    for item in items:
                        text = item.get_text().strip()
                        # Try to parse horse info from list item
                        parts = re.split(r'[,\|/]', text)
                        if len(parts) >= 2:
                            horse = {
                                'name': parts[0].strip(),
                                'info': ' / '.join(parts[1:])
                            }
                            race['horses'].append(horse)
                    
                    if race['horses']:
                        races.append(race)
        
        return len(races) > 0, races, debug_info
    
    def strategy_mixed_content(self, soup) -> Tuple[bool, List[Dict], Dict]:
        """Final strategy: extract any structured data"""
        races = []
        debug_info = {'elements_processed': 0}
        
        # Look for any repeating structures
        all_elements = soup.find_all(['div', 'section', 'article', 'table', 'ul'])
        debug_info['elements_processed'] = len(all_elements)
        
        for elem in all_elements:
            # Count certain keywords
            text = elem.get_text()
            horse_indicators = text.count('Jockey') + text.count('Trainer') + text.count('Odds')
            
            if horse_indicators >= 3:  # Likely contains horse data
                race = self._extract_race_from_container(elem)
                if race and race.get('horses'):
                    races.append(race)
        
        # Deduplicate races
        unique_races = []
        seen = set()
        for race in races:
            race_key = str(race.get('race_number', '')) + str(len(race['horses']))
            if race_key not in seen:
                seen.add(race_key)
                unique_races.append(race)
        
        return len(unique_races) > 0, unique_races, debug_info
    
    def _extract_race_from_container(self, container) -> Dict:
        """Generic extraction from any container"""
        race = {'horses': []}
        
        text = container.get_text()
        
        # Extract race number
        race_match = re.search(r'Race\s+(\d+)', text, re.I)
        if race_match:
            race['race_number'] = int(race_match.group(1))
        
        # Look for structured data
        # Try to find repeating patterns (likely horses)
        lines = text.split('\n')
        potential_horses = []
        
        for line in lines:
            line = line.strip()
            # Skip empty or very short lines
            if len(line) < 5:
                continue
            
            # Check if line might be a horse entry
            words = line.split()
            if 2 <= len(words) <= 20:  # Reasonable range for horse data
                # Check for common patterns
                if re.search(r'\d+', line):  # Has numbers (program, odds, etc)
                    potential_horses.append(line)
        
        # Group consecutive lines that might be horse data
        if len(potential_horses) >= 3:  # At least 3 horses
            for line in potential_horses:
                parts = re.split(r'\s{2,}|\t', line)  # Split by multiple spaces or tabs
                if parts:
                    horse = {
                        'raw_data': line,
                        'parsed_fields': parts
                    }
                    race['horses'].append(horse)
        
        return race