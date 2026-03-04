import asyncio
import aiohttp
import random

async def send(txn):
    async with aiohttp.ClientSession() as s:
        async with s.post("http://localhost:8000/transaction", json=txn) as r:
            print(await r.json())

def scenario_high_amount(user_id):
    return {
        "user_id": user_id,
        "amount": random.uniform(20000, 150000),
        "location": "Delhi",
        "device_id": "device_" + str(random.randint(1, 100)),
        "merchant": "Electronics",
        "timestamp": f"{random.randint(0,23)}:{random.randint(0,59):02d}",
    }

def scenario_new_location(user_id):
    return {
        "user_id": user_id,
        "amount": random.uniform(100, 3000),
        "location": "Mumbai",
        "device_id": "device_" + str(random.randint(1, 100)),
        "merchant": "Grocery",
        "timestamp": f"{random.randint(0,23)}:{random.randint(0,59):02d}",
    }

async def main():
    txns = []
    for _ in range(5):
        txns.append(scenario_high_amount("user_42"))
    for _ in range(5):
        txns.append(scenario_new_location("user_42"))
    await asyncio.gather(*(send(t) for t in txns))

if __name__ == "__main__":
    asyncio.run(main())
