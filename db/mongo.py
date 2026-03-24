"""
MongoDB Atlas connection module.

How Atlas connections work:
    MongoDB Atlas gives you a URI that looks like:
        mongodb+srv://username:password@cluster0.abc123.mongodb.net/

    The "mongodb+srv://" prefix means "use DNS SRV lookup to find the
    actual server addresses." This is how Atlas handles load balancing
    and auto-failover without you hardcoding IP addresses.

    The [srv] extra in pymongo (pip install "pymongo[srv]") installs
    the dnspython library that makes SRV DNS lookups possible.

Security:
    The URI contains your password, so it must NEVER be committed to git.
    We store it in a .env file (listed in .gitignore) and load it with
    python-dotenv. The .env file is only on your local machine.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

# Load environment variables from the .env file in the project root.
# load_dotenv() reads KEY=VALUE pairs from the file into os.environ.
# If .env does not exist it does nothing silently -- no crash.
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# Module-level variable to hold the connection once created.
# None until get_client() is called for the first time.
_client: MongoClient | None = None

DB_NAME = "tariff_study"


def get_client() -> MongoClient:
    """
    Return a MongoClient, creating it on first call and reusing it after.

    Why a singleton?
        A MongoClient manages a connection pool -- a set of open TCP
        connections to Atlas that are shared across all requests. Creating
        a new client on every call would open and close connections
        repeatedly, which is slow. The singleton opens the pool once and
        keeps it alive for the lifetime of the script.
    """
    global _client
    if _client is None:
        uri = os.environ.get("MONGO_URI")
        if not uri:
            raise RuntimeError(
                "MONGO_URI is not set.\n"
                "Create a .env file in the project root with:\n"
                f"  MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/"
                f"{DB_NAME}?retryWrites=true&w=majority\n"
                "Copy .env.example to .env and fill in your Atlas credentials."
            )
        _client = MongoClient(uri)
    return _client


def get_db() -> Database:
    """Return the tariff_study database object."""
    return get_client()[DB_NAME]


def get_collection(name: str) -> Collection:
    """
    Return a named collection from the tariff_study database.

    In MongoDB, a collection is analogous to a SQL table -- it holds
    documents (analogous to rows). Collections are created automatically
    on first write; no CREATE TABLE statement needed.
    """
    return get_db()[name]


def ensure_indexes() -> None:
    """
    Create indexes on all collections. Safe to call multiple times.

    Why indexes matter:
        Without an index, MongoDB scans every document to answer a query
        (a "collection scan"). With millions of rows this is very slow.
        An index is a sorted data structure that lets MongoDB jump directly
        to the matching documents.

        Compound indexes like (ticker, collection_date) cover queries that
        filter on both fields at once -- e.g. "all AAPL rows from April."
        MongoDB can use the compound index to satisfy this without
        scanning the entire collection.

    unique=True on the upsert key prevents duplicate documents. If you
    re-run the upload script, pymongo matches on the unique key and
    updates the existing document instead of inserting a second copy.

    create_index() is idempotent -- calling it on an already-existing
    index is harmless.
    """
    db = get_db()

    # -- options_clean indexes
    col = db["options_clean"]
    col.create_index([("ticker", ASCENDING), ("collection_date", ASCENDING)])
    col.create_index([("ticker", ASCENDING), ("phase", ASCENDING)])
    # Unique key: one snapshot per option contract per collection day.
    # optionSymbol encodes ticker + expiry + side + strike (OCC format),
    # so (optionSymbol, collection_date) is guaranteed unique.
    col.create_index(
        [("optionSymbol", ASCENDING), ("collection_date", ASCENDING)],
        unique=True,
        name="uq_symbol_date",
    )

    # -- options_features indexes (same structure, extra engineered columns)
    col = db["options_features"]
    col.create_index([("ticker", ASCENDING), ("collection_date", ASCENDING)])
    col.create_index([("ticker", ASCENDING), ("phase", ASCENDING)])
    col.create_index(
        [("optionSymbol", ASCENDING), ("collection_date", ASCENDING)],
        unique=True,
        name="uq_symbol_date",
    )

    # -- prices indexes
    col = db["prices"]
    # One price row per ticker per trading day
    col.create_index(
        [("ticker", ASCENDING), ("date", ASCENDING)],
        unique=True,
        name="uq_ticker_date",
    )

    print("Indexes ensured on: options_clean, options_features, prices")
