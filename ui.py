import streamlit as st

from nimbus_agent import answer_question

st.set_page_config(page_title="Nimbus Assistant", page_icon="🧦")
st.title("🧦 Nimbus Assistant")
st.caption("Ask about Nimbus Novelty Socks policies, benefits and company info.")

# stop Streamlit from reading $...$ as a math formula
def clean(text):
    return text.replace("$", "\\$")


# keep the chat history between reruns
if "messages" not in st.session_state:
    st.session_state.messages = []

# sample questions in the sidebar, clicking one asks it
st.sidebar.header("Try asking")
samples = [
    "How many sick days do I get?",
    "How much can I spend on a hotel when travelling?",
    "When can I bring my dog to the office?",
    "Do employees get stock options?",
]
for s in samples:
    if st.sidebar.button(s):
        st.session_state.pending = s

# show the earlier messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(clean(m["content"]))
        if m.get("sources"):
            st.caption("Sources: " + ", ".join(m["sources"]))


# take a typed question or a clicked sample
pending = st.session_state.pop("pending", None)
question = st.chat_input("Ask a question") or pending

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(clean(question))

    with st.chat_message("assistant"):
        with st.spinner("Searching the documents..."):
            answer, sources = answer_question(question)
        st.write(clean(answer))
        if sources:
            st.caption("Sources: " + ", ".join(sources))

    st.session_state.messages.append(
        {"role": "assistant", "content": clean(answer), "sources": sources}
    )

