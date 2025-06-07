import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2
import logging
import json
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class SelfDebuggingScraper:
    """A scraper that can analyze HTML and update its own selectors"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.base_url = "https://www.equibase.com/static/entry/"
        self.selector_history = []
        self.successful_selectors = {}
        
    def analyze_html_structure(self, html: str) -> Dict[str, List[str]]:
        """Analyze HTML to find potential selectors for race data"""
        soup = BeautifulSoup(html, 'html.parser')
        analysis = {
            'race_containers': [],
            'horse_tables': [],
            'race_numbers': [],
            'horse_names': [],
            'odds_elements': [],
            'jockey_elements': [],
            'trainer_elements': []
        }
        
        # Look for race containers (divs/sections with multiple horses)
        for tag in ['div', 'section', 'table', 'article']:
            containers = soup.find_all(tag)
            for container in containers:
                # Check if container has multiple horse-like entries
                text = container.get_text()
                if text.count('Jockey') >= 2 or text.count('Trainer') >= 2:
                    classes = container.get('class', [])
                    if classes:
                        analysis['race_containers'].append({
                            'tag': tag,
                            'class': ' '.join(classes),
                            'id': container.get('id', ''),
                            'sample': text[:200]
                        })
        
        # Look for tables that might contain horses
        tables = soup.find_all('table')
        for table in tables:
            headers = [th.get_text().strip() for th in table.find_all('th')]
            if any(word in ' '.join(headers).lower() for word in ['horse', 'jockey', 'trainer', 'odds']):
                analysis['horse_tables'].append({
                    'class': ' '.join(table.get('class', [])),
                    'headers': headers,
                    'row_count': len(table.find_all('tr'))
                })
        
        # Look for race numbers
        for pattern in [r'Race\s+(\d+)', r'RACE\s+(\d+)', r'Race:\s*(\d+)']:
            matches = soup.find_all(text=re.compile(pattern))
            for match in matches[:5]:  # Limit to first 5
                parent = match.parent
                analysis['race_numbers'].append({
                    'pattern': pattern,
                    'tag': parent.name,
                    'class': ' '.join(parent.get('class', [])),
                    'text': match.strip()
                })
        
        # Look for odds patterns
        odds_patterns = [r'\d+-\d+', r'\d+/\d+', r'\d+\.\d+']
        for pattern in odds_patterns:
            elements = soup.find_all(text=re.compile(pattern))
            for elem in elements[:10]:
                parent = elem.parent
                if parent:
                    analysis['odds_elements'].append({
                        'pattern': pattern,
                        'tag': parent.name,
                        'class': ' '.join(parent.get('class', [])),
                        'value': elem.strip()
                    })
        
        return analysis
    
    def generate_selectors(self, analysis: Dict) -> Dict[str, str]:
        """Generate CSS selectors based on HTML analysis"""
        selectors = {}
        
        # Generate race container selector
        if analysis['race_containers']:
            # Prefer containers with classes
            for container in analysis['race_containers']:
                if container['class']:
                    selectors['race_container'] = f"{container['tag']}.{container['class'].replace(' ', '.')}"
                    break
            else:
                # Fallback to tag with id
                for container in analysis['race_containers']:
                    if container['id']:
                        selectors['race_container'] = f"{container['tag']}#{container['id']}"
                        break
        
        # Generate table selector
        if analysis['horse_tables']:
            table = analysis['horse_tables'][0]
            if table['class']:
                selectors['horse_table'] = f"table.{table['class'].replace(' ', '.')}"
            else:
                selectors['horse_table'] = 'table'
        
        # Generate race number selector
        if analysis['race_numbers']:
            rn = analysis['race_numbers'][0]
            if rn['class']:
                selectors['race_number'] = f"{rn['tag']}.{rn['class'].replace(' ', '.')}"
            else:
                selectors['race_number'] = rn['tag']
        
        return selectors
    
    def test_selectors(self, html: str, selectors: Dict[str, str]) -> Tuple[bool, Dict]:
        """Test if selectors extract meaningful data"""
        soup = BeautifulSoup(html, 'html.parser')
        results = {
            'races_found': 0,
            'horses_found': 0,
            'sample_data': []
        }
        
        try:
            # Test race container selector
            if 'race_container' in selectors:
                containers = soup.select(selectors['race_container'])
                results['races_found'] = len(containers)
                
                for container in containers[:2]:  # Test first 2
                    race_data = {'horses': []}
                    
                    # Try to find horses in container
                    if 'horse_table' in selectors:
                        tables = container.select(selectors['horse_table'])
                        for table in tables:
                            rows = table.find_all('tr')[1:]  # Skip header
                            for row in rows[:3]:  # First 3 horses
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 3:
                                    horse_data = {
                                        'col1': cells[0].get_text().strip(),
                                        'col2': cells[1].get_text().strip() if len(cells) > 1 else '',
                                        'col3': cells[2].get_text().strip() if len(cells) > 2 else ''
                                    }
                                    race_data['horses'].append(horse_data)
                                    results['horses_found'] += 1
                    
                    results['sample_data'].append(race_data)
            
            # Success if we found races and horses
            success = results['races_found'] > 0 and results['horses_found'] > 0
            return success, results
            
        except Exception as e:
            logger.error(f"Selector test error: {e}")
            return False, results
    
    def fetch_and_learn(self, date: datetime) -> Optional[List[Dict]]:
        """Fetch data and learn from the HTML structure"""
        url = self.generate_url(date)
        logger.info(f"Fetching and learning from: {url}")
        
        try:
            # Add browser headers to avoid bot detection
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html = response.text
            
            # Check for Incapsula block
            if 'Incapsula' in html or 'incident ID' in html:
                logger.error("Blocked by Incapsula bot protection")
                raise Exception("Equibase is blocking automated access. Manual data entry required.")
            
            # Save HTML for debugging
            debug_file = f"/tmp/equibase_{date.strftime('%Y%m%d')}.html"
            with open(debug_file, 'w') as f:
                f.write(html)
            logger.info(f"Saved HTML to {debug_file}")
            
            # First try the auto-fixer
            logger.info("Trying AutoFixParser...")
            from auto_fixer import AutoFixParser
            fixer = AutoFixParser()
            success, races, debug_info = fixer.parse(html)
            
            if success:
                logger.info(f"✅ AutoFixParser succeeded with strategy: {debug_info.get('strategy')}")
                # Convert to our format
                formatted_races = []
                for race in races:
                    formatted_race = {
                        'date': date.date(),
                        'race_number': race.get('race_number', len(formatted_races) + 1),
                        'track_name': 'Fonner Park',  # Default for now
                        'horses': []
                    }
                    
                    for horse in race.get('horses', []):
                        # Extract horse data from whatever format we got
                        horse_data = {
                            'horse_name': 'Unknown',
                            'program_number': '0',
                            'jockey': 'Unknown',
                            'trainer': 'Unknown',
                            'morning_line_odds': 'N/A',
                            'weight': 'N/A'
                        }
                        
                        # Try to extract from different formats
                        if isinstance(horse, dict):
                            horse_data['horse_name'] = horse.get('name', horse.get('horse_name', horse.get('Name', 'Unknown')))
                            horse_data['program_number'] = str(horse.get('program_number', horse.get('Program', '0')))
                            horse_data['jockey'] = horse.get('jockey', horse.get('Jockey', 'Unknown'))
                            horse_data['trainer'] = horse.get('trainer', horse.get('Trainer', 'Unknown'))
                            
                            # Handle parsed fields
                            if 'parsed_fields' in horse and horse['parsed_fields']:
                                fields = horse['parsed_fields']
                                if len(fields) > 0:
                                    horse_data['program_number'] = fields[0] if fields[0].isdigit() else '0'
                                if len(fields) > 1:
                                    horse_data['horse_name'] = fields[1]
                        
                        formatted_race['horses'].append(horse_data)
                    
                    if formatted_race['horses']:
                        formatted_races.append(formatted_race)
                
                return formatted_races
            
            # If auto-fixer failed, try original approach
            logger.info("AutoFixParser failed, trying original analysis...")
            analysis = self.analyze_html_structure(html)
            
            # Log analysis results
            logger.info(f"Found {len(analysis['race_containers'])} potential race containers")
            logger.info(f"Found {len(analysis['horse_tables'])} potential horse tables")
            logger.info(f"Found {len(analysis['race_numbers'])} race number patterns")
            
            # Generate selectors
            selectors = self.generate_selectors(analysis)
            logger.info(f"Generated selectors: {json.dumps(selectors, indent=2)}")
            
            # Test selectors
            success, results = self.test_selectors(html, selectors)
            logger.info(f"Selector test results: {json.dumps(results, indent=2)}")
            
            if success:
                logger.info("✅ Selectors validated successfully!")
                self.successful_selectors = selectors
                
                # Now parse with validated selectors
                return self.parse_with_selectors(html, selectors)
            else:
                logger.warning("❌ Selectors failed validation")
                
                # Try alternative parsing strategies
                return self.fallback_parsing(html, analysis)
                
        except Exception as e:
            logger.error(f"Fetch and learn error: {e}")
            return None
    
    def parse_with_selectors(self, html: str, selectors: Dict[str, str]) -> List[Dict]:
        """Parse HTML using validated selectors"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        try:
            containers = soup.select(selectors.get('race_container', 'div'))
            
            for container in containers:
                race_data = self.extract_race_info(container)
                if race_data:
                    races.append(race_data)
            
            logger.info(f"Successfully parsed {len(races)} races")
            return races
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return []
    
    def fallback_parsing(self, html: str, analysis: Dict) -> List[Dict]:
        """Try multiple parsing strategies when selectors fail"""
        logger.info("Attempting fallback parsing strategies...")
        
        # Strategy 1: Find all text patterns
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        # Look for race patterns
        race_pattern = re.compile(r'Race\s+(\d+)', re.IGNORECASE)
        race_markers = soup.find_all(text=race_pattern)
        
        for marker in race_markers:
            # Find parent container
            parent = marker.parent
            while parent and parent.name not in ['div', 'section', 'article', 'table']:
                parent = parent.parent
            
            if parent:
                # Extract any structured data from parent
                race_data = {
                    'race_number': race_pattern.search(marker).group(1),
                    'horses': []
                }
                
                # Look for horse names (usually proper names)
                potential_horses = parent.find_all(text=re.compile(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$'))
                for horse_text in potential_horses[:10]:  # Limit to 10
                    if len(horse_text.strip()) > 3:  # Skip short words
                        race_data['horses'].append({
                            'horse_name': horse_text.strip()
                        })
                
                if race_data['horses']:
                    races.append(race_data)
        
        logger.info(f"Fallback parsing found {len(races)} races")
        return races
    
    def extract_race_info(self, container) -> Optional[Dict]:
        """Extract race information from a container element"""
        try:
            race_data = {
                'date': datetime.now().date(),
                'horses': []
            }
            
            # Extract race number
            race_text = container.get_text()
            race_match = re.search(r'Race\s+(\d+)', race_text, re.IGNORECASE)
            if race_match:
                race_data['race_number'] = int(race_match.group(1))
            
            # Extract other fields with flexible patterns
            patterns = {
                'track_name': r'Track:\s*([^\n]+)',
                'post_time': r'Post:\s*(\d+:\d+\s*[APM]+)',
                'distance': r'(\d+\s*(?:Mile|Furlong|Yard)s?)',
                'purse': r'\$[\d,]+',
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, race_text, re.IGNORECASE)
                if match:
                    race_data[field] = match.group(1) if field != 'purse' else match.group(0)
            
            return race_data if 'race_number' in race_data else None
            
        except Exception as e:
            logger.error(f"Extract race info error: {e}")
            return None
    
    def generate_url(self, date: datetime) -> str:
        """Generate Equibase URL for given date"""
        date_str = date.strftime("%m%d%y")
        return f"{self.base_url}FMT{date_str}USA-EQB.html"
    
    def save_learning(self):
        """Save successful selectors for future use"""
        if self.successful_selectors:
            config_file = 'scraper_config.json'
            try:
                with open(config_file, 'w') as f:
                    json.dump({
                        'selectors': self.successful_selectors,
                        'last_updated': datetime.now().isoformat(),
                        'history': self.selector_history
                    }, f, indent=2)
                logger.info(f"Saved learned selectors to {config_file}")
            except Exception as e:
                logger.error(f"Error saving config: {e}")


def run_self_debugging_sync(db_url: str):
    """Run the self-debugging scraper"""
    scraper = SelfDebuggingScraper(db_url)
    races = scraper.fetch_and_learn(datetime.now())
    
    if races:
        logger.info(f"Successfully learned and parsed {len(races)} races")
        scraper.save_learning()
        return True, races
    else:
        logger.error("Failed to parse races even with learning")
        return False, []