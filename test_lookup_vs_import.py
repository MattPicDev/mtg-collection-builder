import io
import time
from app import collection_manager

# Test just the cache lookup part
test_csv = """Name,Set,Collector Number,Quantity,Foil,Condition,Language
Forest,6ED,347,1,No,Near Mint,English
Mountain,6ED,348,2,No,Near Mint,English
Plains,6ED,349,1,No,Near Mint,English
"""

print("Testing individual cache lookups...")
cards = [
    ('Forest', '6ED', '347'),
    ('Mountain', '6ED', '348'),
    ('Plains', '6ED', '349')
]

from app import bulk_cache
total_time = 0
for name, set_code, collector_number in cards:
    start = time.time()
    result = bulk_cache.find_card_in_cache(name, set_code, collector_number)
    end = time.time()
    lookup_time = (end - start) * 1000
    total_time += lookup_time
    print(f"  {name} in {set_code}: {lookup_time:.2f}ms - {'Found' if result else 'Not found'}")

print(f"Total lookup time: {total_time:.2f}ms")
print(f"Average per lookup: {total_time/len(cards):.2f}ms")

# Test the full import to see where the extra time is coming from
print("\nTesting full import...")
start = time.time()
result = collection_manager.import_from_csv(test_csv)
end = time.time()

print(f"Full import took: {(end-start)*1000:.2f}ms")
print(f"Cards imported: {result['imported_count']}")
print(f"Cache hits: {result['cache_hits']}")
print(f"API calls: {result['api_calls']}")
print(f"Per card: {((end-start)*1000)/result['imported_count']:.2f}ms")

# Clear collection for next test
collection_manager.clear_collection()
