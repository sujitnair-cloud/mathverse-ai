from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — imported by main.py (app setup) and individual routes
# that need tighter per-endpoint limits.
# Storage is in-process memory; with gunicorn multi-worker each worker tracks
# its own counters (effective limit = limit × workers), which is fine for MVP.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
)
