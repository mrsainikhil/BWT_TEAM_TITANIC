import concurrent.futures
import requests
import random

def send(txn):
    try:
        r = requests.post("http://localhost:8000/transaction", json=txn, timeout=2)
        print(r.json())
    except Exception as e:
        print({"error": str(e)})

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

def main():
    txns = []
    for _ in range(5):
        txns.append(scenario_high_amount("user_42"))
    for _ in range(5):
        txns.append(scenario_new_location("user_42"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(send, txns))

if __name__ == "__main__":
    main()
