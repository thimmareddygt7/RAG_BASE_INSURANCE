# Three-minute demo script

Setup: `docker compose up --build`, then `python scripts/sync_index.py`, open http://localhost:8501. For a no-key rehearsal: `RAG_OFFLINE=1 AUTH_SECRET_KEY=<32+ random chars> make api-offline`, then `streamlit run ui/app.py`.

1. **Normal question (alice, policyholder):** "What is the waiting period for cataract surgery?" Show the answer, the green verified citation, and the page text in "Sources shown to the model".
2. **Table question:** "What is the room rent limit per day?" Point out that the cited page contains the table row.
3. **Refusal:** "What is the annual premium for a 45-year-old?" It says the information is not in the documents instead of guessing.
4. **Permissions, the memorable part:** as alice ask "What is the Gold tier commission?" and it refuses. Log in as bob (agent), ask the same question, and get the answer with a citation to the agent guide. Show the sidebar document lists differ.
5. **Versions:** tick "all" versions and ask how the room rent limit changed between versions.
6. **Evidence:** open `eval/results/REPORT.md` and walk through one stage-to-stage change with its confidence interval and one "what failed" example.
