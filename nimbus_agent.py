from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# load API keys from .env
load_dotenv(override=True)


# read every .md file in the folder into a LangChain Document
def load_documents(docs_dir):
    documents = []
    for path in sorted(Path(docs_dir).glob("*.md")):
        documents.append(Document(
            page_content=path.read_text(encoding="utf-8"),  # the text
            metadata={"source": path.name},                  # file name, used for citations
        ))
    return documents


DOCS_DIR = "/Users/margaretajibola/Desktop/software_learning /ai_agents_projects/nimbus_novelty_socks_rag_agent/company_rag_docs/docs"
docs_list = load_documents(DOCS_DIR)

# cut each document into chunks of 250 tokens, with 30 tokens of overlap
# so a rule is not cut in half between two chunks
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=250, chunk_overlap=30
)
doc_splits = text_splitter.split_documents(docs_list)

# turn each chunk into a vector and store it in Chroma so we can search by meaning
vectorstore = Chroma.from_documents(
    documents=doc_splits,
    collection_name="rag-chroma",
    embedding=OpenAIEmbeddings(),
)

# takes a question and returns the closest chunks (4 by default)
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})


# the shape every grader must answer in: 'yes' or 'no'
class BinaryScoreModel(BaseModel):
    binary_score: str = Field(description="Binary score: 'yes' or 'no'")


# an LLM that must return output matching the schema (temperature 0 keeps it consistent)
def create_structured_llm(model, schema):
    llm = ChatOpenAI(model=model, temperature=0)
    return llm.with_structured_output(schema)


# a prompt with a fixed instruction (system) and a fill-in-the-blank input (human)
def create_grading_prompt(system_message, human_template):
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_template),
    ])


# checks if a retrieved chunk is relevant to the question
retrieval_grader = create_grading_prompt(
    "You are a document retrieval evaluator responsible for checking the relevancy "
    "of a retrieved document to the user's question. \n If the document contains "
    "keyword(s) or semantic meaning related to the question, grade it as relevant. "
    "\n Output a binary score 'yes' or 'no'.",
    "Retrieved document: \n\n {document} \n\n User question: {question}",
) | create_structured_llm("gpt-4o-mini", BinaryScoreModel)

# checks if the answer is supported by the retrieved chunks (no made-up facts)
hallucination_grader = create_grading_prompt(
    "You are a grader assessing whether an LLM generation is grounded in / supported "
    "by a set of retrieved facts. \n Give a binary score 'yes' or 'no'. 'Yes' means "
    "that the answer is grounded in / supported by the set of facts.",
    "Set of facts: \n\n {documents} \n\n LLM generation: {generation}",
) | create_structured_llm("gpt-4o-mini", BinaryScoreModel)

# checks if the answer actually addresses the question
answer_grader = create_grading_prompt(
    "You are a grader assessing whether an answer addresses / resolves a question. "
    "\n Give a binary score 'yes' or 'no'. 'Yes' means that the answer resolves the question.",
    "User question: \n\n {question} \n\n LLM generation: {generation}",
) | create_structured_llm("gpt-4o-mini", BinaryScoreModel)

# rewrites a question so it searches better, used when retrieval fails
question_rewriter = create_grading_prompt(
    "You are a question re-writer that converts an input question to a better version "
    "optimized for vectorstore retrieval. Look at the input and try to reason about "
    "the underlying semantic intent / meaning.",
    "Here is the initial question: \n\n {question} \n Formulate an improved question.",
) | ChatOpenAI(model="gpt-4o-mini", temperature=0) | StrOutputParser()


# join the retrieved chunks into one block of text to give the LLM as context
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# ready-made prompt from LangChain Hub that takes {context} and {question}
# and says "I don't know" if the context lacks the answer
rag_prompt = ChatPromptTemplate.from_template(
    "You are an assistant for question-answering tasks. Use the following pieces "
    "of retrieved context to answer the question. If you don't know the answer, "
    "just say that you don't know. Keep the answer concise, using a short "
    "bulleted list if there are several items.\n\n"
    "Question: {question}\n\n"
    "Context: {context}\n\n"
    "Answer:"
)
rag_llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# prompt, then model, then plain text output
rag_chain = rag_prompt | rag_llm | StrOutputParser()


from typing import List, TypedDict

from langgraph.graph import END, START, StateGraph

# the most times the agent can retry before giving up
MAX_RETRIES = 3


# the data that moves through the graph, each node reads it and updates it
class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    retries: int


# -- NODES --
# search the vector store for chunks related to the question
def retrieve(state):
    docs = retriever.invoke(state["question"])
    return {"documents": docs}

# keep only the chunks the grader says are relevant
def grade_documents(state):
    relevant = []
    for d in state["documents"]:
        score = retrieval_grader.invoke(
            {"question": state["question"], "document": d.page_content}
        ).binary_score
        if score == "yes":
            relevant.append(d)
    return {"documents": relevant}

# write an answer from the relevant chunks
def generate(state):
    answer = rag_chain.invoke(
        {"context": format_docs(state["documents"]), "question": state["question"]}
    )
    return {"generation": answer, "retries": state["retries"] + 1}


# reword the question so the next search works better
def transform_query(state):
    better = question_rewriter.invoke({"question": state["question"]})
    return {"question": better, "retries": state["retries"] + 1}


# stop trying and say the answer is not in the documents
def give_up(state):
    return {"generation": "I don't know. This is not covered in the company documents."}



# -- NOT NODES AS THEY DON'T CHANGE STATE, THEY JUST RETURN VALUES TO SAY WHERE TO GO NEXT --
# after grading chunks: answer if any are relevant, otherwise rewrite the question or give up
def decide_to_generate(state):
    if state["documents"]:
        return "generate"
    if state["retries"] >= MAX_RETRIES:
        return "give_up"
    return "transform_query"


# after generating: check the answer is grounded, then that it answers the question
def grade_generation(state):
    grounded = hallucination_grader.invoke(
        {"documents": format_docs(state["documents"]), "generation": state["generation"]}
    ).binary_score
    if grounded != "yes":
        return "generate" if state["retries"] < MAX_RETRIES else "give_up"

    useful = answer_grader.invoke(
        {"question": state["question"], "generation": state["generation"]}
    ).binary_score
    if useful == "yes":
        return "useful"
    return "transform_query" if state["retries"] < MAX_RETRIES else "give_up"


# register the steps
workflow = StateGraph(GraphState)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("transform_query", transform_query)
workflow.add_node("give_up", give_up)


# connect the steps
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade_documents")

workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {"generate": "generate", "transform_query": "transform_query", "give_up": "give_up"},
)
workflow.add_edge("transform_query", "retrieve")
workflow.add_conditional_edges(
    "generate",
    grade_generation,
    {"generate": "generate", "transform_query": "transform_query",
     "give_up": "give_up", "useful": END},
)
workflow.add_edge("give_up", END)

app = workflow.compile()

# run a question through the graph and return the answer with its sources
def answer_question(question):
    result = app.invoke(
        {"question": question, "generation": "", "documents": [], "retries": 0}
    )
    sources = sorted({d.metadata["source"] for d in result["documents"]})
    return result["generation"], sources


# same as before, for testing in the terminal
def ask(question):
    answer, sources = answer_question(question)
    print("Q:", question)
    print("A:", answer)
    print("Sources:", sources or "none", "\n")


# if __name__ == "__main__":
#     ask("How many sick days do I get?")
#     ask("I have worked here 4 years. How many PTO days do I get?")
#     ask("Do employees get stock options?")