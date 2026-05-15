#!/usr/bin/env python
"""Test WooCommerce API access via ngrok tunnel."""
import urllib.request
import json
import base64

# Configuration
base_url = "https://stethoscopic-revivably-jamey.ngrok-free.dev"
consumer_key = "ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17"
consumer_secret = "cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65"

# Test 1: With consumer key/secret in query params (WooCommerce standard)
print("=== Test 1: Query params auth ===")
url = f"{base_url}/wp-json/wc/v3/products?consumer_key={consumer_key}&consumer_secret={consumer_secret}&per_page=2"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        print(f"Status: {resp.status}, Got {len(data) if isinstance(data, list) else 'dict'} items")
        if isinstance(data, list) and len(data) > 0:
            print("First product:", data[0].get('name', 'N/A'))
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)[:200]}")

# Test 2: With Basic Auth (mathematics/succinct) - from ngrok logs we see this user
print("\n=== Test 2: Basic Auth (mathematics/succinct) ===")
url2 = f"{base_url}/wp-json/wc/v3/products?per_page=2"
auth = base64.b64encode(b"mathematics:succinct").decode()
req2 = urllib.request.Request(url2, headers={"Authorization": f"Basic {auth}"})
try:
    with urllib.request.urlopen(req2, timeout=10) as resp:
        data = json.loads(resp.read())
        print(f"Status: {resp.status}, Got {len(data) if isinstance(data, list) else 'dict'} items")
        if isinstance(data, list) and len(data) > 0:
            print("First product:", data[0].get('name', 'N/A'))
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)[:200]}")

# Test 3: Test root endpoint
print("\n=== Test 3: WordPress root ===")
try:
    with urllib.request.urlopen(f"{base_url}/", timeout=10) as resp:
        print(f"WordPress root status: {resp.status}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)[:200]}")
