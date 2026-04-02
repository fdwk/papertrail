"""
One-time: replace legacy plaintext users.password_hash values with Argon2id hashes.

Deploy order (local Postgres and prod):

1. Deploy backend with Argon2 verification + legacy plaintext fallback (app.auth login).
2. Run this script (or rely on lazy upgrade on next login only).
3. After all rows use Argon2 (e.g. no password_hash left without ``$argon2`` prefix),
   optionally remove the legacy branch in app.passwords.verify_password.

Usage (from backend directory):

  set DATABASE_URL=postgresql://...  (Windows) or export DATABASE_URL=...
  python -m scripts.hash_existing_passwords

Do not run before step 1: stored values would become Argon2 strings while old code still
compares the submitted password to the literal database value.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

from app.database import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.passwords import hash_password  # noqa: E402


def main() -> None:
    if not os.getenv("DATABASE_URL"):
        print(
            "Set DATABASE_URL (e.g. postgresql://postgres:postgres@localhost:5433/mydb)"
        )
        raise SystemExit(1)
    session = SessionLocal()
    try:
        users = session.query(User).all()
        updated = 0
        for u in users:
            if not u.password_hash:
                continue
            if u.password_hash.startswith("$argon2"):
                continue
            u.password_hash = hash_password(u.password_hash)
            updated += 1
        if updated:
            session.commit()
        print("Updated %d user(s)." % updated)
    finally:
        session.close()


if __name__ == "__main__":
    main()
