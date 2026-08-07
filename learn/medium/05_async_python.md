# Async Python — asyncio, Coroutines, and Event Loops

> **What is async Python?** It is a programming model that lets Python perform multiple tasks concurrently without needing multiple threads or processes.
> For an exchange server handling thousands of incoming API requests, async allows high throughput and efficient I/O handling.

---

## 1. Synchronous vs. Asynchronous Execution

### Synchronous Execution (Blocking)
In synchronous Python, each task blocks the main thread until it completes.

```python
import time

def fetch_data():
    time.sleep(2)  # Blocks execution for 2 seconds
    return "Data"

print("Start")
fetch_data()  # Pauses execution completely
print("Done")
```

### Asynchronous Execution (Non-Blocking)
In asynchronous Python, when a task is waiting (e.g. for database I/O or network responses), execution switches to another task.

```python
import asyncio

async def fetch_data():
    await asyncio.sleep(2)  # Yields control back to the event loop
    return "Data"

async def main():
    print("Start")
    await fetch_data()
    print("Done")

asyncio.run(main())
```

---

## 2. Core Concepts: `async`, `await`, and Coroutines

- **`async def`**: Declares a coroutine function. Calling it returns a coroutine object without executing it immediately.
- **`await`**: Pauses the execution of the coroutine until the awaited task completes, freeing the event loop to execute other coroutines.
- **Event Loop**: The central loop managing and dispatching execution of asynchronous tasks.

```python
async def get_price(symbol: str) -> float:
    await asyncio.sleep(0.1)  # Simulating async network call
    return 150.0

async def process():
    # Calling get_price returns a coroutine object
    coro = get_price("AAPL")
    # Awaiting executes the coroutine and extracts the result
    price = await coro
    print(f"Price: {price}")
```

---

## 3. Running Concurrent Tasks with `asyncio.gather`

When multiple independent operations need to run simultaneously, `asyncio.gather` fires them concurrently.

```python
async def fetch_orderbook(symbol: str):
    await asyncio.sleep(0.05)
    return f"Book for {symbol}"

async def main():
    # Runs all 3 calls concurrently on the single-threaded event loop
    results = await asyncio.gather(
        fetch_orderbook("AAPL"),
        fetch_orderbook("GOOGL"),
        fetch_orderbook("MSFT")
    )
    print(results)

asyncio.run(main())
```

---

## 4. How Our Exchange Integrates `asyncio`

In our Order Matching Engine, `Exchange` operations are asynchronous to handle API requests and WebSocket broadcasts cleanly:

```python
# src/engine/exchange.py snippet

class Exchange:
    async def submit_order(self, symbol: str, side: str, order_type: str, price: float | None, quantity: int):
        async with self._locks[symbol]:
            # Critical Section: Exclusive lock per symbol prevents order race conditions
            order, trades = self._order_type_handler.submit_limit(engine, side, price, quantity)
        
        # Async notification after releasing the lock
        await self._broadcast_trade(symbol, trades)
        return order
```
