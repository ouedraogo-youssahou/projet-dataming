#!/usr/bin/env python
"""Test chatbot response with real product data."""
import sys
sys.path.insert(0, '/app/src')

from dashboard.app import ask_llm, get_llm_wrapper

# Load products
import json
from pathlib import Path
products_path = Path('/app/data/raw/products.json')
products = json.load(open(products_path))

print(f"Loaded {len(products)} products")
print("Testing chatbot...")

# Test 1: Ask for cheapest products
question = "Quels sont les 5 produits les moins chers ?"
resp = ask_llm(question, products=products)
print(f"\nQ: {question}")
print(f"A: {resp[:300]}")

# Test 2: Count
question2 = "Combien de produits sont disponibles au total ?"
resp2 = ask_llm(question2, products=products)
print(f"\nQ: {question2}")
print(f"A: {resp2[:200]}")
