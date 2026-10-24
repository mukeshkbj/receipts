#!/usr/bin/env python3
"""Chroma benchmark harness. Runs in-process (no server) with an ephemeral
Chroma client and prints measured metrics as JSON on the last stdout line.

Args: --n vectors (default 5000), --dim (default 128), --queries (default 100).
"""
import argparse
import json
import random
import sys
import time


def vec(dim):
    return [random.random() for _ in range(dim)]


def main():
    import chromadb

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--queries", type=int, default=100)
    a = ap.parse_args()

    client = chromadb.EphemeralClient()
    col = client.create_collection("bench", metadata={"hnsw:space": "cosine"})

    t0 = time.time()
    batch = 256
    for i in range(0, a.n, batch):
        ids = [str(j) for j in range(i, min(i + batch, a.n))]
        col.add(ids=ids, embeddings=[vec(a.dim) for _ in ids])
    ingest_s = time.time() - t0

    lat = []
    for _ in range(a.queries):
        t0 = time.time()
        col.query(query_embeddings=[vec(a.dim)], n_results=10)
        lat.append((time.time() - t0) * 1000)

    lat.sort()
    p50 = lat[len(lat) // 2]
    p99 = lat[int(len(lat) * 0.99) - 1]
    out = {"target": "chroma-ephemeral", "n": a.n, "dim": a.dim, "ingest_s": round(ingest_s, 2), "p50_ms": round(p50, 1), "p99_ms": round(p99, 1), "qps": round(1000 / p50, 1) if p50 else None}
    print(json.dumps(out))


if __name__ == "__main__":
    sys.exit(main())
