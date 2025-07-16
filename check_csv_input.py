import io
import csv

# Test with sample DeckBox data to see what case we get
sample_deckbox_csv = """Count,Tradelist Count,Name,Edition,Card Number,Condition,Foil,Signed,Artist Proof,Altered Art,Misprint,Promo,Textless,My Price
1,,Forest,Classic Sixth Edition,347,Near Mint,,,,,,,
2,,Mountain,Classic Sixth Edition,348,Near Mint,,,,,,,
1,,Lightning Bolt,Classic Sixth Edition,163,Near Mint,,,,,,,
"""

# Test with sample MTGGoldfish data
sample_mtggoldfish_csv = """Name,Set,Collector Number,Quantity,Foil,Condition,Language
Forest,6ED,347,1,No,Near Mint,English
Mountain,6ED,348,2,No,Near Mint,English
Lightning Bolt,6ED,163,1,No,Near Mint,English
"""

print("=== DeckBox CSV Data ===")
csv_file = io.StringIO(sample_deckbox_csv)
reader = csv.DictReader(csv_file)
for row in reader:
    name = row.get('Name', '').strip()
    set_identifier = row.get('Edition', '').strip()
    print(f'Name: "{name}", Set: "{set_identifier}"')

print("\n=== MTGGoldfish CSV Data ===")
csv_file = io.StringIO(sample_mtggoldfish_csv)
reader = csv.DictReader(csv_file)
for row in reader:
    name = row.get('Name', '').strip()
    set_identifier = row.get('Set', '').strip()
    print(f'Name: "{name}", Set: "{set_identifier}"')
