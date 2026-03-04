import asyncio
import sys, os
sys.path.append(os.path.abspath("."))
from app.main import process_transaction, Transaction
async def run():
    t1 = Transaction(user_id="user_42", amount=25000.0, location="Delhi", device_id="device_1", merchant="Electronics", timestamp="23:15", upi_app="GPay", upi_lat=28.6139, upi_lon=77.2090)
    t2 = Transaction(user_id="user_42", amount=1200.0, location="Mumbai", device_id="device_2", merchant="Grocery", timestamp="12:05", upi_app="PhonePe", upi_lat=19.0760, upi_lon=72.8777)
    r1 = await process_transaction(t1, None)
    r2 = await process_transaction(t2, None)
    print(r1.body.decode())
    print(r2.body.decode())
if __name__ == "__main__":
    asyncio.run(run())
