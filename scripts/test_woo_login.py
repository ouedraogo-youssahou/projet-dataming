import asyncio, aiohttp, base64

async def t():
    # Utilisation de l'URL ngrok depuis .env
    base_url = "https://stethoscopic-revivably-jamey.ngrok-free.dev"
    api = f"{base_url}/wp-json/wc/v3/products"
    
    user = "mathematics"
    pw = "succinct"
    basic = base64.b64encode(f"{user}:{pw}".encode()).decode()
    hdrs = {"Authorization": f"Basic {basic}"}
    
    params = {
        "per_page": 5,
        "consumer_key": "ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17",
        "consumer_secret": "cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65",
    }
    
    async with aiohttp.ClientSession(headers=hdrs) as s:
        async with s.get(api, params=params, timeout=10) as r:
            print(f"Status: {r.status}")
            if r.status == 200:
                data = await r.json()
                print(f"Products fetched: {len(data)}")
                for p in data[:3]:
                    print(f"  - {p.get('name', '')} (${p.get('price', '')})")
            else:
                txt = await r.text()
                print(f"Response: {txt[:500]}")

asyncio.run(t())