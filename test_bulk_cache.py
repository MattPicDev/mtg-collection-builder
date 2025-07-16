"""
Test suite for bulk data caching functionality
"""
import pytest
import sqlite3
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from app import BulkDataCache


class TestBulkDataCache:
    """Test bulk data caching functionality"""
    
    def setup_method(self):
        """Set up test environment with temporary database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.cache = BulkDataCache(self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test that database is properly initialized"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check that tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'bulk_metadata' in tables
        assert 'cards_cache' in tables
        
        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert any('idx_cards_name' in idx for idx in indexes)
        assert any('idx_cards_set' in idx for idx in indexes)
        
        conn.close()
    
    def test_cache_validation(self):
        """Test cache validation logic"""
        # Fresh cache should be invalid
        assert not self.cache.is_cache_valid()
        
        # Add some recent metadata
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        from datetime import datetime
        cursor.execute('''
            INSERT INTO bulk_metadata (data_type, download_url, updated_at, size, etag)
            VALUES (?, ?, ?, ?, ?)
        ''', ('default_cards', 'http://example.com', datetime.now().isoformat(), 1000, 'test-etag'))
        conn.commit()
        conn.close()
        
        # Should now be valid
        assert self.cache.is_cache_valid()
    
    @patch('requests.get')
    def test_bulk_data_info_retrieval(self, mock_get):
        """Test retrieval of bulk data information"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'data': [
                {'type': 'default_cards', 'download_uri': 'http://example.com/cards.json', 'size': 1000},
                {'type': 'other_type', 'download_uri': 'http://example.com/other.json', 'size': 500}
            ]
        }
        mock_get.return_value = mock_response
        
        bulk_info = self.cache.get_bulk_data_info()
        
        assert bulk_info is not None
        assert bulk_info['type'] == 'default_cards'
        assert bulk_info['download_uri'] == 'http://example.com/cards.json'
    
    @patch('requests.get')
    def test_bulk_data_download_and_caching(self, mock_get):
        """Test downloading and caching bulk data"""
        # Mock bulk data info
        mock_info_response = MagicMock()
        mock_info_response.raise_for_status.return_value = None
        mock_info_response.json.return_value = {
            'data': [
                {'type': 'default_cards', 'download_uri': 'http://example.com/cards.json', 'size': 1000, 'content_encoding': 'gzip'}
            ]
        }
        
        # Mock bulk data download
        mock_data_response = MagicMock()
        mock_data_response.raise_for_status.return_value = None
        mock_data_response.json.return_value = [
            {
                'id': 'card1',
                'name': 'Lightning Bolt',
                'set': 'lea',
                'collector_number': '161',
                'set_name': 'Limited Edition Alpha',
                'rarity': 'common',
                'image_uris': {'small': 'http://example.com/image1.jpg'}
            },
            {
                'id': 'card2',
                'name': 'Black Lotus',
                'set': 'lea',
                'collector_number': '232',
                'set_name': 'Limited Edition Alpha',
                'rarity': 'rare',
                'image_uris': {'small': 'http://example.com/image2.jpg'}
            }
        ]
        
        mock_get.side_effect = [mock_info_response, mock_data_response]
        
        # Track progress calls
        progress_calls = []
        def progress_callback(data):
            progress_calls.append(data)
        
        result = self.cache.download_and_cache_bulk_data(progress_callback)
        
        assert result is True
        assert len(progress_calls) > 0
        
        # Check that data was cached
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM cards_cache')
        count = cursor.fetchone()[0]
        assert count == 2
        
        # Check specific card data
        cursor.execute('SELECT * FROM cards_cache WHERE name = ?', ('Lightning Bolt',))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == 'Lightning Bolt'  # name
        assert row[2] == 'lea'  # set_code
        assert row[3] == '161'  # collector_number
        
        conn.close()
    
    def test_card_lookup_in_cache(self):
        """Test finding cards in cache"""
        # Add test data to cache
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        test_card_data = {
            'id': 'card1',
            'name': 'Lightning Bolt',
            'set': 'lea',
            'collector_number': '161',
            'set_name': 'Limited Edition Alpha',
            'rarity': 'common',
            'image_uris': {'small': 'http://example.com/image1.jpg'}
        }
        
        cursor.execute('''
            INSERT INTO cards_cache 
            (id, name, set_code, collector_number, set_name, rarity, image_url, data_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_card_data['id'],
            test_card_data['name'],
            test_card_data['set'],
            test_card_data['collector_number'],
            test_card_data['set_name'],
            test_card_data['rarity'],
            test_card_data['image_uris']['small'],
            json.dumps(test_card_data),
            '2023-01-01T00:00:00'
        ))
        conn.commit()
        conn.close()
        
        # Test exact match
        result = self.cache.find_card_in_cache('Lightning Bolt', 'lea', '161')
        assert result is not None
        assert result['name'] == 'Lightning Bolt'
        assert result['set'] == 'lea'
        assert result['collector_number'] == '161'
        
        # Test match without collector number
        result = self.cache.find_card_in_cache('Lightning Bolt', 'lea')
        assert result is not None
        assert result['name'] == 'Lightning Bolt'
        
        # Test no match
        result = self.cache.find_card_in_cache('Nonexistent Card', 'lea')
        assert result is None
    
    def test_fuzzy_card_search(self):
        """Test fuzzy card searching in cache"""
        # Add test data to cache
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        cards = [
            {'id': '1', 'name': 'Lightning Bolt', 'set': 'lea', 'collector_number': '161'},
            {'id': '2', 'name': 'Lightning Storm', 'set': 'lea', 'collector_number': '162'},
            {'id': '3', 'name': 'Lightning Bolt', 'set': 'zen', 'collector_number': '161'},
        ]
        
        for card in cards:
            cursor.execute('''
                INSERT INTO cards_cache 
                (id, name, set_code, collector_number, set_name, rarity, image_url, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                card['id'],
                card['name'],
                card['set'],
                card['collector_number'],
                card['set'],
                'common',
                '',
                json.dumps(card),
                '2023-01-01T00:00:00'
            ))
        conn.commit()
        conn.close()
        
        # Test search with partial name
        results = self.cache.search_cards_in_cache('Light', 'lea')
        assert len(results) == 2
        
        # Test search with full name should prioritize exact match
        results = self.cache.search_cards_in_cache('Lightning Bolt', 'lea')
        assert len(results) >= 1
        assert results[0]['name'] == 'Lightning Bolt'
        assert results[0]['set'] == 'lea'
    
    def test_set_identifier_normalization(self):
        """Test set identifier normalization"""
        # Test 3-letter codes
        assert self.cache._normalize_set_identifier('lea') == 'lea'
        assert self.cache._normalize_set_identifier('ZEN') == 'zen'
        
        # Test known full names
        assert self.cache._normalize_set_identifier('Limited Edition Alpha') == 'lea'
        assert self.cache._normalize_set_identifier('Sixth Edition') == '6ed'
        assert self.cache._normalize_set_identifier('Zendikar') == 'zen'
        
        # Test unknown names (should return lowercase)
        assert self.cache._normalize_set_identifier('Unknown Set') == 'unknown set'
    
    def test_cache_statistics(self):
        """Test cache statistics retrieval"""
        # Add test data
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Add some cards
        for i in range(5):
            cursor.execute('''
                INSERT INTO cards_cache 
                (id, name, set_code, collector_number, set_name, rarity, image_url, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f'card{i}',
                f'Card {i}',
                'lea' if i < 3 else 'zen',
                str(i),
                'Test Set',
                'common',
                '',
                json.dumps({'id': f'card{i}', 'name': f'Card {i}'}),
                '2023-01-01T00:00:00'
            ))
        
        # Add metadata
        from datetime import datetime
        cursor.execute('''
            INSERT INTO bulk_metadata (data_type, download_url, updated_at, size, etag)
            VALUES (?, ?, ?, ?, ?)
        ''', ('default_cards', 'http://example.com', datetime.now().isoformat(), 1000, 'test-etag'))
        
        conn.commit()
        conn.close()
        
        stats = self.cache.get_cache_stats()
        
        assert stats['total_cards'] == 5
        assert stats['total_sets'] == 2  # lea and zen
        assert stats['last_update'] is not None
        assert stats['cache_valid'] is True
    
    def test_get_set_cards_from_cache(self):
        """Test retrieving cards for a specific set from cache"""
        # Add test data
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Add cards for LEA set
        lea_cards = [
            {'id': 'card1', 'name': 'Lightning Bolt', 'set': 'lea', 'collector_number': '161'},
            {'id': 'card2', 'name': 'Black Lotus', 'set': 'lea', 'collector_number': '232'},
        ]
        
        # Add cards for ZEN set
        zen_cards = [
            {'id': 'card3', 'name': 'Zendikar Card', 'set': 'zen', 'collector_number': '001'},
        ]
        
        for card in lea_cards + zen_cards:
            cursor.execute('''
                INSERT INTO cards_cache 
                (id, name, set_code, collector_number, set_name, rarity, image_url, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                card['id'],
                card['name'],
                card['set'],
                card['collector_number'],
                card['set'],
                'common',
                '',
                json.dumps(card),
                '2023-01-01T00:00:00'
            ))
        
        conn.commit()
        conn.close()
        
        # Test getting LEA cards
        lea_results = self.cache.get_set_cards_from_cache('lea')
        assert len(lea_results) == 2
        assert all(card['set'] == 'lea' for card in lea_results)
        
        # Test getting ZEN cards
        zen_results = self.cache.get_set_cards_from_cache('zen')
        assert len(zen_results) == 1
        assert zen_results[0]['set'] == 'zen'
        
        # Test getting non-existent set
        empty_results = self.cache.get_set_cards_from_cache('nonexistent')
        assert len(empty_results) == 0
    
    def test_cache_cards_batch(self):
        """Test batch caching of cards"""
        test_cards = [
            {
                'id': 'card1',
                'name': 'Lightning Bolt',
                'set': 'lea',
                'collector_number': '161',
                'set_name': 'Limited Edition Alpha',
                'rarity': 'common',
                'image_uris': {'small': 'http://example.com/image1.jpg'}
            },
            {
                'id': 'card2',
                'name': 'Black Lotus',
                'set': 'lea',
                'collector_number': '232',
                'set_name': 'Limited Edition Alpha',
                'rarity': 'rare',
                'image_uris': {'small': 'http://example.com/image2.jpg'}
            }
        ]
        
        # Cache the cards
        cached_count = self.cache.cache_cards_batch(test_cards)
        assert cached_count == 2
        
        # Verify they were cached
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM cards_cache')
        count = cursor.fetchone()[0]
        assert count == 2
        
        # Verify specific card data
        cursor.execute('SELECT * FROM cards_cache WHERE name = ?', ('Lightning Bolt',))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == 'Lightning Bolt'  # name
        assert row[2] == 'lea'  # set_code
        assert row[3] == '161'  # collector_number
        
        conn.close()
    
    def test_get_set_completion_stats(self):
        """Test getting completion statistics for a set"""
        # Add test data
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Add some LEA cards
        for i in range(3):
            cursor.execute('''
                INSERT INTO cards_cache 
                (id, name, set_code, collector_number, set_name, rarity, image_url, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f'card{i}',
                f'Card {i}',
                'lea',
                str(i),
                'Limited Edition Alpha',
                'common',
                '',
                json.dumps({'id': f'card{i}', 'name': f'Card {i}'}),
                '2023-01-01T00:00:00'
            ))
        
        conn.commit()
        conn.close()
        
        # Test stats for LEA (has cards)
        lea_stats = self.cache.get_set_completion_stats('lea')
        assert lea_stats['set_code'] == 'lea'
        assert lea_stats['cached_cards'] == 3
        assert lea_stats['cache_available'] == True
        
        # Test stats for non-existent set
        empty_stats = self.cache.get_set_completion_stats('nonexistent')
        assert empty_stats['set_code'] == 'nonexistent'
        assert empty_stats['cached_cards'] == 0
        assert empty_stats['cache_available'] == False
