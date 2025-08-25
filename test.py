import asyncio

async def fetch_data(n):
    print(f"Task {n} started")
    await asyncio.sleep(2)
    print(f"Task {n} done")
    return f"Data {n}"

async def main():
    tasks = [fetch_data(1), fetch_data(2), fetch_data(3)]
    results = await asyncio.gather(*tasks)
    print(results)

asyncio.run(main())
