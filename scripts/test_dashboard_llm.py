#!/usr/bin/env python
"""Test script to verify dashboard LLM chat works end-to-end."""
import os
import sys
sys.path.insert(0, '/app/src')

from src.dashboard.app import ask_llm, get_llm_wrapper

# Test 1: Wrapper instantiation
print("=== Test 1: LLMWrapper instantiation ===")
llm = get_llm_wrapper()
print(f"DeepSeek key present: {bool(llm.deepseek_key)}")
print(f"Groq key present: {bool(llm.groq_key)}")

# Test 2: Simple ask_llm call (with dummy context)
print("\n=== Test 2: ask_llm with context ===")
dummy_products = [
    {"name": "Widget A", "price": 10.0, "category": "Tech", "rating": 4.5, "availability": True},
    {"name": "Widget B", "price": 20.0, "category": "Tech", "rating": 4.0, "availability": True},
]
try:
    response = ask_llm("Quels sont les 2 produits les moins chers ?", products_context=dummy_products)
    print(f"Response: {response[:150]}")
except Exception as e:
    print(f"Error: {e}")

print("\n✅ Tests completed")
