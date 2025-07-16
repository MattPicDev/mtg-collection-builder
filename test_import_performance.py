import io
import time
from app import collection_manager

# Test import performance with common cards
test_csv = """Name,Set,Collector Number,Quantity,Foil,Condition,Language
Forest,6ED,347,1,No,Near Mint,English
Mountain,6ED,348,2,No,Near Mint,English
Plains,6ED,349,1,No,Near Mint,English
Island,6ED,350,1,No,Near Mint,English
Swamp,6ED,351,1,No,Near Mint,English
Lightning Bolt,6ED,163,1,No,Near Mint,English
Forest,LEA,294,1,No,Near Mint,English
Mountain,LEA,295,1,No,Near Mint,English
Plains,LEA,296,1,No,Near Mint,English
Island,LEA,297,1,No,Near Mint,English
"""

print("Testing import performance with common cards...")
start = time.time()
result = collection_manager.import_from_csv(test_csv)
end = time.time()

print(f"Import took: {(end-start)*1000:.2f}ms")
print(f"Cards imported: {result['imported_count']}")
print(f"Cache hits: {result['cache_hits']}")
print(f"API calls: {result['api_calls']}")
print(f"Cache hit rate: {result['cache_hit_rate']:.1f}%")
print(f"Average per card: {((end-start)*1000)/result['imported_count']:.2f}ms")

# Clear collection for next test
collection_manager.clear_collection()
