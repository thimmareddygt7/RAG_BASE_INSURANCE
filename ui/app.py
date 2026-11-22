"""Streamlit demo: log in as a policyholder, agent or admin, upload PDFs, and ask questions.

Run the API first (offline demo: RAG_OFFLINE=1 AUTH_SECRET_KEY=<32+ chars> uvicorn app.api:app).
"""

import os

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo-password")
SAMPLES = [
    "What is the room rent limit per day?",
    "What is the Gold tier commission?",
    "What is the waiting period for cataract surgery?",
    "What is the annual premium for a 45-year-old?",
]

st.set_page_config(page_title="Health Insurance RAG", page_icon="🩺", layout="wide")
st.title("🩺 Health Insurance Policy Q&A")
st.warning("Demo only, not insurance advice.")

with st.sidebar:
    st.header("👤 Sign in")
    username = st.selectbox("Demo user", ["alice (policyholder)", "bob (agent)", "carol (admin)"])
    if st.button("Log in", use_container_width=True):
        try:
            r = httpx.post(
                f"{API_URL}/auth/login",
                timeout=30,
                json={"username": username.split()[0], "password": DEMO_PASSWORD},
            )
            r.raise_for_status()
            st.session_state["auth"] = r.json()
        except httpx.HTTPError as exc:
            st.error(f"Login failed: {exc}")

    auth = st.session_state.get("auth")
    if auth:
        st.success(f"Signed in as **{auth['display_name']}** (`{auth['group']}`)")
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        try:
            docs_resp = httpx.get(f"{API_URL}/documents", headers=headers, timeout=30)
            if docs_resp.status_code == 200:
                docs = docs_resp.json()
                st.subheader(f"📚 Documents ({len(docs)})")
                for d in docs:
                    is_upload = d["doc_id"].startswith("UPLOAD_")
                    icon = "📄" if is_upload else "📋"
                    st.write(f"{icon} `{d['doc_id']}` ({d.get('version', 'v1')})")
        except Exception as exc:
            st.caption(f"Could not load documents: {exc}")

    version_scope = st.radio("Search scope", ["latest", "all"], horizontal=True,
                             help="'latest' searches only the newest version of each policy; 'all' searches every version.")

auth = st.session_state.get("auth")
if not auth:
    st.info("👈 Please choose a demo user in the sidebar and click **Log in** to start.")
    st.stop()

headers = {"Authorization": f"Bearer {auth['access_token']}"}

tab_qa, tab_upload = st.tabs(["💬 Ask Questions", "📤 Upload Policy PDF"])

# =========================================================================
# Tab 1: Ask Questions
# =========================================================================
with tab_qa:
    sample = st.selectbox("Sample questions (or type your own below)", [""] + SAMPLES)
    question = st.text_input("Your question about any indexed policy", value=sample,
                             placeholder="e.g. What is the coverage limit for critical illness?")

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        ask_clicked = st.button("🔍 Ask Question", type="primary", use_container_width=True)

    if ask_clicked and question.strip():
        with st.spinner("Searching documents, reranking, and generating verified answer..."):
            try:
                r = httpx.post(
                    f"{API_URL}/ask",
                    headers=headers,
                    timeout=120,
                    json={"question": question.strip(), "version_scope": version_scope},
                )
                if r.status_code != 200:
                    st.error(f"Request failed ({r.status_code}): {r.text}")
                    st.stop()
                data = r.json()

                if data["refused"]:
                    st.info(f"ℹ️ **Refusal:** {data['answer']}")
                    st.caption(f"Reason: `{data.get('refusal_reason', 'unknown')}`")
                else:
                    st.success(f"### Answer\n{data['answer']}")

                    if data.get("citations"):
                        st.markdown("#### 📌 Citations")
                        for c in data["citations"]:
                            icon = "✅ Verified" if c["verified"] else "⚠️ Unverified"
                            st.write(f"- {icon}: **{c['doc_id']}**, page {c['page']}")

                with st.expander("🔍 Retrieved Context Sources (shown to the LLM)"):
                    for i, s in enumerate(data.get("sources", []), 1):
                        st.markdown(
                            f"**Source {i}: {s['doc_id']}** (ver {s['version']}), "
                            f"Page {s['page']} | Score: `{s['score']:.3f}`"
                        )
                        st.code(s["text"], language="markdown")

                st.caption(
                    f"⏱️ Total Latency: {data['timings_ms'].get('total', 0):.0f} ms "
                    f"(Retrieval: {data['timings_ms'].get('retrieval', 0):.0f} ms, "
                    f"LLM: {data['timings_ms'].get('llm', 0):.0f} ms) | {data['disclaimer']}"
                )
            except Exception as exc:
                st.error(f"Connection error: {exc}")

# =========================================================================
# Tab 2: Upload PDF
# =========================================================================
with tab_upload:
    st.subheader("📄 Upload a New Policy PDF")
    st.write(
        "Upload any health insurance policy or terms document in PDF format. "
        "The system will automatically extract text and tables, split into semantic chunks, "
        "compute vector embeddings, and index it into the Qdrant vector database so you can query it immediately."
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload standard digital or scanned PDF (up to 50 MB)",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_size_kb = len(file_bytes) / 1024
        st.write(f"**Selected File:** `{uploaded_file.name}` ({file_size_kb:.1f} KB)")

        if st.button("🚀 Upload & Index PDF", type="primary"):
            with st.spinner("Uploading, chunking, and embedding PDF into Qdrant..."):
                try:
                    files = {"file": (uploaded_file.name, file_bytes, "application/pdf")}
                    r = httpx.post(f"{API_URL}/upload", headers=headers, files=files, timeout=180)
                    if r.status_code == 200:
                        res = r.json()
                        st.success(res["message"])
                        st.markdown(f"""
                        - **Document ID:** `{res['doc_id']}`
                        - **Original File:** `{res['filename']}`
                        - **Chunks Created & Indexed:** `{res['chunks_indexed']}`
                        """)
                        st.info("👉 Switch to the **'💬 Ask Questions'** tab to ask any question about your document!")
                        st.rerun()
                    else:
                        st.error(f"Upload failed ({r.status_code}): {r.text}")
                except Exception as exc:
                    st.error(f"Error connecting to server: {exc}")
