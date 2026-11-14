# Security notes

This is a demo project, but it follows basic secure-development practice.

- **Secrets:** API keys and the JWT secret live only in `.env` (ignored by git). `.env.example` contains placeholders. A pre-commit hook (gitleaks) blocks commits that contain keys. If a key is ever exposed, revoke it immediately and create a new one.
- **Fail closed:** login and every protected endpoint refuse to work with a missing, placeholder or short (under 32 characters) JWT secret. Tokens signed with another key, expired tokens and `alg: none` tokens are rejected (covered by tests).
- **Prompt injection:** the system prompt tells the model to ignore instructions inside the context or question. This is a mitigation, not a guarantee. The real protection is that restricted text is never retrieved for the user in the first place.
- **Input limits:** questions are limited to 1000 characters and validated. Passwords are verified with constant-time comparison, and unknown users take the same time as wrong passwords.
- **Access control:** the user's group comes from a signed token. The `allowed_groups` filter runs inside the Qdrant query, so restricted chunks never reach the reranker or the LLM. `data/gold/permission_tests.csv` includes a forged-group request that must be refused.
- **Container:** runs as a non-root user, Qdrant is bound to localhost, and `.dockerignore` keeps `.env` out of the image.
- **Downloads:** `scripts/download.py` only fetches documents marked `license_checked = yes`, rejects path traversal in file names, caps file size and verifies SHA-256 hashes.
- **Data:** no real personal data. The internal agent guide is synthetic and labelled fake.

Report issues by opening a GitHub issue.
