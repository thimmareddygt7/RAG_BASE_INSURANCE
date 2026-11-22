import unittest

try:
    from fastapi.testclient import TestClient

    from app.api import create_app
    from app.config import load_settings

    HAVE = True
except ImportError:  # lightweight environments without the API stack
    HAVE = False

SECRET = "t" * 40
PASSWORD = "demo-password"


@unittest.skipUnless(HAVE, "fastapi/httpx/PyJWT not installed")
class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {"AUTH_SECRET_KEY": SECRET, "RAG_OFFLINE": "1"}
        cls.settings = load_settings(stage="stage4_rerank", env=env)
        cls.client = TestClient(create_app(cls.settings, offline=True))

    def token(self, user):
        r = self.client.post("/auth/login", json={"username": user, "password": PASSWORD})
        self.assertEqual(r.status_code, 200, r.text)
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_health_is_public_and_leaks_nothing(self):
        body = self.client.get("/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertNotIn("secret", str(body).lower())

    def test_login_rejects_bad_credentials(self):
        r = self.client.post("/auth/login", json={"username": "bob", "password": "wrong"})
        self.assertEqual(r.status_code, 401)

    def test_ask_requires_token(self):
        self.assertEqual(self.client.post("/ask", json={"question": "hello there"}).status_code,
                         401)
        bad = {"Authorization": "Bearer not.a.token"}
        self.assertEqual(self.client.post("/ask", json={"question": "hello there"},
                                          headers=bad).status_code, 401)

    def test_permission_difference_over_http(self):
        q = {"question": "What is the Gold tier commission?"}
        customer = self.client.post("/ask", json=q, headers=self.token("alice")).json()
        agent = self.client.post("/ask", json=q, headers=self.token("bob")).json()
        self.assertTrue(customer["refused"])
        self.assertNotIn("AGENT_GUIDE_FAKE", str(customer))
        self.assertFalse(agent["refused"])
        self.assertEqual(agent["citations"][0]["doc_id"], "AGENT_GUIDE_FAKE")

    def test_forged_group_in_body_is_ignored(self):
        body = {"question": "What is the Gold tier commission?", "group": "admin",
                "user_group": "admin"}
        r = self.client.post("/ask", json=body, headers=self.token("alice")).json()
        self.assertTrue(r["refused"])
        self.assertNotIn("AGENT_GUIDE_FAKE", str(r))

    def test_documents_list_is_filtered_by_group(self):
        alice = {d["doc_id"] for d in
                 self.client.get("/documents", headers=self.token("alice")).json()}
        bob = {d["doc_id"] for d in self.client.get("/documents", headers=self.token("bob")).json()}
        self.assertNotIn("AGENT_GUIDE_FAKE", alice)
        self.assertIn("AGENT_GUIDE_FAKE", bob)

    def test_reindex_is_admin_only(self):
        self.assertEqual(self.client.post("/admin/reindex", headers=self.token("bob")).status_code,
                         403)
        r = self.client.post("/admin/reindex", headers=self.token("carol"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["added"], [])  # already indexed: nothing changes

    def test_input_validation(self):
        r = self.client.post("/ask", json={"question": "hi"}, headers=self.token("alice"))
        self.assertEqual(r.status_code, 422)

    def test_prompt_is_never_returned(self):
        r = self.client.post("/ask", json={"question": "What is the free-look period?"},
                             headers=self.token("alice")).json()
        self.assertNotIn("prompt", r)

    def test_unconfigured_secret_fails_closed(self):
        settings = load_settings(env={})
        client = TestClient(create_app(settings, offline=True))
        r = client.post("/auth/login", json={"username": "bob", "password": PASSWORD})
        self.assertEqual(r.status_code, 500)

    def test_upload_pdf_and_query(self):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "The Diamond Rider policy covers acupuncture therapy up to 25000 rupees.")
        pdf_bytes = doc.tobytes()
        doc.close()

        files = {"file": ("diamond_rider.pdf", pdf_bytes, "application/pdf")}
        r = self.client.post("/upload", files=files, headers=self.token("alice"))
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("UPLOAD_", data["doc_id"])
        self.assertGreater(data["chunks_indexed"], 0)

        # Check it appears in documents list
        docs = self.client.get("/documents", headers=self.token("alice")).json()
        doc_ids = [d["doc_id"] for d in docs]
        self.assertIn(data["doc_id"], doc_ids)

        # Query the newly uploaded document
        ask_res = self.client.post("/ask",
                                   json={"question": "What does the Diamond Rider cover for acupuncture?"},
                                   headers=self.token("alice"))
        self.assertEqual(ask_res.status_code, 200)
        answer_data = ask_res.json()
        self.assertFalse(answer_data["refused"])
        self.assertIn("25000", answer_data["answer"])


if __name__ == "__main__":
    unittest.main()
