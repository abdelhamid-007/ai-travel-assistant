"""Chat page for the travel assistant. Run: streamlit run app.py"""
import streamlit as st
from assistant import ask

st.set_page_config(page_title="Travel Assistant", page_icon="✈️")
st.title("✈️ Travel Assistant")
st.caption("Answers from live offers in PostgreSQL + pgvector, checked by a second model. Runs locally with Ollama.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Ask about trips, prices, dates, visas, payment…")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching offers…"):
            result = ask(question)
        st.markdown(result["answer"])

        # Shows the client how the answer was made: the part that sells a RAG project
        with st.expander("How this answer was made"):
            st.write(f"**Status:** {result['status']}  ·  **Filters read from the question:** {result['filters']}")
            if result["status"].startswith("blocked"):
                st.warning(f"Blocked draft: {result['draft']}")
            for label, text in result["cited"].items():
                st.info(f"**{label}** — {text}")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
