"""
database.py — MongoDB connection with graceful fallback to an in-memory mock.

If MONGO_URI is not set (or MongoDB is unreachable), the app still runs using
a lightweight in-memory store so you can test predictions without a DB.

Set MONGO_URI in your environment or a .env file to persist data:
    MONGO_URI=mongodb://localhost:27017
"""

import os

MONGO_URI = os.getenv("MONGO_URI", "")
DB_NAME = os.getenv("DB_NAME", "enerpredict")


# ---------------------------------------------------------------------------
# In-memory fallback collection (mimics the minimal pymongo Collection API)
# ---------------------------------------------------------------------------
class _InMemoryCollection:
    """Minimal stand-in for a pymongo Collection when MongoDB is unavailable."""

    def __init__(self, name: str):
        self._name = name
        self._docs: list = []
        self._counter = 0

    def insert_one(self, doc: dict):
        self._counter += 1
        fake_id = f"mem_{self._name}_{self._counter}"
        doc = dict(doc)
        doc["_id"] = fake_id
        self._docs.append(doc)

        class _Result:
            inserted_id = fake_id

        return _Result()

    def find(self, query: dict = None, *args, **kwargs):
        """Very basic equality-filter find — good enough for house_id lookups."""
        query = query or {}
        results = []
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in query.items()):
                results.append(dict(doc))
        return _SortableCursor(results)


class _SortableCursor:
    """Minimal cursor that supports .sort() and .limit() chaining."""

    def __init__(self, docs: list):
        self._docs = docs

    def sort(self, key, direction=-1):
        try:
            self._docs = sorted(self._docs, key=lambda d: d.get(key, ""), reverse=(direction == -1))
        except Exception:
            pass
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)


# ---------------------------------------------------------------------------
# Attempt real MongoDB connection; fall back silently if unavailable
# ---------------------------------------------------------------------------
pred_col = None
household_col = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        # Force a connection attempt to catch errors early
        _client.admin.command("ping")
        _db = _client[DB_NAME]
        pred_col = _db["predictions"]
        household_col = _db["households"]
        print(f"[DB] Connected to MongoDB at {MONGO_URI} (db: {DB_NAME})")
    except Exception as e:
        print(f"[DB] MongoDB connection failed ({e}). Using in-memory store.")
        pred_col = None
        household_col = None

if pred_col is None:
    print("[DB] Using in-memory store (data is not persisted between restarts).")
    pred_col = _InMemoryCollection("predictions")
    household_col = _InMemoryCollection("households")
