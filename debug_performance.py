#!/usr/bin/env python3
"""Debug script to investigate cache performance issues with common cards"""

import sys
import sqlite3
import time
from app import bulk_cache

def check_database_indexes():
    """Check what indexes exist in the database"""
    conn = sqlite3.connect('mtg_cache.db')
    cursor = conn.cursor()
    
    print("=== Database Indexes ===")
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    for name, sql in indexes:
        if not name.startswith('sqlite_'):
            print(f"  {name}: {sql}")
    
    conn.close()

def check_query_performance():
    """Check performance of different query approaches"""
    conn = sqlite3.connect('mtg_cache.db')
    cursor = conn.cursor()
    
    print("\n=== Query Performance Analysis ===")
    
    # Check how many Forest cards exist
    cursor.execute("SELECT COUNT(*) FROM cards_cache WHERE LOWER(name) = LOWER(?)", ('Forest',))
    forest_count = cursor.fetchone()[0]
    print(f"Total Forest cards in cache: {forest_count}")
    
    # Test the current query approach
    print("\nTesting current query approach:")
    start = time.time()
    cursor.execute('''
        SELECT data_json FROM cards_cache 
        WHERE LOWER(name) = LOWER(?) AND LOWER(set_code) = LOWER(?)
        ORDER BY collector_number
    ''', ('Forest', 'zen'))
    result = cursor.fetchone()
    end = time.time()
    print(f"  Current query: {(end-start)*1000:.2f}ms - {'Found' if result else 'Not found'}")
    
    # Test with exact case match (should be faster)
    print("\nTesting case-sensitive approach:")
    start = time.time()
    cursor.execute('''
        SELECT data_json FROM cards_cache 
        WHERE name = ? AND set_code = ?
        ORDER BY collector_number
    ''', ('Forest', 'zen'))
    result = cursor.fetchone()
    end = time.time()
    print(f"  Case-sensitive query: {(end-start)*1000:.2f}ms - {'Found' if result else 'Not found'}")
    
    # Test with composite index lookup
    print("\nTesting with better indexing:")
    cursor.execute("EXPLAIN QUERY PLAN SELECT data_json FROM cards_cache WHERE LOWER(name) = LOWER('Forest') AND LOWER(set_code) = LOWER('zen')")
    query_plan = cursor.fetchall()
    print("  Query plan:")
    for row in query_plan:
        print(f"    {row}")
    
    conn.close()

def test_cache_lookup_performance():
    """Test the cache lookup performance with common cards"""
    print("\n=== Cache Lookup Performance ===")
    
    test_cards = [
        ('Forest', 'zen'),
        ('Mountain', 'zen'),
        ('Plains', 'zen'),
        ('Island', 'zen'),
        ('Swamp', 'zen'),
        ('Lightning Bolt', 'zen'),
        ('Forest', 'lea'),
        ('Mountain', 'lea'),
    ]
    
    for name, set_code in test_cards:
        start = time.time()
        result = bulk_cache.find_card_in_cache(name, set_code)
        end = time.time()
        print(f"  {name} in {set_code}: {(end-start)*1000:.2f}ms - {'Found' if result else 'Not found'}")

def analyze_common_card_distribution():
    """Analyze how common cards are distributed across sets"""
    conn = sqlite3.connect('mtg_cache.db')
    cursor = conn.cursor()
    
    print("\n=== Common Card Distribution ===")
    
    common_cards = ['Forest', 'Mountain', 'Plains', 'Island', 'Swamp']
    
    for card_name in common_cards:
        cursor.execute('''
            SELECT COUNT(DISTINCT set_code) as set_count, COUNT(*) as total_count
            FROM cards_cache 
            WHERE LOWER(name) = LOWER(?)
        ''', (card_name,))
        set_count, total_count = cursor.fetchone()
        print(f"  {card_name}: {total_count} cards across {set_count} sets")
    
    conn.close()

if __name__ == "__main__":
    check_database_indexes()
    check_query_performance()
    test_cache_lookup_performance()
    analyze_common_card_distribution()
