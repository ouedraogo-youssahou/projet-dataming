import asyncio, aiohttp, base64

async def t():
    user = "mathematics"
    pw = "succinct"
    basic = base64.b64encode(f"{user}:{pw}".encode()).decode()
    hdrs = {"Authorization": f"Basic {basic}"}
    api = "https://famous-breath.localsite.io/wp-json/wc/v3/products"
    params = {
        "per_page": 3,
        "consumer_key": "ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17",
        "consumer_secret": "cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65",
    }
    async with aiohttp.ClientSession(headers=hdrs) as s:
        async with s.get(api, params=params, timeout=10) as r:
            print(f"Status: {r.status}")
            if r.status == 200:
                data = await r.json()
                print(f"Products: {len(data)}")
                for p in data[:5]:
                    name = p.get("name", "")
                    price = p.get("price", "")
                    print(f"  - {name} (${price})")
            else:
                txt = await r.text()
                print(f"Resp: {txt[:400]}")

asyncio.run(t())