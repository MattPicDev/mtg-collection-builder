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
from queue import Queue

app = Flask(__name__)

# Progress tracking system
import_progress = {}

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
        """Fetch all MTG sets from Scryfall API"""
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
            for s in data['data']:
                # Filter by set type and ensure it has cards
                if (s['set_type'] in relevant_set_types and 
                    s.get('card_count', 0) > 0 and
                    s['set_type'] not in ['token', 'memorabilia', 'art_series']):
                    sets.append(s)
            
            # Sort by release date (newest first)
            sets.sort(key=lambda x: x['released_at'], reverse=True)
            
            return sets
        except requests.RequestException as e:
            print(f"Error fetching sets: {e}")
            return []
    
    @staticmethod
    def get_set_cards(set_code: str) -> List[Dict]:
        """Fetch all cards from a specific set"""
        try:
            cards = []
            page = 1
            
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
            'image_url': card_data.get('image_uris', {}).get('small', '')
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
                        'My Price': ''
                    })
        else:
            # MTGGoldfish format (default)
            fieldnames = ['Name', 'Set', 'Collector Number', 'Quantity', 'Foil', 'Condition', 'Language']
            
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
                        'Language': card['language']
                    })
        
        return output.getvalue()
    
    def get_collection_summary(self) -> Dict:
        """Get summary statistics of the collection"""
        total_cards = sum(card['quantity'] for card in self.collection.values())
        total_unique = len([card for card in self.collection.values() if card['quantity'] > 0])
        
        return {
            'total_cards': total_cards,
            'unique_cards': total_unique,
            'sets_represented': len(set(card['set'] for card in self.collection.values() if card['quantity'] > 0))
        }
    
    def import_from_csv(self, csv_content: str, progress_callback=None) -> Dict:
        """Import collection from CSV format - supports both MTGGoldfish and DeckBox formats"""
        imported_count = 0
        errors = []
        
        try:
            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # Convert to list to get total count
            rows = list(reader)
            total_rows = len(rows)
            
            for row_num, row in enumerate(rows, start=2):  # Start at 2 because of header
                try:
                    # Update progress if callback provided
                    if progress_callback:
                        progress_callback({
                            'current': row_num - 1,
                            'total': total_rows,
                            'card_name': row.get('Name', '').strip(),
                            'status': 'processing'
                        })
                    
                    # Handle different column name formats
                    name = row.get('Name', '').strip()
                    
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
                    
                    if not name or not set_code or quantity <= 0:
                        continue  # Skip invalid rows
                    
                    # Try to find the card via Scryfall API
                    card_data = self._find_card_by_details(name, set_code, collector_number)
                    
                    if card_data:
                        # Create collection entry
                        card_id = card_data['id']
                        key = f"{card_id}_{foil}"
                        
                        self.collection[key] = {
                            'name': name,
                            'set': card_data.get('set', set_code).upper(),
                            'set_name': card_data.get('set_name', ''),
                            'collector_number': collector_number,
                            'quantity': quantity,
                            'foil': foil,
                            'condition': condition,
                            'language': language,
                            'rarity': card_data.get('rarity', 'unknown'),
                            'image_url': card_data.get('image_uris', {}).get('small', '')
                        }
                        imported_count += 1
                        
                        # Update progress with success
                        if progress_callback:
                            progress_callback({
                                'current': row_num - 1,
                                'total': total_rows,
                                'card_name': name,
                                'status': 'imported'
                            })
                    else:
                        errors.append(f"Row {row_num}: Could not find card '{name}' in set '{set_code}'")
                        
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
            
            # Final progress update
            if progress_callback:
                progress_callback({
                    'current': total_rows,
                    'total': total_rows,
                    'card_name': '',
                    'status': 'complete'
                })
                    
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return {
            'imported_count': imported_count,
            'errors': errors,
            'success': imported_count > 0
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

# Global dictionary to store import progress
import_progress = {}

# Global progress tracking
progress_queues = {}
progress_lock = threading.Lock()

def get_progress_queue(session_id):
    """Get or create a progress queue for a session"""
    with progress_lock:
        if session_id not in progress_queues:
            progress_queues[session_id] = Queue()
        return progress_queues[session_id]

def cleanup_progress_queue(session_id):
    """Remove a progress queue when done"""
    with progress_lock:
        if session_id in progress_queues:
            del progress_queues[session_id]

class ImportProgressTracker:
    """Tracks progress for CSV imports"""
    
    def __init__(self, import_id: str):
        self.import_id = import_id
        self.total_rows = 0
        self.current_row = 0
        self.imported_count = 0
        self.errors = []
        self.current_card = ""
        self.status = "starting"
        self.completed = False
        
    def update_progress(self, current_row: int, current_card: str, imported_count: int, errors: List[str]):
        """Update progress information"""
        self.current_row = current_row
        self.current_card = current_card
        self.imported_count = imported_count
        self.errors = errors
        self.status = "processing"
        
    def set_total_rows(self, total_rows: int):
        """Set the total number of rows to process"""
        self.total_rows = total_rows
        
    def complete(self, success: bool):
        """Mark import as completed"""
        self.completed = True
        self.status = "completed" if success else "failed"
        
    def get_progress_data(self) -> Dict:
        """Get current progress data"""
        percentage = 0
        if self.total_rows > 0:
            percentage = min(100, (self.current_row / self.total_rows) * 100)
            
        return {
            'import_id': self.import_id,
            'total_rows': self.total_rows,
            'current_row': self.current_row,
            'imported_count': self.imported_count,
            'errors': self.errors,
            'current_card': self.current_card,
            'status': self.status,
            'percentage': percentage,
            'completed': self.completed
        }

@app.route('/')
def index():
    """Main page - show set selection"""
    sets = ScryfallAPI.get_sets()
    return render_template('index.html', sets=sets)  # Show all filtered sets

@app.route('/set/<set_code>')
def set_view(set_code: str):
    """View cards in a specific set for collection entry"""
    cards = ScryfallAPI.get_set_cards(set_code)
    set_info = next((s for s in ScryfallAPI.get_sets() if s['code'] == set_code), None)
    
    if not set_info:
        return "Set not found", 404
    
    return render_template('set_view.html', cards=cards, set_info=set_info)

@app.route('/set/<set_code>/rapid')
def set_rapid_view(set_code: str):
    """Rapid input mode for a specific set"""
    cards = ScryfallAPI.get_set_cards(set_code)
    set_info = next((s for s in ScryfallAPI.get_sets() if s['code'] == set_code), None)
    
    if not set_info:
        return "Set not found", 404
    
    return render_template('rapid_view.html', cards=cards, set_info=set_info)

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
        
        # Read and decode the file content
        csv_content = file.read().decode('utf-8')
        
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
                    'total': result.get('imported_count', 0)
                })
            except Exception as e:
                update_import_progress(import_id, {
                    'status': 'error',
                    'error': str(e),
                    'current': 0,
                    'total': 0
                })
        
        thread = threading.Thread(target=run_import)
        thread.start()
        
        return jsonify({'import_id': import_id})
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/import_progress/<import_id>')
def import_progress_stream(import_id):
    """Server-sent events endpoint for import progress"""
    def generate():
        while True:
            progress_data = get_import_progress(import_id)
            
            if progress_data:
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # If import is complete, clean up and stop
                if progress_data.get('status') in ['complete', 'error']:
                    cleanup_import_progress(import_id)
                    break
            
            time.sleep(0.1)  # Poll every 100ms
    
    return Response(generate(), mimetype='text/plain')

# ...existing routes...

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
