"""Generate data/synthetic/demo_users.json. Demo accounts only; never reuse this password."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import hash_password  # noqa: E402

DEMO_PASSWORD = "demo-password"
USERS = {
    "alice": ("policyholder", "Alice (policyholder)"),
    "bob": ("agent", "Bob (agent)"),
    "carol": ("admin", "Carol (admin)"),
}

if __name__ == "__main__":
    out = {u: {"group": g, "display_name": n, "password_hash": hash_password(DEMO_PASSWORD)}
           for u, (g, n) in USERS.items()}
    path = Path(__file__).resolve().parent.parent / "data/synthetic/demo_users.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} (password for all demo users: {DEMO_PASSWORD})")
