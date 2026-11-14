"""Streamlit demo: log in as a policyholder, agent or admin and ask questions.

Run the API first (offline demo: RAG_OFFLINE=1 AUTH_SECRET_KEY=<32+ chars> uvicorn app.api:app).
"""

import os

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo-password")
SAMPLES = ["What is the room rent limit per day?", "What is the Gold tier commission?",
           "What is the waiting period for cataract surgery?",
           "What is the annual premium for a 45-year-old?"]

st.set_page_config(page_title="Health Insurance RAG", page_icon="🩺", layout="wide")
st.title("Health Insurance Policy Q&A")
st.warning("Demo only, not insurance advice.")

with st.sidebar:
    st.header("Sign in")
    username = st.selectbox("Demo user", ["alice (policyholder)", "bob (agent)", "carol (admin)"])
    if st.button("Log in"):
        try:
            r = httpx.post(f"{API_URL}/auth/login", timeout=30,
                           json={"username": username.split()[0], "password": DEMO_PASSWORD})
            r.raise_for_status()
            st.session_state["auth"] = r.json()
        except httpx.HTTPError as exc:
            st.error(f"Login failed: {exc}")
    auth = st.session_state.get("auth")
    if auth:
        st.success(f"Signed in as {auth['display_name']}")
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        docs = httpx.get(f"{API_URL}/documents", headers=headers, timeout=30)
        if docs.status_code == 200:
            st.subheader("Documents you can see")
            for d in docs.json():
                st.write(f"- {d['doc_id']} ({d['version']})")
    version_scope = st.radio("Versions", ["latest", "all"], horizontal=True)

auth = st.session_state.get("auth")
if not auth:
    st.info("Choose a demo user in the sidebar and log in.")
    st.stop()

headers = {"Authorization": f"Bearer {auth['access_token']}"}
sample = st.selectbox("Try a sample question", [""] + SAMPLES)
question = st.text_input("Your question", value=sample)
if st.button("Ask") and question:
    r = httpx.post(f"{API_URL}/ask", headers=headers, timeout=120,
                   json={"question": question, "version_scope": version_scope})
    if r.status_code != 200:
        st.error(f"Request failed ({r.status_code}): {r.text}")
        st.stop()
    data = r.json()
    if data["refused"]:
        st.info(data["answer"])
    else:
        st.success(data["answer"])
        for c in data["citations"]:
            icon = "✅" if c["verified"] else "⚠️ unverified"
            st.write(f"{icon} **{c['doc_id']}**, page {c['page']}")
    with st.expander("Sources shown to the model"):
        for s in data["sources"]:
            st.markdown(f"**{s['doc_id']}** ({s['version']}), page {s['page']}, "
                        f"score {s['score']:.3f}")
            st.code(s["text"])
    st.caption(f"Latency: {data['timings_ms'].get('total', 0):.0f} ms | {data['disclaimer']}")
