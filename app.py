from flask import Flask, render_template, request, jsonify, send_file
import requests
import csv
import io
import os
from typing import List, Dict, Optional
import time

app = Flask(__name__)

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
    
    def export_to_csv(self) -> str:
        """Export collection to CSV format compatible with MTGGoldfish/Deckbox"""
        output = io.StringIO()
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
    
    def import_from_csv(self, csv_content: str) -> Dict:
        """Import collection from CSV format"""
        imported_count = 0
        errors = []
        
        try:
            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                try:
                    name = row.get('Name', '').strip()
                    set_code = row.get('Set', '').strip().lower()
                    collector_number = row.get('Collector Number', '').strip()
                    quantity = int(row.get('Quantity', 0))
                    foil = row.get('Foil', '').strip().lower() in ['yes', 'true', '1']
                    condition = row.get('Condition', 'Near Mint').strip()
                    language = row.get('Language', 'English').strip()
                    
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
                            'set': set_code.upper(),
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
                    else:
                        errors.append(f"Row {row_num}: Could not find card '{name}' in set '{set_code}'")
                        
                except (ValueError, KeyError) as e:
                    errors.append(f"Row {row_num}: Invalid data format - {str(e)}")
                    
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return {
            'imported_count': imported_count,
            'errors': errors,
            'success': imported_count > 0
        }
    
    def _find_card_by_details(self, name: str, set_code: str, collector_number: str) -> Optional[Dict]:
        """Find a card using Scryfall API by name, set, and collector number"""
        try:
            # First try exact search with collector number
            if collector_number:
                response = requests.get(
                    f"{ScryfallAPI.BASE_URL}/cards/{set_code}/{collector_number}"
                )
                if response.status_code == 200:
                    card_data = response.json()
                    # Verify the name matches (case-insensitive)
                    if card_data['name'].lower() == name.lower():
                        return card_data
            
            # Fallback: search by name and set
            response = requests.get(
                f"{ScryfallAPI.BASE_URL}/cards/named",
                params={
                    'exact': name,
                    'set': set_code
                }
            )
            if response.status_code == 200:
                return response.json()
                
            # Last resort: fuzzy search
            response = requests.get(
                f"{ScryfallAPI.BASE_URL}/cards/named",
                params={
                    'fuzzy': name,
                    'set': set_code
                }
            )
            if response.status_code == 200:
                return response.json()
                
        except requests.RequestException:
            pass
        
        return None
    
    def clear_collection(self):
        """Clear the entire collection"""
        self.collection = {}

# Global collection manager
collection_manager = CollectionManager()

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
    """Export collection as CSV"""
    csv_data = collection_manager.export_to_csv()
    
    # Create a file-like object
    output = io.BytesIO()
    output.write(csv_data.encode('utf-8'))
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='mtg_collection.csv'
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

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
