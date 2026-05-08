import json

with open("/app/data/raw/products.json") as f:
    products = json.load(f)

print("Total products:", len(products))

cats = {}
for p in products:
    c = p.get("category", "")
    cats[c] = cats.get(c, 0) + 1
print("Categories:", cats)

prices = [p["price"] for p in products if p["price"] > 0]
if prices:
    print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")
    print(f"Avg price: ${sum(prices)/len(prices):.2f}")

ratings = [p["rating"] for p in products if p["rating"] > 0]
if ratings:
    print(f"Ratings: {min(ratings):.1f} - {max(ratings):.1f}")
    print(f"Products with reviews: {len(ratings)}")

print("\nSample 3 products:")
for p in products[:3]:
    name = p["name"][:50]
    price = p["price"]
    cat = p["category"]
    rating = p["rating"]
    reviews = p["reviews_count"]
    print(f"  - {name} | ${price:.2f} | {cat} | rating: {rating} | reviews: {reviews}")