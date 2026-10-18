# Nimbus Assistant — Corrective RAG Agent

A retrieval-augmented chatbot that answers employee questions about Nimbus Novelty Socks' internal policies (PTO, expenses, IT security, benefits, FAQ) by searching the company's own Markdown documents. Built with LangGraph as a **corrective RAG** loop: retrieved documents are graded for relevance, generated answers are graded for grounding and usefulness, and the question is rewritten and retried when retrieval comes up short.

## How it works

1. **Retrieve** — embed the question and pull the most similar chunks from a Chroma vector store.
2. **Grade documents** — an LLM grader keeps only the chunks that are actually relevant to the question.
3. **Generate** — if relevant chunks were found, answer using only those chunks as context.
4. **Grade the generation** — check the answer is grounded in the retrieved chunks (no hallucination) and that it actually answers the question.
5. **Retry or give up** — if grading fails at any point, the question is rewritten for a better search and the loop retries, up to `MAX_RETRIES` times. If it still fails, the agent replies "I don't know" instead of guessing.

## Project structure

- `nimbus_agent.py` — document loading, chunking, the Chroma vector store, the LLM graders, and the LangGraph workflow (`answer_question`)
- `ui.py` — Streamlit chat interface with sample questions and source citations
- `company_rag_docs/docs/` — the knowledge base: employee handbook, PTO and leave policy, expenses and travel policy, IT security policy, and an FAQ
- `company_rag_docs/test_questions.md` — a manual test set with expected answers, used to sanity-check the agent after changes
- `IMPROVEMENTS.md` — notes on possible next steps (conversation memory, persistence, evaluation, etc.)

## Setup

### 1. Install dependencies

```bash
cd nimbus_novelty_socks_rag_agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI key:

```
OPENAI_API_KEY=<your-openai-key>
```

### 3. Point the agent at your local docs path

`nimbus_agent.py` currently sets `DOCS_DIR` to an absolute path. Update it to the `company_rag_docs/docs` folder on your machine before running.

## Running

Launch the chat UI:

```bash
streamlit run ui.py
```

Ask questions from the sidebar or type your own, e.g. "How many sick days do I get?" or "When can I bring my dog to the office?". Each answer shows the source documents it was grounded in.

You can also test from the terminal by uncommenting the `ask(...)` calls at the bottom of `nimbus_agent.py` and running `python nimbus_agent.py`.

## Tech stack

- [LangGraph](https://github.com/langchain-ai/langgraph) — the corrective RAG workflow (retrieve → grade → generate → retry)
- [LangChain](https://github.com/langchain-ai/langchain) — document loading, chunking, prompts
- [Chroma](https://www.trychroma.com/) — vector store for semantic search over the docs
- [OpenAI](https://platform.openai.com/) — embeddings and chat models (`gpt-4o-mini`)
- [Streamlit](https://streamlit.io) — chat UI
