import os

# Make any database problem fail in seconds with a clear error instead of hanging.
os.environ.setdefault("PGCONNECT_TIMEOUT", "5")
os.environ.setdefault("PGOPTIONS", "-c lock_timeout=5000 -c statement_timeout=30000")
