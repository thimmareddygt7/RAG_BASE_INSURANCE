import json
import unittest
from pathlib import Path

from app.auth import (AuthError, User, authenticate, create_token, decode_token, hash_password,
                      load_users, verify_password)

try:
    import jwt  # noqa: F401
    HAVE_JWT = True
except ImportError:
    HAVE_JWT = False

SECRET = "s" * 40
GROUPS = ["policyholder", "agent", "admin"]
ROOT = Path(__file__).resolve().parent.parent


class Passwords(unittest.TestCase):
    def test_hash_roundtrip_and_salting(self):
        h1, h2 = hash_password("pw"), hash_password("pw")
        self.assertNotEqual(h1, h2)
        self.assertTrue(verify_password("pw", h1))
        self.assertFalse(verify_password("wrong", h1))

    def test_malformed_hash_is_rejected_not_crashing(self):
        self.assertFalse(verify_password("pw", "garbage"))

    def test_demo_users_file_authenticates(self):
        users = load_users(ROOT / "data/synthetic/demo_users.json")
        self.assertEqual(authenticate(users, "bob", "demo-password").group, "agent")
        for bad in (("bob", "nope"), ("nobody", "demo-password")):
            with self.assertRaises(AuthError):
                authenticate(users, *bad)

    def test_users_file_contains_only_hashes(self):
        raw = (ROOT / "data/synthetic/demo_users.json").read_text()
        self.assertNotIn("demo-password", raw)
        self.assertTrue(all(u["password_hash"].startswith("scrypt$")
                            for u in json.loads(raw).values()))


@unittest.skipUnless(HAVE_JWT, "PyJWT not installed")
class Tokens(unittest.TestCase):
    USER = User("bob", "agent", "Bob")

    def test_roundtrip_carries_group(self):
        token = create_token(self.USER, SECRET, "HS256", 5)
        self.assertEqual(decode_token(token, SECRET, "HS256", GROUPS).group, "agent")

    def test_wrong_secret_expired_and_tampered_tokens_rejected(self):
        token = create_token(self.USER, SECRET, "HS256", 5)
        with self.assertRaises(AuthError):
            decode_token(token, "x" * 40, "HS256", GROUPS)
        with self.assertRaises(AuthError):
            decode_token(create_token(self.USER, SECRET, "HS256", -1), SECRET, "HS256", GROUPS)
        with self.assertRaises(AuthError):
            decode_token(token[:-2] + "xx", SECRET, "HS256", GROUPS)

    def test_unknown_group_rejected(self):
        token = create_token(User("e", "superuser", "E"), SECRET, "HS256", 5)
        with self.assertRaises(AuthError):
            decode_token(token, SECRET, "HS256", GROUPS)

    def test_alg_none_token_rejected(self):
        import jwt
        forged = jwt.encode({"sub": "x", "group": "admin", "exp": 9999999999}, "", algorithm="none")
        with self.assertRaises(AuthError):
            decode_token(forged, SECRET, "HS256", GROUPS)


if __name__ == "__main__":
    unittest.main()
