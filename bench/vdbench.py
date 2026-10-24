#!/usr/bin/env python3
"""Vector DB benchmark harness (Qdrant REST). Runs a real workload and prints
measured metrics as JSON on the last stdout line.

Env: BENCH_URL (e.g. https://xyz.qdrant.io or http://localhost:6333), BENCH_KEY.
Args: --n vectors (default 10000), --dim (default 128), --queries (default 100).

Designed to run as a Nebius AI Cloud Serverless Job or locally via Docker.
"""
import argparse
import json
import os
import random
import sys
import time
import uuid

import httpx

BASE = os.environ.get("BENCH_URL", "http://localhost:6333").rstrip("/")
KEY = os.environ.get("BENCH_KEY", "")


def hdrs():
    return {"api-key": KEY, "Content-Type": "application/json"} if KEY else {"Content-Type": "application/json"}


def vec(dim):
    return [random.random() for _ in range(dim)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--queries", type=int, default=100)
    a = ap.parse_args()

    name = "bench_" + uuid.uuid4().hex[:8]
    lat = []
    with httpx.Client(base_url=BASE, headers=hdrs(), timeout=60) as c:
        r = c.put(f"/collections/{name}", json={"vectors": {"size": a.dim, "distance": "Cosine"}})
        r.raise_for_status()
        # upsert in batches of 256
        t0 = time.time()
        for i in range(0, a.n, 256):
            pts = [{"id": j, "vector": vec(a.dim)} for j in range(i, min(i + 256, a.n))]
            c.put(f"/collections/{name}/points?wait=true", json={"points": pts}).raise_for_status()
        ingest_s = time.time() - t0
        # query latency
        for _ in range(a.queries):
            t0 = time.time()
            c.post(f"/collections/{name}/points/search", json={"vector": vec(a.dim), "limit": 10}).raise_for_status()
            lat.append((time.time() - t0) * 1000)
        try:
            c.delete(f"/collections/{name}")
        except Exception:
            pass

    lat.sort()
    p50 = lat[len(lat) // 2]
    p99 = lat[int(len(lat) * 0.99) - 1]
    out = {"target": BASE, "n": a.n, "dim": a.dim, "ingest_s": round(ingest_s, 2), "p50_ms": round(p50, 1), "p99_ms": round(p99, 1), "qps": round(1000 / p50, 1) if p50 else None}
    print(json.dumps(out))


if __name__ == "__main__":
    sys.exit(main())
