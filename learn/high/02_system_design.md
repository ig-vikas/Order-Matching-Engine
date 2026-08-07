# System Design — Architectural Overview

> **High-Level System Design:** Explains how client apps, API services, in-memory matching engines, and persistent databases interact.

---

## 1. System Topology

```
                  ┌──────────────────────┐
                  │   HTTP / WebSocket   │
                  │       Clients        │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │    FastAPI Server    │
                  │ (Routing & Security) │
                  └──────────┬───────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                   Exchange Orchestrator                  │
│                                                          │
│  Symbol "AAPL" Lock          Symbol "GOOGL" Lock         │
│  ┌────────────────────┐      ┌────────────────────┐      │
│  │   MatchingEngine   │      │   MatchingEngine   │      │
│  │(RB-Tree + DLL Book)│      │(RB-Tree + DLL Book)│      │
│  └─────────┬──────────┘      └─────────┬──────────┘      │
└────────────┼───────────────────────────┼─────────────────┘
             │                           │
             ▼                           ▼
  ┌─────────────────────┐     ┌─────────────────────┐
  │ WebSocket Broadcast │     │ SQLAlchemy Async DB │
  │    (Real-time)      │     │  (SQLite / MySQL)   │
  └─────────────────────┘     └─────────────────────┘
```

---

## 2. Key Architecture Principles

1. **In-Memory Source of Truth**: The active Order Book is kept purely in memory (RB-Tree + DLL) for sub-millisecond execution speeds.
2. **Asynchronous Persistence**: Database writes occur AFTER matching completes without blocking the matching pipeline.
3. **Decoupled Analytics**: SQL analytics run directly against DB tables, preventing query load from affecting execution latency.
