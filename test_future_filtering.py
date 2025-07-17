#!/usr/bin/env python3
"""
Test script to verify future set filtering.
"""

from datetime import datetime, timedelta
import time

# Test the date filtering logic
print("Testing future set filtering logic")

# Mock sets with various dates
today = datetime.now().date()
future_date = today + timedelta(days=30)
past_date = today - timedelta(days=30)

test_sets = [
    {'name': 'Current Set', 'released_at': today.strftime('%Y-%m-%d')},
    {'name': 'Future Set', 'released_at': future_date.strftime('%Y-%m-%d')},
    {'name': 'Past Set', 'released_at': past_date.strftime('%Y-%m-%d')},
    {'name': 'Very Future Set', 'released_at': '2026-01-01'},
    {'name': 'Ancient Set', 'released_at': '2020-01-01'}
]

print(f"Today's date: {today}")
print(f"Test sets:")
for s in test_sets:
    print(f"  {s['name']}: {s['released_at']}")

# Apply filtering logic
filtered_sets = []
for s in test_sets:
    try:
        release_date = datetime.strptime(s['released_at'], '%Y-%m-%d').date()
        if release_date <= today:
            filtered_sets.append(s)
    except ValueError:
        continue

print(f"\nFiltered sets (should exclude future sets):")
for s in filtered_sets:
    print(f"  {s['name']}: {s['released_at']}")

print(f"\nFiltered out {len(test_sets) - len(filtered_sets)} future sets")
