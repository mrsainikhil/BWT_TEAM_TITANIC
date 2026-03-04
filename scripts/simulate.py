import concurrent.futures
import requests
import random
import argparse

def send(txn):
    try:
        r = requests.post("http://localhost:8000/transaction", json=txn, timeout=2)
        print(r.json())
    except Exception as e:
        print({"error": str(e)})

def scenario_high_amount(user_id, location="Delhi", payee="person_abc", lat=None, lon=None):
    d = {
        "user_id": user_id,
        "amount": random.uniform(20000, 150000),
        "location": location,
        "upi_app": random.choice(["GPay", "PhonePe", "Paytm"]),
        "device_id": "device_" + str(random.randint(1, 100)),
        "merchant": "Electronics",
        "timestamp": f"{random.randint(0,23)}:{random.randint(0,59):02d}",
        "payee_id": payee,
    }
    if lat is None:
        lat = 28.6139 + random.uniform(-0.01, 0.01)
    if lon is None:
        lon = 77.2090 + random.uniform(-0.01, 0.01)
    d["upi_lat"] = lat
    d["upi_lon"] = lon
    return d

def scenario_new_location(user_id, location="Mumbai", payee="person_new", lat=None, lon=None):
    d = {
        "user_id": user_id,
        "amount": random.uniform(100, 3000),
        "location": location,
        "upi_app": random.choice(["GPay", "PhonePe", "Paytm"]),
        "device_id": "device_" + str(random.randint(1, 100)),
        "merchant": "Grocery",
        "timestamp": f"{random.randint(0,23)}:{random.randint(0,59):02d}",
        "payee_id": payee,
    }
    if lat is None:
        lat = 19.0760 + random.uniform(-0.02, 0.02)
    if lon is None:
        lon = 72.8777 + random.uniform(-0.02, 0.02)
    d["upi_lat"] = lat
    d["upi_lon"] = lon
    return d

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="user_42")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--actual-lat", type=float, default=None)
    parser.add_argument("--actual-lon", type=float, default=None)
    parser.add_argument("--txn-location", default="Delhi")
    parser.add_argument("--payee", default="person_abc")
    args = parser.parse_args()
    txns = []
    for _ in range(args.count):
        txns.append(scenario_high_amount(args.user, location=args.txn_location, payee=args.payee, lat=args.actual_lat, lon=args.actual_lon))
    for _ in range(args.count):
        txns.append(scenario_new_location(args.user, location="Mumbai", payee="person_new", lat=args.actual_lat, lon=args.actual_lon))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(send, txns))

if __name__ == "__main__":
    main()
