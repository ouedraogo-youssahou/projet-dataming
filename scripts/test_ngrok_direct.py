#!/usr/bin/env python
"""Test direct WooCommerce API via ngrok - check if accessible from host."""
import urllib.request
import json
import base64

base_url = "https://stethoscopic-revivably-jamey.ngrok-free.dev"
consumer_key = "ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17"
consumer_secret = "cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65"

print(f"Testing WooCommerce API at: {base_url}")
print("="*60)

# Test 1: GET products via query params (standard WooCommerce)
url1 = f"{base_url}/wp-json/wc/v3/products?consumer_key={consumer_key}&consumer_secret={consumer_secret}&per_page=3"
print("\n[Test 1] Query param auth:")
try:
    req = urllib.request.Request(url1)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        print(f"  ✅ Status: {r.status}, Got {len(data) if isinstance(data, list) else 'dict'} items")
        if data and isinstance(data, list):
            print(f"  First product: {data[0].get('name', 'N/A')}")
except Exception as e:
    print(f"  ❌ Error: {type(e).__name__}: {str(e)[:200]}")

# Test 2: Basic auth (mathematics/succinct) - common for LocalWP
url2 = f"{base_url}/wp-json/wc/v3/products?per_page=3"
auth = base64.b64encode(b"mathematics:succinct").decode()
print("\n[Test 2] Basic Auth (mathematics/succinct):")
try:
    req2 = urllib.request.Request(url2, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req2, timeout=10) as r:
        data = json.loads(r.read())
        print(f"  ✅ Status: {r.status}, Got {len(data) if isinstance(data, list) else 'dict'} items")
        if data and isinstance(data, list):
            print(f"  First product: {data[0].get('name', 'N/A')}")
except Exception as e:
    print(f"  ❌ Error: {type(e).__name__}: {str(e)[:200]}")

# Test 3: WordPress REST API root (to confirm WP is alive)
print("\n[Test 3] WordPress root:")
try:
    with urllib.request.urlopen(f"{base_url}/", timeout=10) as r:
        print(f"  ✅ WordPress root reachable, status: {r.status}")
except Exception as e:
    print(f"  ❌ Error: {type(e).__name__}: {str(e)[:200]}")

print("\n" + "="*60)
print("If tests fail, the ngrok tunnel may be down or misconfigured.")
print("Restart ngrok on your host: ngrok http 10005")
