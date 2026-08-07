# Scaling and Low Latency — High Frequency Design

> **How do institutional exchanges handle millions of transactions per second?** By optimizing memory layout, minimizing lock contention, and avoiding dynamic allocation.

---

## 1. Bottlenecks in Python Matching Engines

1. **Global Interpreter Lock (GIL)**: Multi-threading in Python is constrained by GIL for CPU-bound tasks.
2. **Object Overhead**: Python objects (`Order`, `RBNode`) have heap overhead and pointer-chasing overhead in memory cache hits (L1/L2 cache misses).
3. **Garbage Collection (GC)**: Frequent allocations and deallocations trigger GC pauses.

---

## 2. Low-Latency Optimization Techniques

| Technique | Description |
|-----------|-------------|
| **Fixed Price Bins** | Instead of an RB-Tree, use a flat array of price levels for fixed-tick assets (O(1) price lookup). |
| **Object Pooling** | Pre-allocate fixed `Order` arrays to avoid heap allocations during live trading. |
| **Intrusive Double Linked Lists** | Embed `prev`/`next` pointers directly within the `Order` struct. |
| **Kernel Bypass (DPDK/Solarflare)** | Bypass OS network stack for ultra-low latency packet ingestion. |
