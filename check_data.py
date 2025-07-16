import sqlite3

conn = sqlite3.connect('mtg_cache.db')
cursor = conn.cursor()

# Check the actual case of data in the database
cursor.execute("SELECT name, set_code FROM cards_cache WHERE name LIKE 'Forest' AND set_code LIKE 'zen' LIMIT 5")
results = cursor.fetchall()
print('Sample Forest cards in zen set:')
for name, set_code in results:
    print(f'  name: "{name}", set_code: "{set_code}"')

# Check distinct name variations
cursor.execute("SELECT DISTINCT name FROM cards_cache WHERE name LIKE 'Forest' LIMIT 5")
forest_names = cursor.fetchall()
print('\nDistinct Forest name variations:')
for name, in forest_names:
    print(f'  "{name}"')

conn.close()
