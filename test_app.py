import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import io
import csv
import requests
from flask import Flask
from app import app, ScryfallAPI, CollectionManager, collection_manager


class TestScryfallAPI(unittest.TestCase):
    """Test cases for ScryfallAPI class"""
    
    @patch('app.requests.get')
    def test_get_sets_success(self, mock_get):
        """Test successful retrieval and filtering of MTG sets"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'data': [
                {
                    'code': 'neo',
                    'name': 'Kamigawa: Neon Dynasty',
                    'set_type': 'expansion',
                    'card_count': 300,
                    'released_at': '2022-02-18'
                },
                {
                    'code': 'tneo',
                    'name': 'Kamigawa: Neon Dynasty Tokens',
                    'set_type': 'token',
                    'card_count': 50,
                    'released_at': '2022-02-18'
                },
                {
                    'code': 'dom',
                    'name': 'Dominaria',
                    'set_type': 'expansion',
                    'card_count': 280,
                    'released_at': '2018-04-27'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        sets = ScryfallAPI.get_sets()
        
        # Should filter out token sets and sort by release date
        self.assertEqual(len(sets), 2)
        self.assertEqual(sets[0]['code'], 'neo')  # Newest first
        self.assertEqual(sets[1]['code'], 'dom')
        
        # Verify token set was filtered out
        set_codes = [s['code'] for s in sets]
        self.assertNotIn('tneo', set_codes)
    
    @patch('app.requests.get')
    def test_get_sets_api_error(self, mock_get):
        """Test handling of API errors when fetching sets"""
        mock_get.side_effect = requests.RequestException("API Error")
        
        sets = ScryfallAPI.get_sets()
        
        self.assertEqual(sets, [])
    
    @patch('app.requests.get')
    @patch('app.time.sleep')  # Mock sleep to speed up tests
    def test_get_set_cards_success(self, mock_sleep, mock_get):
        """Test successful retrieval of cards from a set"""
        # Mock paginated API response
        mock_response_page1 = MagicMock()
        mock_response_page1.raise_for_status.return_value = None
        mock_response_page1.json.return_value = {
            'data': [
                {
                    'id': 'card1',
                    'name': 'Lightning Bolt',
                    'set': 'neo',
                    'collector_number': '1'
                }
            ],
            'has_more': True
        }
        
        mock_response_page2 = MagicMock()
        mock_response_page2.raise_for_status.return_value = None
        mock_response_page2.json.return_value = {
            'data': [
                {
                    'id': 'card2',
                    'name': 'Counterspell',
                    'set': 'neo',
                    'collector_number': '2'
                }
            ],
            'has_more': False
        }
        
        mock_get.side_effect = [mock_response_page1, mock_response_page2]
        
        cards = ScryfallAPI.get_set_cards('neo')
        
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]['name'], 'Lightning Bolt')
        self.assertEqual(cards[1]['name'], 'Counterspell')
        
        # Verify pagination was handled
        self.assertEqual(mock_get.call_count, 2)
    
    @patch('app.requests.get')
    def test_get_set_cards_api_error(self, mock_get):
        """Test handling of API errors when fetching cards"""
        mock_get.side_effect = requests.RequestException("API Error")
        
        cards = ScryfallAPI.get_set_cards('neo')
        
        self.assertEqual(cards, [])


class TestCollectionManager(unittest.TestCase):
    """Test cases for CollectionManager class"""
    
    def setUp(self):
        """Set up test collection manager"""
        self.manager = CollectionManager()
        self.sample_card = {
            'id': 'test-card-id',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common',
            'image_uris': {'small': 'http://example.com/image.jpg'}
        }
    
    def test_add_card_regular(self):
        """Test adding a regular (non-foil) card"""
        self.manager.add_card(self.sample_card, 3, False)
        
        key = f"{self.sample_card['id']}_False"
        self.assertIn(key, self.manager.collection)
        
        card_entry = self.manager.collection[key]
        self.assertEqual(card_entry['name'], 'Lightning Bolt')
        self.assertEqual(card_entry['quantity'], 3)
        self.assertEqual(card_entry['foil'], False)
        self.assertEqual(card_entry['set'], 'NEO')
    
    def test_add_card_foil(self):
        """Test adding a foil card"""
        self.manager.add_card(self.sample_card, 1, True)
        
        key = f"{self.sample_card['id']}_True"
        self.assertIn(key, self.manager.collection)
        
        card_entry = self.manager.collection[key]
        self.assertEqual(card_entry['foil'], True)
        self.assertEqual(card_entry['quantity'], 1)
    
    def test_export_to_csv(self):
        """Test CSV export functionality"""
        # Add some cards to collection
        self.manager.add_card(self.sample_card, 2, False)
        self.manager.add_card(self.sample_card, 1, True)
        
        csv_output = self.manager.export_to_csv()
        
        # Parse the CSV to verify content
        csv_file = io.StringIO(csv_output)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        
        self.assertEqual(len(rows), 2)  # Regular + foil versions
        
        # Check regular card
        regular_card = next(row for row in rows if row['Foil'] == 'No')
        self.assertEqual(regular_card['Name'], 'Lightning Bolt')
        self.assertEqual(regular_card['Quantity'], '2')
        self.assertEqual(regular_card['Set'], 'NEO')
        
        # Check foil card
        foil_card = next(row for row in rows if row['Foil'] == 'Yes')
        self.assertEqual(foil_card['Quantity'], '1')
        self.assertEqual(foil_card['Foil'], 'Yes')
    
    def test_export_to_csv_deckbox_format(self):
        """Test CSV export in DeckBox format"""
        # Add some cards to collection
        self.manager.add_card(self.sample_card, 2, False)
        self.manager.add_card(self.sample_card, 1, True)
        
        # Test DeckBox format export
        csv_output = self.manager.export_to_csv('deckbox')
        
        # Parse the CSV to verify content
        csv_file = io.StringIO(csv_output)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        
        self.assertEqual(len(rows), 2)  # Regular + foil versions
        
        # Check that it has DeckBox format columns
        expected_columns = ['Count', 'Tradelist Count', 'Name', 'Edition', 'Card Number', 'Condition', 'Foil', 'Signed', 'Artist Proof', 'Altered Art', 'Misprint', 'Promo', 'Textless', 'My Price']
        self.assertEqual(list(rows[0].keys()), expected_columns)
        
        # Check regular card
        regular_card = next(row for row in rows if row['Foil'] == '')
        self.assertEqual(regular_card['Name'], 'Lightning Bolt')
        self.assertEqual(regular_card['Count'], '2')
        self.assertEqual(regular_card['Edition'], 'Kamigawa: Neon Dynasty')
        self.assertEqual(regular_card['Card Number'], '123')
        
        # Check foil card
        foil_card = next(row for row in rows if row['Foil'] == 'foil')
        self.assertEqual(foil_card['Count'], '1')
        self.assertEqual(foil_card['Foil'], 'foil')
        self.assertEqual(foil_card['Name'], 'Lightning Bolt')
    
    def test_export_to_csv_mtggoldfish_format(self):
        """Test CSV export in MTGGoldfish format (default)"""
        # Add some cards to collection
        self.manager.add_card(self.sample_card, 2, False)
        self.manager.add_card(self.sample_card, 1, True)
        
        # Test MTGGoldfish format export (default)
        csv_output = self.manager.export_to_csv('mtggoldfish')
        
        # Parse the CSV to verify content
        csv_file = io.StringIO(csv_output)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        
        self.assertEqual(len(rows), 2)  # Regular + foil versions
        
        # Check that it has MTGGoldfish format columns
        expected_columns = ['Name', 'Set', 'Collector Number', 'Quantity', 'Foil', 'Condition', 'Language']
        self.assertEqual(list(rows[0].keys()), expected_columns)
        
        # Check regular card
        regular_card = next(row for row in rows if row['Foil'] == 'No')
        self.assertEqual(regular_card['Name'], 'Lightning Bolt')
        self.assertEqual(regular_card['Quantity'], '2')
        self.assertEqual(regular_card['Set'], 'NEO')
        
        # Check foil card
        foil_card = next(row for row in rows if row['Foil'] == 'Yes')
        self.assertEqual(foil_card['Quantity'], '1')
        self.assertEqual(foil_card['Foil'], 'Yes')
    
    def test_export_to_csv_default_format(self):
        """Test CSV export with default format (should be MTGGoldfish)"""
        # Add some cards to collection
        self.manager.add_card(self.sample_card, 2, False)
        
        # Test default format export
        csv_output = self.manager.export_to_csv()
        
        # Parse the CSV to verify content
        csv_file = io.StringIO(csv_output)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        
        # Check that it has MTGGoldfish format columns (default)
        expected_columns = ['Name', 'Set', 'Collector Number', 'Quantity', 'Foil', 'Condition', 'Language']
        self.assertEqual(list(rows[0].keys()), expected_columns)
        
        # Check the card
        card = rows[0]
        self.assertEqual(card['Name'], 'Lightning Bolt')
        self.assertEqual(card['Quantity'], '2')
        self.assertEqual(card['Set'], 'NEO')
        self.assertEqual(card['Foil'], 'No')
    
    def test_get_collection_summary(self):
        """Test collection summary statistics"""
        # Add multiple cards
        self.manager.add_card(self.sample_card, 3, False)
        self.manager.add_card(self.sample_card, 1, True)
        
        another_card = self.sample_card.copy()
        another_card['id'] = 'different-card'
        another_card['name'] = 'Counterspell'
        self.manager.add_card(another_card, 2, False)
        
        summary = self.manager.get_collection_summary()
        
        self.assertEqual(summary['total_cards'], 6)  # 3 + 1 + 2
        self.assertEqual(summary['unique_cards'], 3)  # 3 different entries
        self.assertEqual(summary['sets_represented'], 1)  # All from NEO
    
    @patch('app.requests.get')
    def test_import_from_csv_success(self, mock_get):
        """Test successful CSV import"""
        # Mock Scryfall API response for card lookup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_card
        mock_get.return_value = mock_response
        
        csv_content = """Name,Set,Collector Number,Quantity,Foil,Condition,Language
Lightning Bolt,neo,123,2,No,Near Mint,English
Lightning Bolt,neo,123,1,Yes,Near Mint,English"""
        
        result = self.manager.import_from_csv(csv_content)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['imported_count'], 2)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(self.manager.collection), 2)
    
    def test_import_from_csv_invalid_data(self):
        """Test CSV import with invalid data"""
        csv_content = """Name,Set,Collector Number,Quantity,Foil,Condition,Language
,neo,123,2,No,Near Mint,English
Lightning Bolt,,123,1,Yes,Near Mint,English
Lightning Bolt,neo,123,invalid,No,Near Mint,English"""
        
        result = self.manager.import_from_csv(csv_content)
        
        # Should skip invalid rows
        self.assertFalse(result['success'])
        self.assertEqual(result['imported_count'], 0)
        self.assertGreater(len(result['errors']), 0)
    
    @patch('app.requests.get')
    def test_find_card_by_details_exact_match(self, mock_get):
        """Test finding card by exact collector number"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_card
        mock_get.return_value = mock_response
        
        result = self.manager._find_card_by_details('Lightning Bolt', 'neo', '123')
        
        self.assertEqual(result['name'], 'Lightning Bolt')
        mock_get.assert_called_once()
    
    @patch('app.requests.get')
    def test_find_card_by_details_not_found(self, mock_get):
        """Test card lookup when card is not found"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.manager._find_card_by_details('Nonexistent Card', 'neo', '999')
        
        self.assertIsNone(result)
    
    def test_clear_collection(self):
        """Test clearing the entire collection"""
        # Add some cards first
        self.manager.add_card(self.sample_card, 5, False)
        self.assertEqual(len(self.manager.collection), 1)
        
        self.manager.clear_collection()
        self.assertEqual(len(self.manager.collection), 0)
    
    @patch('app.requests.get')
    def test_import_from_csv_with_progress_callback(self, mock_get):
        """Test CSV import with progress tracking"""
        # Mock Scryfall API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_card
        mock_get.return_value = mock_response
        
        csv_content = """Name,Set,Collector Number,Quantity,Foil,Condition,Language
Lightning Bolt,neo,123,2,No,Near Mint,English
Counterspell,neo,456,1,Yes,Near Mint,English"""
        
        # Track progress updates
        progress_updates = []
        
        def progress_callback(progress_data):
            progress_updates.append(progress_data)
        
        result = self.manager.import_from_csv(csv_content, progress_callback)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['imported_count'], 2)
        self.assertEqual(len(result['errors']), 0)
        
        # Check progress updates
        self.assertGreater(len(progress_updates), 0)
        
        # Check that we got processing updates
        processing_updates = [u for u in progress_updates if u['status'] == 'processing']
        self.assertEqual(len(processing_updates), 2)  # One for each card
        
        # Check that we got imported updates
        imported_updates = [u for u in progress_updates if u['status'] == 'imported']
        self.assertEqual(len(imported_updates), 2)  # One for each card
        
        # Check that we got a complete update
        complete_updates = [u for u in progress_updates if u['status'] == 'complete']
        self.assertEqual(len(complete_updates), 1)
        
        # Check final update
        final_update = complete_updates[0]
        self.assertEqual(final_update['current'], 2)
        self.assertEqual(final_update['total'], 2)
    
    @patch('app.requests.get')
    def test_import_from_csv_with_progress_callback_errors(self, mock_get):
        """Test CSV import with progress tracking when cards aren't found"""
        # Mock Scryfall API response (card not found)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        csv_content = """Name,Set,Collector Number,Quantity,Foil,Condition,Language
Nonexistent Card,neo,999,1,No,Near Mint,English"""
        
        # Track progress updates
        progress_updates = []
        
        def progress_callback(progress_data):
            progress_updates.append(progress_data)
        
        result = self.manager.import_from_csv(csv_content, progress_callback)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['imported_count'], 0)
        self.assertEqual(len(result['errors']), 1)
        
        # Check progress updates
        self.assertGreater(len(progress_updates), 0)
        
        # Check that we got processing updates
        processing_updates = [u for u in progress_updates if u['status'] == 'processing']
        self.assertEqual(len(processing_updates), 1)
        
        # Check that we got error updates
        error_updates = [u for u in progress_updates if u['status'] == 'error']
        self.assertEqual(len(error_updates), 1)
        
        # Check that we got a complete update
        complete_updates = [u for u in progress_updates if u['status'] == 'complete']
        self.assertEqual(len(complete_updates), 1)
    

class TestFlaskRoutes(unittest.TestCase):
    """Test cases for Flask routes"""
    
    def setUp(self):
        """Set up Flask test client"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Clear collection before each test
        collection_manager.clear_collection()
    
    @patch('app.ScryfallAPI.get_sets')
    def test_index_route(self, mock_get_sets):
        """Test main index route"""
        mock_get_sets.return_value = [
            {
                'code': 'neo', 
                'name': 'Kamigawa: Neon Dynasty', 
                'set_type': 'expansion',
                'released_at': '2022-02-18',
                'card_count': 300
            }
        ]
        
        response = self.app.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Kamigawa: Neon Dynasty', response.data)
    
    @patch('app.ScryfallAPI.get_set_cards')
    @patch('app.ScryfallAPI.get_sets')
    def test_set_view_route(self, mock_get_sets, mock_get_set_cards):
        """Test set view route"""
        mock_get_sets.return_value = [
            {
                'code': 'neo', 
                'name': 'Kamigawa: Neon Dynasty', 
                'set_type': 'expansion',
                'released_at': '2022-02-18',
                'card_count': 300
            }
        ]
        mock_get_set_cards.return_value = [
            {
                'id': 'card1', 
                'name': 'Lightning Bolt', 
                'collector_number': '1',
                'rarity': 'common',
                'mana_cost': '{R}',
                'image_uris': {'small': 'http://example.com/card1.jpg'}
            },
            {
                'id': 'card2', 
                'name': 'Counterspell', 
                'collector_number': '2',
                'rarity': 'common',
                'mana_cost': '{1}{U}',
                'image_uris': {'small': 'http://example.com/card2.jpg'}
            }
        ]
        
        response = self.app.get('/set/neo')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lightning Bolt', response.data)
        self.assertIn(b'Counterspell', response.data)
        # Check for sorting buttons
        self.assertIn(b'sortByNumber', response.data)
        self.assertIn(b'sortByName', response.data)
        self.assertIn(b'Card #', response.data)
        self.assertIn(b'Name', response.data)
        # Check for name filter
        self.assertIn(b'nameFilter', response.data)
        self.assertIn(b'Filter by name...', response.data)
        self.assertIn(b'filterCards()', response.data)
        self.assertIn(b'clearFilter()', response.data)
    
    @patch('app.ScryfallAPI.get_set_cards')
    @patch('app.ScryfallAPI.get_sets')
    def test_set_view_name_filter_functionality(self, mock_get_sets, mock_get_set_cards):
        """Test that name filter elements are present in set view"""
        mock_get_sets.return_value = [
            {
                'code': 'neo', 
                'name': 'Kamigawa: Neon Dynasty', 
                'set_type': 'expansion',
                'released_at': '2022-02-18',
                'card_count': 300
            }
        ]
        mock_get_set_cards.return_value = [
            {
                'id': 'card1', 
                'name': 'Lightning Bolt', 
                'collector_number': '1',
                'rarity': 'common',
                'mana_cost': '{R}',
                'image_uris': {'small': 'http://example.com/card1.jpg'}
            },
            {
                'id': 'card2', 
                'name': 'Counterspell', 
                'collector_number': '2',
                'rarity': 'common',
                'mana_cost': '{1}{U}',
                'image_uris': {'small': 'http://example.com/card2.jpg'}
            }
        ]
        
        response = self.app.get('/set/neo')
        
        self.assertEqual(response.status_code, 200)
        # Check for name filter input elements
        self.assertIn(b'id="nameFilter"', response.data)
        self.assertIn(b'placeholder="Filter by name..."', response.data)
        self.assertIn(b'oninput="filterCards()"', response.data)
        self.assertIn(b'onclick="clearFilter()"', response.data)
        # Check for search icon
        self.assertIn(b'fa-search', response.data)
        # Check for JavaScript functions
        self.assertIn(b'function filterCards()', response.data)
        self.assertIn(b'function clearFilter()', response.data)
        self.assertIn(b'function updateFilteredProgress()', response.data)
    
    @patch('app.ScryfallAPI.get_set_cards')
    @patch('app.ScryfallAPI.get_sets')
    def test_set_rapid_view_route(self, mock_get_sets, mock_get_set_cards):
        """Test rapid view route with sorting functionality"""
        mock_get_sets.return_value = [
            {
                'code': 'neo', 
                'name': 'Kamigawa: Neon Dynasty', 
                'set_type': 'expansion',
                'released_at': '2022-02-18',
                'card_count': 300
            }
        ]
        mock_get_set_cards.return_value = [
            {
                'id': 'card1', 
                'name': 'Lightning Bolt', 
                'collector_number': '1',
                'rarity': 'common',
                'mana_cost': '{R}',
                'set_name': 'Kamigawa: Neon Dynasty',
                'image_uris': {'normal': 'http://example.com/card1.jpg'}
            },
            {
                'id': 'card2', 
                'name': 'Counterspell', 
                'collector_number': '2',
                'rarity': 'common',
                'mana_cost': '{1}{U}',
                'set_name': 'Kamigawa: Neon Dynasty',
                'image_uris': {'normal': 'http://example.com/card2.jpg'}
            }
        ]
        
        response = self.app.get('/set/neo/rapid')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lightning Bolt', response.data)
        self.assertIn(b'Counterspell', response.data)
        self.assertIn(b'Rapid Input Mode', response.data)
        # Check for sorting buttons
        self.assertIn(b'sortByNumber', response.data)
        self.assertIn(b'sortByName', response.data)
        self.assertIn(b'Card #', response.data)
        self.assertIn(b'Name', response.data)
        # Check for rapid input instructions
        self.assertIn(b'Rapid Input Controls', response.data)
        self.assertIn(b'Type a number', response.data)
        self.assertIn(b'Space', response.data)
        self.assertIn(b'Enter', response.data)

    def test_set_view_not_found(self):
        """Test set view with invalid set code"""
        response = self.app.get('/set/invalid')
        
        self.assertEqual(response.status_code, 404)
    
    def test_add_card_api(self):
        """Test add card API endpoint"""
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        
        response = self.app.post('/api/add_card', 
                               json={
                                   'card': card_data,
                                   'quantity': 3,
                                   'foil': False
                               },
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify card was added to collection
        self.assertEqual(len(collection_manager.collection), 1)
    
    def test_collection_view(self):
        """Test collection view route"""
        # Add a card to collection first
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        collection_manager.add_card(card_data, 2, False)
        
        response = self.app.get('/collection')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lightning Bolt', response.data)
    
    def test_export_collection(self):
        """Test CSV export route"""
        # Add a card to collection first
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        collection_manager.add_card(card_data, 2, False)
        
        response = self.app.get('/export')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        self.assertIn(b'Lightning Bolt', response.data)
    
    def test_import_collection_get(self):
        """Test import collection GET route"""
        response = self.app.get('/import')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'import', response.data.lower())
    
    @patch('app.CollectionManager.import_from_csv')
    def test_import_collection_post_success(self, mock_import):
        """Test successful CSV file upload"""
        mock_import.return_value = {
            'success': True,
            'imported_count': 2,
            'errors': []
        }
        
        csv_data = b"Name,Set,Collector Number,Quantity,Foil,Condition,Language\nLightning Bolt,neo,123,2,No,Near Mint,English"
        
        response = self.app.post('/import',
                               data={'file': (io.BytesIO(csv_data), 'test.csv')},
                               content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['imported_count'], 2)
    
    def test_import_collection_no_file(self):
        """Test import with no file uploaded"""
        response = self.app.post('/import')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_import_collection_invalid_file_type(self):
        """Test import with non-CSV file"""
        response = self.app.post('/import',
                               data={'file': (io.BytesIO(b'test'), 'test.txt')},
                               content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('CSV', data['error'])
    
    def test_clear_collection_api(self):
        """Test clear collection API endpoint"""
        # Add a card first
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        collection_manager.add_card(card_data, 2, False)
        self.assertEqual(len(collection_manager.collection), 1)
        
        response = self.app.post('/api/clear_collection')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify collection was cleared
        self.assertEqual(len(collection_manager.collection), 0)
    
    @patch('app.requests.get')
    def test_import_deckbox_format(self, mock_get):
        """Test importing DeckBox CSV format"""
        # Clear collection before test
        collection_manager.clear_collection()
        
        # Mock Scryfall API responses for different cards
        def mock_api_response(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            if '/cards/6ed/195' in url:
                # Lightning Bolt response
                mock_response.json.return_value = {
                    'id': 'lightning-bolt-id',
                    'name': 'Lightning Bolt',
                    'set': '6ed',
                    'set_name': 'Classic Sixth Edition',
                    'collector_number': '195',
                    'rarity': 'common',
                    'image_uris': {'small': 'http://example.com/bolt.jpg'}
                }
            elif '/cards/6ed/68' in url:
                # Counterspell response  
                mock_response.json.return_value = {
                    'id': 'counterspell-id',
                    'name': 'Counterspell',
                    'set': '6ed',
                    'set_name': 'Classic Sixth Edition',
                    'collector_number': '68',
                    'rarity': 'common',
                    'image_uris': {'small': 'http://example.com/counter.jpg'}
                }
            else:
                # Default fallback
                mock_response.json.return_value = {
                    'id': 'default-id',
                    'name': 'Default Card',
                    'set': '6ed',
                    'set_name': 'Classic Sixth Edition',
                    'collector_number': '1',
                    'rarity': 'common',
                    'image_uris': {'small': 'http://example.com/default.jpg'}
                }
            
            return mock_response
        
        mock_get.side_effect = mock_api_response
        
        # DeckBox CSV format
        deckbox_csv = '''Count,"Tradelist Count",Name,Edition,"Card Number",Condition,Foil,Signed,"Artist Proof","Altered Art",Misprint,Promo,Textless,"My Price"
2,,"Lightning Bolt","Classic Sixth Edition",195,,,,,,,,,0.25
1,,"Counterspell","Classic Sixth Edition",68,,foil,,,,,,,1.50'''
        
        result = collection_manager.import_from_csv(deckbox_csv)
        
        # Should successfully import both cards
        self.assertEqual(result['imported_count'], 2)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['errors']), 0)
        
        # Check that cards were added to collection
        self.assertEqual(len(collection_manager.collection), 2)
        
        # Check that foil detection works
        foil_cards = [card for card in collection_manager.collection.values() if card['foil']]
        regular_cards = [card for card in collection_manager.collection.values() if not card['foil']]
        
        self.assertEqual(len(foil_cards), 1)
        self.assertEqual(len(regular_cards), 1)
        self.assertEqual(foil_cards[0]['name'], 'Counterspell')  # Counterspell is foil in CSV
        self.assertEqual(regular_cards[0]['name'], 'Lightning Bolt')  # Lightning Bolt is regular
        self.assertEqual(regular_cards[0]['quantity'], 2)

    def test_export_collection_mtggoldfish_format(self):
        """Test CSV export route with MTGGoldfish format"""
        # Add a card to collection first
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        collection_manager.add_card(card_data, 2, False)
        
        response = self.app.get('/export?format=mtggoldfish')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        self.assertIn(b'Lightning Bolt', response.data)
        
        # Check filename
        self.assertIn('mtg_collection_mtggoldfish.csv', response.headers.get('Content-Disposition', ''))
    
    def test_export_collection_deckbox_format(self):
        """Test CSV export route with DeckBox format"""
        # Add a card to collection first
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        collection_manager.add_card(card_data, 2, False)
        
        response = self.app.get('/export?format=deckbox')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        self.assertIn(b'Lightning Bolt', response.data)
        
        # Check filename
        self.assertIn('mtg_collection_deckbox.csv', response.headers.get('Content-Disposition', ''))
        
        # Check that it has DeckBox format headers
        csv_content = response.data.decode('utf-8')
        self.assertIn('Count,Tradelist Count,Name,Edition,Card Number', csv_content)
    
    def test_export_collection_invalid_format(self):
        """Test CSV export route with invalid format defaults to MTGGoldfish"""
        # Add a card to collection first
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        collection_manager.add_card(card_data, 2, False)
        
        response = self.app.get('/export?format=invalid')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        self.assertIn(b'Lightning Bolt', response.data)
        
        # Check filename defaults to MTGGoldfish
        self.assertIn('mtg_collection_mtggoldfish.csv', response.headers.get('Content-Disposition', ''))
    
    def test_export_collection_default_format(self):
        """Test CSV export route with no format parameter defaults to MTGGoldfish"""
        # Add a card to collection first
        card_data = {
            'id': 'test-card',
            'name': 'Lightning Bolt',
            'set': 'neo',
            'set_name': 'Kamigawa: Neon Dynasty',
            'collector_number': '123',
            'rarity': 'common'
        }
        collection_manager.add_card(card_data, 2, False)
        
        response = self.app.get('/export')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        self.assertIn(b'Lightning Bolt', response.data)
        
        # Check filename defaults to MTGGoldfish
        self.assertIn('mtg_collection_mtggoldfish.csv', response.headers.get('Content-Disposition', ''))


if __name__ == '__main__':
    unittest.main()
