import sqlite3

conn = sqlite3.connect('mtg_cache.db')
cursor = conn.cursor()

# Check actual card names for common cards
cursor.execute("SELECT DISTINCT name FROM cards_cache WHERE name IN ('Forest', 'Mountain', 'Plains', 'Island', 'Swamp', 'Lightning Bolt') ORDER BY name")
results = cursor.fetchall()
print('Card names in database:')
for name, in results:
    print(f'  "{name}"')

# Check set codes for zen
cursor.execute("SELECT DISTINCT set_code FROM cards_cache WHERE set_code = 'zen'")
results = cursor.fetchall()
print('\nSet codes in database:')
for set_code, in results:
    print(f'  "{set_code}"')

conn.close()
