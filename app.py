from flask import Flask, render_template, request, jsonify, send_file, Response
import requests
import csv
import io
import os
from typing import List, Dict, Optional, Generator
import time
import json
import uuid
import threading
import sqlite3
from datetime import datetime, timedelta
import hashlib
import re

app = Flask(__name__)

# Progress tracking system
import_progress = {}

# Cache configuration
CACHE_DB_PATH = 'mtg_cache.db'
CACHE_EXPIRY_DAYS = 7  # Cache bulk data for 7 days

def sanitize_card_name(card_name: str) -> str:
    """
    Sanitize card name by removing parenthetical information commonly added by collection exporters.
    
    Examples:
    - "Mountain (59)" -> "Mountain"
    - "Zendikar (FDN) (87)" -> "Zendikar"
    - "Lightning Bolt" -> "Lightning Bolt" (unchanged)
    
    Args:
        card_name: The card name to sanitize
        
    Returns:
        The sanitized card name with parenthetical information removed
    """
    if not card_name:
        return card_name
    
    # Remove all parenthetical information (including nested parentheses)
    # This regex removes any text within parentheses along with the parentheses themselves
    sanitized = re.sub(r'\s*\([^)]*\)\s*', '', card_name)
    
    # Clean up any extra whitespace
    sanitized = sanitized.strip()
    
    return sanitized

class BulkDataCache:
    """Manages local caching of Scryfall bulk data for faster imports"""
    
    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database for caching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for caching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bulk_metadata (
                id INTEGER PRIMARY KEY,
                data_type TEXT UNIQUE,
                download_url TEXT,
                updated_at TEXT,
                size INTEGER,
                etag TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards_cache (
                id TEXT PRIMARY KEY,
                name TEXT,
                set_code TEXT,
                collector_number TEXT,
                set_name TEXT,
                rarity TEXT,
                image_url TEXT,
                price_usd TEXT,
                price_usd_foil TEXT,
                data_json TEXT,
                updated_at TEXT
            )
        ''')
        
        # Check if price columns exist and add them if not (for backwards compatibility)
        cursor.execute("PRAGMA table_info(cards_cache)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'price_usd' not in columns:
            cursor.execute('ALTER TABLE cards_cache ADD COLUMN price_usd TEXT')
        
        if 'price_usd_foil' not in columns:
            cursor.execute('ALTER TABLE cards_cache ADD COLUMN price_usd_foil TEXT')
        
        # Create indexes for fast lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_name ON cards_cache(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_set ON cards_cache(set_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_collector ON cards_cache(collector_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_lookup ON cards_cache(name, set_code, collector_number)')
        
        conn.commit()
        conn.close()
    
    def is_cache_valid(self, data_type: str = 'default_cards') -> bool:
        """Check if cached data is still valid"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT updated_at FROM bulk_metadata WHERE data_type = ?',
            (data_type,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        updated_at = datetime.fromisoformat(result[0])
        return datetime.now() - updated_at < timedelta(days=CACHE_EXPIRY_DAYS)
    
    def get_bulk_data_info(self) -> Optional[Dict]:
        """Get bulk data download information from Scryfall"""
        try:
            response = requests.get(f"{ScryfallAPI.BASE_URL}/bulk-data")
            response.raise_for_status()
            data = response.json()
            
            # Find the default cards bulk data
            for bulk_data in data['data']:
                if bulk_data['type'] == 'default_cards':
                    return bulk_data
            
            return None
        except requests.RequestException as e:
            print(f"Error fetching bulk data info: {e}")
            return None
    
    def download_and_cache_bulk_data(self, progress_callback=None) -> bool:
        """Download and cache bulk card data"""
        bulk_info = self.get_bulk_data_info()
        if not bulk_info:
            return False
        
        try:
            # Check if we need to download (based on etag/size)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT etag, size FROM bulk_metadata WHERE data_type = ?',
                ('default_cards',)
            )
            cached_info = cursor.fetchone()
            
            # If we have the same etag and size, skip download
            if cached_info and cached_info[0] == bulk_info.get('content_encoding') and cached_info[1] == bulk_info.get('size'):
                conn.close()
                return True
            
            if progress_callback:
                progress_callback({
                    'status': 'downloading',
                    'message': 'Downloading bulk card data...',
                    'current': 0,
                    'total': 100
                })
            
            # Download bulk data
            response = requests.get(bulk_info['download_uri'], stream=True)
            response.raise_for_status()
            
            # Parse JSON incrementally
            cards_data = response.json()
            total_cards = len(cards_data)
            
            # Clear existing cache
            cursor.execute('DELETE FROM cards_cache')
            
            # Insert cards into cache
            for i, card in enumerate(cards_data):
                if progress_callback and i % 1000 == 0:
                    progress_callback({
                        'status': 'caching',
                        'message': f'Caching card {i+1} of {total_cards}...',
                        'current': i,
                        'total': total_cards
                    })
                
                cursor.execute('''
                    INSERT OR REPLACE INTO cards_cache 
                    (id, name, set_code, collector_number, set_name, rarity, image_url, price_usd, price_usd_foil, data_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card['id'],
                    card['name'],
                    card['set'],
                    card['collector_number'],
                    card.get('set_name', ''),
                    card.get('rarity', ''),
                    card.get('image_uris', {}).get('small', ''),
                    card.get('prices', {}).get('usd'),
                    card.get('prices', {}).get('usd_foil'),
                    json.dumps(card),
                    datetime.now().isoformat()
                ))
            
            # Update bulk metadata
            cursor.execute('''
                INSERT OR REPLACE INTO bulk_metadata 
                (data_type, download_url, updated_at, size, etag)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                'default_cards',
                bulk_info['download_uri'],
                datetime.now().isoformat(),
                bulk_info.get('size', 0),
                bulk_info.get('content_encoding', '')
            ))
            
            conn.commit()
            conn.close()
            
            if progress_callback:
                progress_callback({
                    'status': 'complete',
                    'message': f'Cached {total_cards} cards successfully',
                    'current': total_cards,
                    'total': total_cards
                })
            
            return True
            
        except Exception as e:
            print(f"Error downloading bulk data: {e}")
            if progress_callback:
                progress_callback({
                    'status': 'error',
                    'message': f'Error downloading bulk data: {str(e)}',
                    'current': 0,
                    'total': 0
                })
            return False
    
    def find_card_in_cache(self, name: str, set_code: str, collector_number: str = None) -> Optional[Dict]:
        """Find a card in the local cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Normalize set code using the same logic as the CollectionManager
        set_code = self._normalize_set_identifier(set_code)
        
        # First try exact match with collector number
        if collector_number:
            cursor.execute('''
                SELECT data_json FROM cards_cache 
                WHERE name = ? AND set_code = ? AND collector_number = ?
            ''', (name, set_code, collector_number))
            result = cursor.fetchone()
            if result:
                conn.close()
                return json.loads(result[0])
        
        # Try without collector number
        cursor.execute('''
            SELECT data_json FROM cards_cache 
            WHERE name = ? AND set_code = ?
            ORDER BY collector_number
        ''', (name, set_code))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return json.loads(result[0])
        
        return None
    
    def search_cards_in_cache(self, name: str, set_identifier: str = None) -> List[Dict]:
        """Search for cards in cache with fuzzy matching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if set_identifier:
            # Normalize set identifier
            set_code = self._normalize_set_identifier(set_identifier)
            cursor.execute('''
                SELECT data_json FROM cards_cache 
                WHERE (LOWER(name) LIKE LOWER(?) OR LOWER(name) = LOWER(?)) 
                AND (LOWER(set_code) = LOWER(?) OR LOWER(set_name) LIKE LOWER(?))
                ORDER BY 
                    CASE WHEN LOWER(name) = LOWER(?) THEN 0 ELSE 1 END,
                    CASE WHEN LOWER(set_code) = LOWER(?) THEN 0 ELSE 1 END
                LIMIT 10
            ''', (f'%{name}%', name, set_code, f'%{set_identifier}%', name, set_code))
        else:
            cursor.execute('''
                SELECT data_json FROM cards_cache 
                WHERE LOWER(name) LIKE LOWER(?) OR LOWER(name) = LOWER(?)
                ORDER BY CASE WHEN LOWER(name) = LOWER(?) THEN 0 ELSE 1 END
                LIMIT 10
            ''', (f'%{name}%', name, name))
        
        results = cursor.fetchall()
        conn.close()
        
        return [json.loads(result[0]) for result in results]
    
    def _normalize_set_identifier(self, set_identifier: str) -> str:
        """Convert full set names to 3-letter codes where possible"""
        # Common set name mappings for DeckBox format
        set_mappings = {
            'classic sixth edition': '6ed',
            'sixth edition': '6ed',
            'fifth edition': '5ed',
            'fourth edition': '4ed',
            'revised edition': '3ed',
            'unlimited edition': '2ed',
            'limited edition alpha': 'lea',
            'limited edition beta': 'leb',
            'zendikar': 'zen',
            'magic 2015 core set': 'm15',
            'magic 2014 core set': 'm14',
            'magic 2013': 'm13',
            'magic 2012': 'm12',
            'magic 2011': 'm11',
            'magic 2010': 'm10',
            'tenth edition': '10e',
            'ninth edition': '9ed',
            'eighth edition': '8ed',
            'seventh edition': '7ed',
            'tempest': 'tmp',
            'stronghold': 'sth',
            'exodus': 'exo',
            'weatherlight': 'wth',
            'visions': 'vis',
            'mirage': 'mir',
            'alliances': 'all',
            'ice age': 'ice',
            'homelands': 'hml',
            'fallen empires': 'fem',
            'the dark': 'drk',
            'legends': 'leg',
            'antiquities': 'atq',
            'arabian nights': 'arn'
        }
        
        # If it's already a 3-letter code, return as is
        if len(set_identifier) == 3:
            return set_identifier.lower()
        
        # Try to find a mapping for the full name
        normalized = set_identifier.lower().strip()
        return set_mappings.get(normalized, set_identifier.lower())
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about cached data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM cards_cache')
        total_cards = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT set_code) FROM cards_cache')
        total_sets = cursor.fetchone()[0]
        
        cursor.execute('SELECT updated_at FROM bulk_metadata WHERE data_type = ?', ('default_cards',))
        last_update = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_cards': total_cards,
            'total_sets': total_sets,
            'last_update': last_update[0] if last_update else None,
            'cache_valid': self.is_cache_valid()
        }
    
    def get_set_cards_from_cache(self, set_code: str) -> List[Dict]:
        """Get all cards from a specific set from cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data_json FROM cards_cache 
            WHERE LOWER(set_code) = LOWER(?)
            ORDER BY CAST(collector_number AS INTEGER), collector_number
        ''', (set_code,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [json.loads(result[0]) for result in results]
    
    def get_sets_from_cache(self) -> List[Dict]:
        """Get all available sets from cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get distinct sets from cache with their basic information
        cursor.execute('''
            SELECT DISTINCT set_code, set_name, MIN(data_json) as sample_card
            FROM cards_cache 
            WHERE set_code IS NOT NULL AND set_code != ''
            GROUP BY set_code, set_name
            ORDER BY set_code
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        sets = []
        today = datetime.now().date()
        
        for row in results:
            set_code, set_name, sample_card_json = row
            try:
                sample_card = json.loads(sample_card_json)
                
                # Create set info from the sample card
                set_info = {
                    'code': set_code,
                    'name': set_name or sample_card.get('set_name', set_code.upper()),
                    'set_type': sample_card.get('set_type', 'unknown'),
                    'released_at': sample_card.get('released_at', '1993-01-01'),
                    'card_count': 0,  # Will be calculated
                    'icon_svg_uri': sample_card.get('set_uri', ''),
                    'search_uri': f"https://api.scryfall.com/cards/search?q=set:{set_code}",
                    'uri': f"https://api.scryfall.com/sets/{set_code}",
                    '_source': 'cache'
                }
                
                # Filter out future sets
                try:
                    release_date = datetime.strptime(set_info['released_at'], '%Y-%m-%d').date()
                    if release_date > today:
                        continue  # Skip future sets
                except ValueError:
                    # If date parsing fails, assume it's not a future set
                    pass
                
                # Get card count for this set
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM cards_cache WHERE set_code = ?', (set_code,))
                card_count = cursor.fetchone()[0]
                set_info['card_count'] = card_count
                conn.close()
                
                sets.append(set_info)
            except Exception as e:
                print(f"Error processing set {set_code}: {e}")
                continue
        
        # Sort by release date (newest first), then alphabetically by name
        sets.sort(key=lambda x: (-time.mktime(time.strptime(x['released_at'], '%Y-%m-%d')), x['name']))
        
        return sets
    
    def cache_cards_batch(self, cards: List[Dict]) -> int:
        """Cache a batch of cards from API responses"""
        if not cards:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cached_count = 0
        for card in cards:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO cards_cache 
                    (id, name, set_code, collector_number, set_name, rarity, image_url, price_usd, price_usd_foil, data_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card['id'],
                    card['name'],
                    card['set'],
                    card['collector_number'],
                    card.get('set_name', ''),
                    card.get('rarity', ''),
                    card.get('image_uris', {}).get('small', ''),
                    card.get('prices', {}).get('usd'),
                    card.get('prices', {}).get('usd_foil'),
                    json.dumps(card),
                    datetime.now().isoformat()
                ))
                cached_count += 1
            except Exception as e:
                print(f"Error caching card {card.get('name', 'unknown')}: {e}")
        
        conn.commit()
        conn.close()
        
        return cached_count
    
    def get_set_completion_stats(self, set_code: str) -> Dict:
        """Get cache completion statistics for a specific set"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM cards_cache 
            WHERE LOWER(set_code) = LOWER(?)
        ''', (set_code,))
        
        cached_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            'set_code': set_code,
            'cached_cards': cached_count,
            'cache_available': cached_count > 0
        }

# Global cache instance
bulk_cache = BulkDataCache()

def generate_import_id():
    """Generate a unique ID for import operations"""
    return str(uuid.uuid4())

def update_import_progress(import_id: str, progress_data: Dict):
    """Update progress for an import operation"""
    import_progress[import_id] = progress_data
    
def get_import_progress(import_id: str) -> Dict:
    """Get progress for an import operation"""
    return import_progress.get(import_id, {})

def cleanup_import_progress(import_id: str):
    """Clean up progress data for completed import"""
    import_progress.pop(import_id, None)

class ScryfallAPI:
    """Handler for Scryfall API interactions"""
    
    BASE_URL = "https://api.scryfall.com"
    
    @staticmethod
    def get_sets() -> List[Dict]:
        """Fetch all MTG sets using hybrid cache approach"""
        # First try to get sets from cache
        if bulk_cache.is_cache_valid():
            cached_sets = bulk_cache.get_sets_from_cache()
            if cached_sets:
                print(f"Retrieved {len(cached_sets)} sets from cache")
                return cached_sets
        
        # Fallback to API if cache miss or invalid
        try:
            response = requests.get(f"{ScryfallAPI.BASE_URL}/sets")
            response.raise_for_status()
            data = response.json()
            
            # Filter for Magic: The Gathering expansions and relevant sets
            # Include main expansions, core sets, masters sets, commander sets, etc.
            # Exclude tokens, art series, memorabilia, and other non-playable sets
            relevant_set_types = [
                'core', 'expansion', 'masters', 'commander', 'planechase', 
                'archenemy', 'from_the_vault', 'spellbook', 'premium_deck',
                'duel_deck', 'draft_innovation', 'treasure_chest', 'arsenal',
                'box', 'funny', 'starter', 'supplemental'
            ]
            
            sets = []
            today = datetime.now().date()
            
            for s in data['data']:
                # Filter by set type and ensure it has cards
                if (s['set_type'] in relevant_set_types and 
                    s.get('card_count', 0) > 0 and
                    s['set_type'] not in ['token', 'memorabilia', 'art_series']):
                    
                    # Filter out future sets
                    try:
                        release_date = datetime.strptime(s['released_at'], '%Y-%m-%d').date()
                        if release_date <= today:
                            s['_source'] = 'api'
                            sets.append(s)
                    except ValueError:
                        # If date parsing fails, skip this set
                        continue
            
            # Sort by release date (newest first), then alphabetically by name
            sets.sort(key=lambda x: (-time.mktime(time.strptime(x['released_at'], '%Y-%m-%d')), x['name']))
            
            print(f"Retrieved {len(sets)} sets from API")
            return sets
        except requests.RequestException as e:
            print(f"Error fetching sets: {e}")
            # If API fails, try cache anyway (even if expired)
            cached_sets = bulk_cache.get_sets_from_cache()
            if cached_sets:
                print(f"Fallback: Retrieved {len(cached_sets)} sets from cache")
                return cached_sets
            return []
    
    @staticmethod
    def get_set_cards(set_code: str) -> List[Dict]:
        """Fetch all cards from a specific set using hybrid cache approach"""
        # First try to get cards from cache
        cached_cards = bulk_cache.get_set_cards_from_cache(set_code)
        
        if cached_cards:
            # Mark as cache source and return
            for card in cached_cards:
                card['_source'] = 'cache'
            print(f"Retrieved {len(cached_cards)} cards for set {set_code} from cache")
            return cached_cards
        
        # If not in cache, fetch from API
        try:
            cards = []
            page = 1
            
            print(f"Fetching cards for set {set_code} from Scryfall API...")
            
            while True:
                response = requests.get(
                    f"{ScryfallAPI.BASE_URL}/cards/search",
                    params={
                        'q': f'set:{set_code}',
                        'page': page,
                        'order': 'set'
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                cards.extend(data['data'])
                
                if not data.get('has_more', False):
                    break
                
                page += 1
                time.sleep(0.1)  # Rate limiting
            
            # Cache the fetched cards for future use
            if cards:
                cached_count = bulk_cache.cache_cards_batch(cards)
                print(f"Cached {cached_count} cards for set {set_code}")
                
                # Mark as API source
                for card in cards:
                    card['_source'] = 'api'
            
            return cards
        except requests.RequestException as e:
            print(f"Error fetching cards for set {set_code}: {e}")
            return []

class CollectionManager:
    """Manages collection data and CSV export"""
    
    def __init__(self):
        self.collection = {}
    
    def add_card(self, card_data: Dict, quantity: int, foil: bool = False):
        """Add a card to the collection"""
        card_id = card_data['id']
        key = f"{card_id}_{foil}"
        
        self.collection[key] = {
            'name': card_data['name'],
            'set': card_data['set'].upper(),
            'set_name': card_data['set_name'],
            'collector_number': card_data['collector_number'],
            'quantity': quantity,
            'foil': foil,
            'condition': 'Near Mint',
            'language': 'English',
            'rarity': card_data['rarity'],
            'image_url': card_data.get('image_uris', {}).get('small', ''),
            'price_usd': card_data.get('prices', {}).get('usd_foil' if foil else 'usd'),
            'price_usd_regular': card_data.get('prices', {}).get('usd'),
            'price_usd_foil': card_data.get('prices', {}).get('usd_foil')
        }
    
    def export_to_csv(self, format_type: str = 'mtggoldfish') -> str:
        """Export collection to CSV format compatible with MTGGoldfish or DeckBox"""
        output = io.StringIO()
        
        if format_type.lower() == 'deckbox':
            # DeckBox format
            fieldnames = ['Count', 'Tradelist Count', 'Name', 'Edition', 'Card Number', 'Condition', 'Foil', 'Signed', 'Artist Proof', 'Altered Art', 'Misprint', 'Promo', 'Textless', 'My Price']
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for card in self.collection.values():
                if card['quantity'] > 0:
                    writer.writerow({
                        'Count': card['quantity'],
                        'Tradelist Count': '',
                        'Name': card['name'],
                        'Edition': card.get('set_name', card['set']),
                        'Card Number': card['collector_number'],
                        'Condition': card['condition'],
                        'Foil': 'foil' if card['foil'] else '',
                        'Signed': '',
                        'Artist Proof': '',
                        'Altered Art': '',
                        'Misprint': '',
                        'Promo': '',
                        'Textless': '',
                        'My Price': card.get('price_usd', '')
                    })
        else:
            # MTGGoldfish format (default)
            fieldnames = ['Name', 'Set', 'Collector Number', 'Quantity', 'Foil', 'Condition', 'Language', 'Price USD']
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for card in self.collection.values():
                if card['quantity'] > 0:
                    writer.writerow({
                        'Name': card['name'],
                        'Set': card['set'],
                        'Collector Number': card['collector_number'],
                        'Quantity': card['quantity'],
                        'Foil': 'Yes' if card['foil'] else 'No',
                        'Condition': card['condition'],
                        'Language': card['language'],
                        'Price USD': card.get('price_usd', '')
                    })
        
        return output.getvalue()
    
    def get_collection_summary(self) -> Dict:
        """Get summary statistics of the collection"""
        total_cards = sum(card['quantity'] for card in self.collection.values())
        total_unique = len([card for card in self.collection.values() if card['quantity'] > 0])
        
        # Calculate total estimated value
        total_value = 0.0
        priced_cards = 0
        
        for card in self.collection.values():
            if card['quantity'] > 0:
                price_str = card.get('price_usd')
                if price_str:
                    try:
                        price = float(price_str)
                        total_value += price * card['quantity']
                        priced_cards += 1
                    except (ValueError, TypeError):
                        pass
        
        return {
            'total_cards': total_cards,
            'unique_cards': total_unique,
            'sets_represented': len(set(card['set'] for card in self.collection.values() if card['quantity'] > 0)),
            'total_value': total_value,
            'priced_cards': priced_cards
        }
    
    def import_from_csv(self, csv_content: str, progress_callback=None) -> Dict:
        """Import collection from CSV format - supports both MTGGoldfish and DeckBox formats with bulk cache optimization"""
        imported_count = 0
        errors = []
        cache_hits = 0
        api_calls = 0
        
        try:
            # Check if bulk cache is available and valid
            if not bulk_cache.is_cache_valid():
                if progress_callback:
                    progress_callback({
                        'current': 0,
                        'total': 0,
                        'card_name': '',
                        'status': 'cache_update',
                        'message': 'Updating card database for faster imports...'
                    })
                
                # Download bulk data in background
                bulk_cache.download_and_cache_bulk_data(progress_callback)
            
            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # Convert to list to get total count
            rows = list(reader)
            total_rows = len(rows)
            
            for row_num, row in enumerate(rows, start=2):  # Start at 2 because of header
                try:
                    # Handle different column name formats
                    name = row.get('Name', '').strip()
                    
                    # Sanitize card name by removing parenthetical information
                    # (e.g., "Mountain (59)" -> "Mountain", "Zendikar (FDN) (87)" -> "Zendikar")
                    sanitized_name = sanitize_card_name(name)
                    
                    # Update progress if callback provided
                    if progress_callback:
                        progress_callback({
                            'current': row_num - 1,
                            'total': total_rows,
                            'card_name': sanitized_name,
                            'status': 'processing'
                        })
                    
                    # Handle different quantity column names
                    quantity = int(row.get('Quantity', row.get('Count', 0)))
                    
                    # Handle different set column names
                    set_code = row.get('Set', row.get('Edition', '')).strip()
                    
                    # Handle different collector number column names
                    collector_number = row.get('Collector Number', row.get('Card Number', '')).strip()
                    
                    # Handle different foil formats
                    foil_value = row.get('Foil', '').strip().lower()
                    foil = foil_value in ['yes', 'true', '1', 'foil']
                    
                    # Handle condition and language with defaults
                    condition = row.get('Condition', 'Near Mint').strip()
                    if not condition:
                        condition = 'Near Mint'
                    
                    language = row.get('Language', 'English').strip()
                    if not language:
                        language = 'English'
                    
                    if not sanitized_name or not set_code or quantity <= 0:
                        continue  # Skip invalid rows
                    
                    # Try to find the card using hybrid approach (cache first, then API)
                    card_data = self._find_card_by_details_hybrid(sanitized_name, set_code, collector_number)
                    
                    if card_data:
                        if card_data.get('_source') == 'cache':
                            cache_hits += 1
                        else:
                            api_calls += 1
                    
                    if card_data:
                        # Create collection entry
                        card_id = card_data['id']
                        key = f"{card_id}_{foil}"
                        
                        self.collection[key] = {
                            'name': sanitized_name,
                            'set': card_data.get('set', set_code).upper(),
                            'set_name': card_data.get('set_name', ''),
                            'collector_number': collector_number,
                            'quantity': quantity,
                            'foil': foil,
                            'condition': condition,
                            'language': language,
                            'rarity': card_data.get('rarity', 'unknown'),
                            'image_url': card_data.get('image_uris', {}).get('small', ''),
                            'price_usd': card_data.get('prices', {}).get('usd_foil' if foil else 'usd'),
                            'price_usd_regular': card_data.get('prices', {}).get('usd'),
                            'price_usd_foil': card_data.get('prices', {}).get('usd_foil')
                        }
                        imported_count += 1
                        
                        # Update progress with success
                        if progress_callback:
                            progress_callback({
                                'current': row_num - 1,
                                'total': total_rows,
                                'card_name': sanitized_name,
                                'status': 'imported'
                            })
                    else:
                        errors.append(f"Row {row_num}: Could not find card '{sanitized_name}' in set '{set_code}'")
                        
                        # Update progress with error
                        if progress_callback:
                            progress_callback({
                                'current': row_num - 1,
                                'total': total_rows,
                                'card_name': name,
                                'status': 'error'
                            })
                        
                except (ValueError, KeyError) as e:
                    errors.append(f"Row {row_num}: Invalid data format - {str(e)}")
                    
                    # Update progress with error
                    if progress_callback:
                        progress_callback({
                            'current': row_num - 1,
                            'total': total_rows,
                            'card_name': row.get('Name', ''),
                            'status': 'error'
                        })
            
            # Final progress update with performance stats
            if progress_callback:
                progress_callback({
                    'current': total_rows,
                    'total': total_rows,
                    'card_name': '',
                    'status': 'complete',
                    'message': f'Import complete! {imported_count} cards imported. Cache hits: {cache_hits}, API calls: {api_calls}'
                })
                    
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return {
            'imported_count': imported_count,
            'errors': errors,
            'success': imported_count > 0,
            'cache_hits': cache_hits,
            'api_calls': api_calls,
            'cache_hit_rate': (cache_hits / max(1, cache_hits + api_calls)) * 100
        }
    
    def _find_card_by_details(self, name: str, set_identifier: str, collector_number: str) -> Optional[Dict]:
        """Find a card using Scryfall API by name, set, and collector number"""
        try:
            # Convert set identifier to 3-letter code if needed
            set_code = self._normalize_set_identifier(set_identifier)
            
            # First try exact search with collector number
            if collector_number and set_code:
                response = requests.get(
                    f"{ScryfallAPI.BASE_URL}/cards/{set_code}/{collector_number}"
                )
                if response.status_code == 200:
                    card_data = response.json()
                    # Verify the name matches (case-insensitive)
                    if card_data['name'].lower() == name.lower():
                        return card_data
            
            # Fallback: search by name and set code
            if set_code:
                response = requests.get(
                    f"{ScryfallAPI.BASE_URL}/cards/named",
                    params={
                        'exact': name,
                        'set': set_code
                    }
                )
                if response.status_code == 200:
                    return response.json()
                    
                # Last resort: fuzzy search with set code
                response = requests.get(
                    f"{ScryfallAPI.BASE_URL}/cards/named",
                    params={
                        'fuzzy': name,
                        'set': set_code
                    }
                )
                if response.status_code == 200:
                    return response.json()
            
            # If set code lookup failed, try searching by full set name
            response = requests.get(
                f"{ScryfallAPI.BASE_URL}/cards/search",
                params={
                    'q': f'"{name}" set:"{set_identifier}"'
                }
            )
            if response.status_code == 200:
                search_data = response.json()
                if search_data.get('data'):
                    return search_data['data'][0]  # Return first match
                
        except requests.RequestException:
            pass
        
        return None
    
    def _find_card_by_details_hybrid(self, name: str, set_identifier: str, collector_number: str) -> Optional[Dict]:
        """Find a card using hybrid approach: cache first, then API fallback"""
        # First try the bulk cache
        card_data = bulk_cache.find_card_in_cache(name, set_identifier, collector_number)
        if card_data:
            card_data['_source'] = 'cache'
            return card_data
        
        # If not in cache, try fuzzy search in cache
        cached_results = bulk_cache.search_cards_in_cache(name, set_identifier)
        if cached_results:
            # Return the best match from cache
            card_data = cached_results[0]
            card_data['_source'] = 'cache'
            return card_data
        
        # Fallback to API if cache miss
        card_data = self._find_card_by_details(name, set_identifier, collector_number)
        if card_data:
            card_data['_source'] = 'api'
            return card_data
        
        return None
    
    def _normalize_set_identifier(self, set_identifier: str) -> str:
        """Convert full set names to 3-letter codes where possible"""
        # Common set name mappings for DeckBox format
        set_mappings = {
            'classic sixth edition': '6ed',
            'sixth edition': '6ed',
            'fifth edition': '5ed',
            'fourth edition': '4ed',
            'revised edition': '3ed',
            'unlimited edition': '2ed',
            'limited edition alpha': 'lea',
            'limited edition beta': 'leb',
            'zendikar': 'zen',
            'magic 2015 core set': 'm15',
            'magic 2014 core set': 'm14',
            'magic 2013': 'm13',
            'magic 2012': 'm12',
            'magic 2011': 'm11',
            'magic 2010': 'm10',
            'tenth edition': '10e',
            'ninth edition': '9ed',
            'eighth edition': '8ed',
            'seventh edition': '7ed',
            'tempest': 'tmp',
            'stronghold': 'sth',
            'exodus': 'exo',
            'weatherlight': 'wth',
            'visions': 'vis',
            'mirage': 'mir',
            'alliances': 'all',
            'ice age': 'ice',
            'homelands': 'hml',
            'fallen empires': 'fem',
            'the dark': 'drk',
            'legends': 'leg',
            'antiquities': 'atq',
            'arabian nights': 'arn'
        }
        
        # If it's already a 3-letter code, return as is
        if len(set_identifier) == 3:
            return set_identifier.lower()
        
        # Try to find a mapping for the full name
        normalized = set_identifier.lower().strip()
        return set_mappings.get(normalized, set_identifier.lower())
    
    def clear_collection(self):
        """Clear the entire collection"""
        self.collection = {}

# Global collection manager
collection_manager = CollectionManager()

@app.route('/')
def index():
    """Main page - show set selection"""
    sets = ScryfallAPI.get_sets()
    cache_stats = bulk_cache.get_cache_stats()
    return render_template('index.html', sets=sets, cache_stats=cache_stats)  # Show all filtered sets

@app.route('/set/<set_code>')
def set_view(set_code: str):
    """View cards in a specific set for collection entry"""
    cards = ScryfallAPI.get_set_cards(set_code)
    set_info = next((s for s in ScryfallAPI.get_sets() if s['code'] == set_code), None)
    
    if not set_info:
        return "Set not found", 404
    
    # Get cache statistics for this set
    cache_stats = bulk_cache.get_set_completion_stats(set_code)
    
    # Count cache hits vs API calls
    cache_hits = sum(1 for card in cards if card.get('_source') == 'cache')
    api_calls = sum(1 for card in cards if card.get('_source') == 'api')
    
    performance_stats = {
        'cache_hits': cache_hits,
        'api_calls': api_calls,
        'total_cards': len(cards),
        'cache_hit_rate': (cache_hits / len(cards) * 100) if cards else 0
    }
    
    return render_template('set_view.html', 
                         cards=cards, 
                         set_info=set_info,
                         cache_stats=cache_stats,
                         performance_stats=performance_stats)

@app.route('/set/<set_code>/rapid')
def set_rapid_view(set_code: str):
    """Rapid input mode for a specific set"""
    cards = ScryfallAPI.get_set_cards(set_code)
    set_info = next((s for s in ScryfallAPI.get_sets() if s['code'] == set_code), None)
    
    if not set_info:
        return "Set not found", 404
    
    # Get cache statistics for this set
    cache_stats = bulk_cache.get_set_completion_stats(set_code)
    
    # Count cache hits vs API calls
    cache_hits = sum(1 for card in cards if card.get('_source') == 'cache')
    api_calls = sum(1 for card in cards if card.get('_source') == 'api')
    
    performance_stats = {
        'cache_hits': cache_hits,
        'api_calls': api_calls,
        'total_cards': len(cards),
        'cache_hit_rate': (cache_hits / len(cards) * 100) if cards else 0
    }
    
    return render_template('rapid_view.html', 
                         cards=cards, 
                         set_info=set_info,
                         cache_stats=cache_stats,
                         performance_stats=performance_stats)

@app.route('/api/add_card', methods=['POST'])
def add_card():
    """API endpoint to add a card to collection"""
    data = request.json
    card_data = data.get('card')
    quantity = int(data.get('quantity', 0))
    foil = data.get('foil', False)
    
    if quantity > 0:
        collection_manager.add_card(card_data, quantity, foil)
    
    return jsonify({'status': 'success'})

@app.route('/collection')
def collection_view():
    """View current collection"""
    summary = collection_manager.get_collection_summary()
    return render_template('collection.html', 
                         collection=collection_manager.collection,
                         summary=summary)

@app.route('/export')
def export_collection():
    """Export collection as CSV with format selection"""
    format_type = request.args.get('format', 'mtggoldfish').lower()
    
    if format_type not in ['mtggoldfish', 'deckbox']:
        format_type = 'mtggoldfish'
    
    csv_data = collection_manager.export_to_csv(format_type)
    
    # Create a file-like object
    output = io.BytesIO()
    output.write(csv_data.encode('utf-8'))
    output.seek(0)
    
    # Set appropriate filename based on format
    filename = f'mtg_collection_{format_type}.csv'
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/import', methods=['GET', 'POST'])
def import_collection():
    """Import collection from CSV file"""
    if request.method == 'GET':
        return render_template('import.html')
    
    # Handle file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400
    
    try:
        # Read and decode the file content
        csv_content = file.read().decode('utf-8')
        
        # Import the collection
        result = collection_manager.import_from_csv(csv_content)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/api/clear_collection', methods=['POST'])
def clear_collection():
    """API endpoint to clear the entire collection"""
    collection_manager.clear_collection()
    return jsonify({'status': 'success', 'message': 'Collection cleared'})

@app.route('/import_with_progress', methods=['POST'])
def import_collection_with_progress():
    """Import collection with progress tracking"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400
    
    try:
        # Generate unique import ID
        import_id = generate_import_id()
        
        # Initialize progress tracking
        update_import_progress(import_id, {
            'status': 'starting',
            'current': 0,
            'total': 0,
            'card_name': '',
            'message': 'Reading file...'
        })
        
        # Read and decode the file content
        csv_content = file.read().decode('utf-8')
        
        # Update progress
        update_import_progress(import_id, {
            'status': 'processing',
            'current': 0,
            'total': 0,
            'card_name': '',
            'message': 'Starting import...'
        })
        
        # Create progress callback
        def progress_callback(progress_data):
            update_import_progress(import_id, progress_data)
        
        # Start import in background thread
        def run_import():
            try:
                result = collection_manager.import_from_csv(csv_content, progress_callback)
                # Store final result
                update_import_progress(import_id, {
                    'status': 'complete',
                    'result': result,
                    'current': result.get('imported_count', 0),
                    'total': result.get('imported_count', 0),
                    'card_name': '',
                    'message': f'Import complete! {result.get("imported_count", 0)} cards imported.'
                })
            except Exception as e:
                update_import_progress(import_id, {
                    'status': 'error',
                    'error': str(e),
                    'current': 0,
                    'total': 0,
                    'card_name': '',
                    'message': f'Import failed: {str(e)}'
                })
        
        thread = threading.Thread(target=run_import)
        thread.daemon = True  # Make thread daemon so it dies when main thread dies
        thread.start()
        
        return jsonify({'import_id': import_id})
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/import_progress/<import_id>')
def import_progress_stream(import_id):
    """Server-sent events endpoint for import progress"""
    def generate():
        # Initialize progress tracking if not exists
        if import_id not in import_progress:
            update_import_progress(import_id, {
                'status': 'starting',
                'current': 0,
                'total': 0,
                'card_name': '',
                'message': 'Initializing import...'
            })
        
        while True:
            progress_data = get_import_progress(import_id)
            
            if progress_data:
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # If import is complete, clean up and stop
                if progress_data.get('status') in ['complete', 'error']:
                    cleanup_import_progress(import_id)
                    break
            else:
                # If no progress data, send a heartbeat
                yield f"data: {json.dumps({'status': 'waiting', 'message': 'Waiting for import to start...'})}\n\n"
            
            time.sleep(0.1)  # Poll every 100ms
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/api/cache/status')
def cache_status():
    """API endpoint to get cache status and statistics"""
    stats = bulk_cache.get_cache_stats()
    return jsonify({
        'cache_valid': stats['cache_valid'],
        'total_cards': stats['total_cards'],
        'total_sets': stats['total_sets'],
        'last_update': stats['last_update'],
        'cache_size_mb': os.path.getsize(CACHE_DB_PATH) / (1024 * 1024) if os.path.exists(CACHE_DB_PATH) else 0
    })

@app.route('/api/cache/set/<set_code>')
def set_cache_status(set_code: str):
    """API endpoint to get cache status for a specific set"""
    stats = bulk_cache.get_set_completion_stats(set_code)
    return jsonify(stats)

@app.route('/api/cache/refresh', methods=['POST'])
def refresh_cache():
    """API endpoint to refresh bulk cache"""
    try:
        # Generate unique refresh ID for progress tracking
        refresh_id = generate_import_id()
        
        # Initialize progress tracking
        update_import_progress(refresh_id, {
            'status': 'starting',
            'current': 0,
            'total': 0,
            'message': 'Starting cache refresh...'
        })
        
        # Create progress callback
        def progress_callback(progress_data):
            update_import_progress(refresh_id, progress_data)
        
        # Start refresh in background thread
        def run_refresh():
            try:
                success = bulk_cache.download_and_cache_bulk_data(progress_callback)
                if success:
                    update_import_progress(refresh_id, {
                        'status': 'complete',
                        'message': 'Cache refresh completed successfully',
                        'current': 100,
                        'total': 100
                    })
                else:
                    update_import_progress(refresh_id, {
                        'status': 'error',
                        'message': 'Cache refresh failed',
                        'current': 0,
                        'total': 0
                    })
            except Exception as e:
                update_import_progress(refresh_id, {
                    'status': 'error',
                    'message': f'Cache refresh failed: {str(e)}',
                    'current': 0,
                    'total': 0
                })
        
        thread = threading.Thread(target=run_refresh)
        thread.daemon = True
        thread.start()
        
        return jsonify({'refresh_id': refresh_id})
        
    except Exception as e:
        return jsonify({'error': f'Error starting cache refresh: {str(e)}'}), 500

@app.route('/api/cache/refresh_progress/<refresh_id>')
def cache_refresh_progress(refresh_id):
    """Server-sent events endpoint for cache refresh progress"""
    def generate():
        while True:
            progress_data = get_import_progress(refresh_id)
            
            if progress_data:
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # If refresh is complete, clean up and stop
                if progress_data.get('status') in ['complete', 'error']:
                    cleanup_import_progress(refresh_id)
                    break
            else:
                # If no progress data, send a heartbeat
                yield f"data: {json.dumps({'status': 'waiting', 'message': 'Waiting for refresh to start...'})}\n\n"
            
            time.sleep(0.1)  # Poll every 100ms
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
