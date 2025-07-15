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
            
            # Filter for relevant sets and sort by release date (newest first)
            sets = [s for s in data['data'] if s['set_type'] not in ['token', 'memorabilia']]
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

# Global collection manager
collection_manager = CollectionManager()

@app.route('/')
def index():
    """Main page - show set selection"""
    sets = ScryfallAPI.get_sets()
    return render_template('index.html', sets=sets[:50])  # Show first 50 sets

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

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
