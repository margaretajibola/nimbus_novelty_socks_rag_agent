# Nimbus RAG Agent: Possible Improvements

Ideas for making the agent better, grouped by effort. Pick from the top first.

Keep this file in the project folder, not inside `docs/`, so it does not get indexed as a company document.

## Suggested order

1. Conversation memory
2. Persist the vector store
3. Markdown-aware chunking
4. Automated evaluation using `test_questions.md`
5. Small talk router
6. Streaming and better source display

---

## Quick wins

### 1. Conversation memory

**Problem:** Each question is answered on its own. A follow-up like "and for non-birth parents?" fails, because the agent has no idea what "and" refers to.

**Fix:** Add a step at the start of the graph that rewrites a follow-up into a standalone question using recent chat history. The retriever then searches with a full question.

```python
# add to GraphState
chat_history: List[dict]   # [{"role": "user", "content": ...}, {"role": "assistant", ...}]

# a chain that turns a follow-up into a standalone question
condense_chain = create_grading_prompt(
    "Given the conversation history and a follow-up question, rewrite the follow-up "
    "as a standalone question. If it is already standalone, return it unchanged.",
    "History:\n{history}\n\nFollow-up question: {question}",
) | ChatOpenAI(model="gpt-4o-mini", temperature=0) | StrOutputParser()


# new node
def condense_question(state):
    history = state["chat_history"][-6:]   # last 3 exchanges
    if not history:
        return {}
    text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    return {"question": condense_chain.invoke({"history": text, "question": state["question"]})}


# graph wiring: replace START -> retrieve with
workflow.add_node("condense_question", condense_question)
workflow.add_edge(START, "condense_question")
workflow.add_edge("condense_question", "retrieve")
```

Then update `answer_question(question, chat_history=None)` to pass `chat_history` into the starting state, and in `ui.py` pass `st.session_state.messages`.

**Alternative:** LangGraph has a built-in checkpointer (`MemorySaver`) that stores state per `thread_id`. It is less code, but the condense step above is easier to understand and debug first.

**Effort:** 1 to 2 hours.

### 2. Persist the vector store

**Problem:** Every start re-embeds all documents, which costs a little and slows startup.

**Fix:** Save Chroma to disk and only rebuild when the documents change.

```python
from pathlib import Path

PERSIST_DIR = "chroma_db"

if Path(PERSIST_DIR).exists():
    vectorstore = Chroma(
        collection_name="rag-chroma",
        embedding_function=OpenAIEmbeddings(),
        persist_directory=PERSIST_DIR,
    )
else:
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=OpenAIEmbeddings(),
        persist_directory=PERSIST_DIR,
    )
```

Delete the `chroma_db` folder to force a rebuild after you edit the documents. A later upgrade is to store a hash of each file and re-index only the changed ones.

**Effort:** 30 minutes.

### 3. Markdown-aware chunking

**Problem:** A chunk from the middle of a section may not say which policy it belongs to, for example "up to $220 per night" with no heading nearby.

**Fix:** Split by headings first, so each chunk keeps its section title as metadata, then split by size.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "title"), ("##", "section")]
)
```

Run it on each file's text, then pass the results through your existing token splitter. You can also put the title and section at the top of each chunk's text so the embedding captures them.

**Effort:** 1 hour.

### 4. Tune retrieval

- Try `k` between 4 and 10 and compare results on the test questions.
- Try MMR search (`search_type="mmr"`) to avoid returning near-duplicate chunks.
- Try chunk sizes of 200, 250 and 400 tokens and compare.

**Effort:** 1 hour, mostly testing.

---

## Medium effort

### 5. Automated evaluation

Turn `test_questions.md` into a script that runs every question through the agent and scores it. Use an LLM judge that compares the answer to the expected answer, with the "should say I don't know" questions scored separately. Log accuracy, retries, and latency per question as JSON.

This connects directly to the evaluation dashboard project: the same results format can feed the Streamlit dashboard, so you can compare chunk sizes, retrieval settings, or models on this agent.

**Effort:** 2 to 3 hours.

### 6. Small talk and off-topic router

**Problem:** "Hi" or "What's the weather?" goes through the full retrieve and grade loop and ends in a slow "I don't know."

**Fix:** Add a first node that classifies the message as `company_question`, `small_talk` or `off_topic`. Small talk gets a quick friendly reply. Off-topic gets a polite refusal. Only company questions enter the retrieval loop. This is the "adaptive RAG" pattern.

**Effort:** 1 to 2 hours.

### 7. Better source display

Show the matching snippet and section title under each answer, in an expandable box, not only the file name. Users can then verify the answer.

```python
with st.expander("View sources"):
    for d in documents:
        st.markdown(f"**{d.metadata['source']}**")
        st.caption(d.page_content[:300])
```

This needs `answer_question` to return the documents as well as the file names.

**Effort:** 1 hour.

### 8. Streaming answers

Stream the answer token by token in the UI instead of waiting for the full reply. Use `st.write_stream` with the LLM's `.stream()` method. Note that the graph runs several steps first, so only the final generate step can stream.

**Effort:** 1 to 2 hours.

### 9. Hybrid search and reranking

Combine keyword search (BM25) with vector search, then rerank the combined results. This helps with exact terms like "Receipto", "Leaflet" or "Sock Friday" that embeddings sometimes miss. Also consider a reranker model to reorder the top results before grading.

**Effort:** 3 to 4 hours.

### 10. Support more file types

Add loaders for PDF, DOCX and web pages, since real company knowledge is rarely all Markdown. The loader function can pick the loader by file extension.

**Effort:** 1 to 2 hours.

---

## Larger improvements

### 11. Observability

Add tracing (Langfuse or LangSmith) to see every step: which chunks were retrieved, what the graders decided, how many retries happened, and how long each step took. This is the fastest way to find out why a specific answer was wrong.

### 12. Speed and cost

- Grade the retrieved chunks in parallel instead of one by one (`retrieval_grader.batch(...)`).
- Skip the answer grader when the hallucination grader passes and the answer is short.
- Cache answers to repeated questions.
- Try a smaller or local model for the graders (this ties in with the Ollama support from the evaluation dashboard).

### 13. Clarifying questions

When a question is ambiguous, such as "How many days off do I get?" (PTO, sick, bereavement, or parental), ask which one the user means instead of guessing.

### 14. Guardrails and safety

- Treat document content as data, not instructions, so text inside a file cannot hijack the agent.
- Add a rule that the agent never reveals restricted data categories.
- Limit question length and rate-limit requests if the app is shared.

### 15. User feedback

Add thumbs up and thumbs down buttons under each answer and log them with the question, answer and sources. Bad answers become new test questions.

### 16. Document freshness and conflicts

Store each document's last-updated date as metadata, show it with the sources, and prefer newer documents when two disagree. Test this by adding a deliberately conflicting document.

### 17. Deployment

Deploy the Streamlit app (Streamlit Community Cloud or a Docker container), keep API keys in secrets, and add simple authentication if the content is private.

---

## Portfolio notes

- Add a README with a screenshot of the chat and a diagram of the graph.
- Document the evaluation results: accuracy on the test questions before and after each improvement. Numbers make a stronger story than a list of features.
- Mention the design choices: the corrective RAG loop, the retry cap, and the "I don't know" behavior.
